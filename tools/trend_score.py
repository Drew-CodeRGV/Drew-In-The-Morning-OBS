#!/usr/bin/env python3
"""Dedupe + trend score for Drew in the Morning.

Used by the 6 AM packet build (packet/build_packet.py) and by the 15-minute
breaking watch (tools/breaking_watch.py). No pip packages.

1. CLUSTER near-duplicate stories (same story, different outlets) with
   - URL canonicalization (tracking params, www/m/amp, fragments, trailing /)
   - normalized-title similarity: token Jaccard, plus a containment rule for a
     short headline that sits inside a longer one.
   One item is kept; the rest become its `sources[]`.
2. SCORE each cluster 0-100 from five transparent signals (see FORMULA below)
   and LABEL it Hot / Trending / Active.
3. Flag UNCOVERED: community/social buzz (and Valley relevance) but no local
   outlet has it. A scoop lead, always CONFIRM BEFORE AIR.

FORMULA (weights/thresholds live in DEFAULTS and can be overridden under
`scoring:` in feeds.yml):

    outlets  = min(30, 6 x distinct outlets covering the story)
    recency  = 20 x 0.5 ^ (age_hours / 12)       newest coverage; no timestamp -> 8
    x        = 20 x min(1, log10(1 + engagement + 25 x posts) / 4)
    trends   = 20 if the story matches a Google Trends US-TX item, else 12 for US
    chatter  = 10 x min(1, log10(1 + engagement + 5 x posts) / 2.5)   Reddit/Facebook
    score    = round(outlets + recency + x + trends + chatter)       (max 100)
    label    = Hot if score >= 45; Trending if >= 27; else Active

CLI:
    python3 tools/trend_score.py trends                 fetch + print Google Trends (US-TX, US)
    python3 tools/trend_score.py packet FILE.json [--fetch-trends]   score a packet data file (dry run table)
    python3 tools/trend_score.py stories FILE.json       score a flat list of stories
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ditm_yaml  # noqa: E402

UA = "DITM-BreakingWatch/1.0 (+https://github.com/Drew-CodeRGV/Drew-In-The-Morning-OBS)"
UTC = datetime.timezone.utc

DEFAULTS = {
    "weights": {"outlets": 30, "recency": 20, "x": 20, "trends": 20, "chatter": 10},
    "per_outlet": 6,
    "half_life_hours": 12,
    "no_timestamp_recency": 8,
    "trends_tx": 20,
    "trends_us": 12,
    "x_full_log10": 4.0,
    "x_post_weight": 25,
    "chatter_full_log10": 2.5,
    "chatter_post_weight": 5,
    "hot": 45,
    "trending": 27,
    "jaccard_strong": 0.6,
    "jaccard": 0.42,
    "containment": 0.75,
    "min_shared": 3,
    "merge_window_hours": 72,
    "uncovered_min_chatter": 5,
    "uncovered_min_x": 100,
    "coverage_containment": 0.35,
    "coverage_jaccard": 0.35,
}

STOP = set("""a an the and or but of for to in on at by with from as is are was were be been it its this that these those
after before over under into about up down out off new says say said will would could should may might more most than then
their his her they them he she we you i our your not no yes just also still amid vs via per""".split())
TRACKING = {"fbclid", "gclid", "ocid", "cid", "ref", "ref_src", "src", "taid", "mc_cid", "mc_eid", "igshid", "output",
            "outputtype", "ito", "smid", "smtyp", "cmp", "partner", "referrer", "source", "campaign"}
AGGREGATORS = {"news.google.com", "trends.google.com", "feedx.net"}


# ------------------------------------------------------------------ config
def load_config(root: str = ROOT) -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))
    feeds = {}
    p = os.path.join(root, "feeds.yml")
    if os.path.exists(p):
        feeds = ditm_yaml.load(p) or {}
        for k, v in (feeds.get("scoring") or {}).items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    cfg["local_outlets"] = {canon_domain(d) for d in (feeds.get("local_outlets") or [])}
    cfg["aliases"] = {canon_domain(k): canon_domain(v) for k, v in (feeds.get("outlet_aliases") or {}).items()}
    cfg["local_outlets"] |= {cfg["aliases"].get(d, d) for d in list(cfg["local_outlets"])}
    kw = {}
    kp = os.path.join(root, "watch-keywords.yml")
    if os.path.exists(kp):
        kw = ditm_yaml.load(kp) or {}
    cfg["keywords"] = kw
    return cfg


# ------------------------------------------------------------------ text/url helpers
def canon_domain(host: str) -> str:
    host = (host or "").lower().strip()
    host = re.sub(r"^https?://", "", host).split("/")[0].split(":")[0]
    for pre in ("www.", "m.", "amp.", "mobile."):
        if host.startswith(pre):
            host = host[len(pre):]
    return host


def domain_of(url: str, aliases: dict | None = None) -> str:
    try:
        d = canon_domain(urllib.parse.urlsplit(url).netloc)
    except Exception:
        d = ""
    return (aliases or {}).get(d, d)


def canon_url(url: str) -> str:
    """Stable form of a URL for equality checks."""
    if not url:
        return ""
    try:
        s = urllib.parse.urlsplit(url.strip())
    except Exception:
        return url.strip().lower()
    host = canon_domain(s.netloc)
    path = re.sub(r"/(amp|amp/)$", "", s.path)
    path = re.sub(r"/index\.(html?|php)$", "/", path)
    path = path.rstrip("/") or "/"
    q = [(k, v) for k, v in urllib.parse.parse_qsl(s.query, keep_blank_values=False)
         if not (k.lower().startswith("utm_") or k.lower() in TRACKING)]
    q.sort()
    return f"{host}{path}" + (("?" + urllib.parse.urlencode(q)) if q else "")


_SUFFIX = re.compile(r"\s+[-|\u2013\u2014:]\s+([^-|\u2013\u2014:]{2,40})$")


def strip_outlet_suffix(title: str, outlet: str = "") -> str:
    t = (title or "").strip()
    for _ in range(2):
        m = _SUFFIX.search(t)
        if not m:
            break
        tail = m.group(1).strip()
        if outlet and tail.lower().rstrip(".") == outlet.lower().rstrip("."):
            t = t[: m.start()].strip()
        elif len(tail.split()) <= 4 and (tail.istitle() or tail.isupper() or re.search(r"\b(news|times|post|herald|tribune|monitor|report|press|tv|radio|kveo|krgv|cbs|nbc|abc|fox|npr|ap)\b", tail, re.I)):
            t = t[: m.start()].strip()
        else:
            break
    return t


def norm_title(title: str, outlet: str = "") -> str:
    t = strip_outlet_suffix(title, outlet)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = t.replace("\u2019", "'").replace("'s ", " ")
    t = re.sub(r"[^a-z0-9$%\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _stem(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("ches", "shes", "sses", "xes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def tokens(title: str, outlet: str = "") -> frozenset:
    out = []
    for w in norm_title(title, outlet).split():
        if w in STOP or (len(w) < 2 and not w.isdigit()):
            continue
        out.append(_stem(w))
    return frozenset(out)


def jaccard(a, b) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment(a, b) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _nums(title: str) -> frozenset:
    return frozenset(re.findall(r"\$?\d[\d,.]*[mkb%]?", (title or "").lower()))


def _geo(title: str, cfg: dict) -> frozenset:
    kw = cfg.get("keywords") or {}
    if not kw.get("geo"):
        return frozenset()
    return frozenset(t.lower() for t in match_keywords(title, {"geo": kw.get("geo")}, True)["geo"])


def similar(a: dict, b: dict, cfg: dict) -> bool:
    """a, b: normalized items (see norm_item). Precision first: a wrongly merged pair hides a separate event."""
    if a["curl"] and a["curl"] == b["curl"] and _url_title_ok(a, b):
        return True  # same page + overlapping headline (a digest page shared by different stories does not count)
    ta, tb = a["tok"], b["tok"]
    shared = len(ta & tb)
    if shared < cfg["min_shared"]:
        return False
    if a.get("published") and b.get("published"):
        if abs((a["published"] - b["published"]).total_seconds()) > cfg["merge_window_hours"] * 3600:
            return False
    j, c = jaccard(ta, tb), containment(ta, tb)
    strong = j >= cfg["jaccard_strong"]
    medium = (j >= cfg["jaccard"] and shared >= 4) or (c >= cfg["containment"] and shared >= 5)
    if not (strong or medium):
        return False
    # guards: different numbers or different places = different events
    na, nb = _nums(a.get("title", "")), _nums(b.get("title", ""))
    if na and nb and not (na & nb):
        return False
    ga, gb = _geo(a.get("title", ""), cfg), _geo(b.get("title", ""), cfg)
    if ga and gb and not (ga & gb):
        return False
    return True


def parse_dt(s) -> datetime.datetime | None:
    if not s:
        return None
    if isinstance(s, datetime.datetime):
        return s if s.tzinfo else s.replace(tzinfo=UTC)
    s = str(s).strip()
    try:
        from email.utils import parsedate_to_datetime
        d = parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except Exception:
        pass
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except Exception:
        return None


_MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def date_hint(text: str, ref: datetime.datetime) -> datetime.datetime | None:
    """'MyRGV · Nov 17' -> Nov 17 noon CT (UTC-6) of the reference year."""
    m = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\b", text or "", re.I)
    if not m:
        return None
    mo, day = _MON[m.group(1).lower()[:3]], int(m.group(2))
    try:
        d = datetime.datetime(ref.year, mo, day, 18, 0, tzinfo=UTC)
    except ValueError:
        return None
    if d > ref + datetime.timedelta(days=2):
        d = d.replace(year=ref.year - 1)
    return d


def norm_item(raw: dict, cfg: dict) -> dict:
    """Normalize a story dict. Accepted keys: title, url, source/outlet, domain, published,
    kind (local|regional|state|national|wire|community|trend), x {posts, engagement},
    chatter {posts, engagement} (or list of such), valley (bool), text/summary."""
    url = raw.get("url") or ""
    dom = canon_domain(raw.get("domain") or "") or domain_of(url)
    dom = cfg["aliases"].get(dom, dom)
    outlet = (raw.get("outlet") or raw.get("source") or "").split("\u00b7")[0].strip()
    ch = raw.get("chatter") or {}
    if isinstance(ch, list):
        ch = {"posts": sum(int(c.get("posts", 0) or 0) for c in ch), "engagement": sum(int(c.get("engagement", 0) or 0) for c in ch)}
    x = raw.get("x") or {}
    it = {
        "title": re.sub(r"\s+", " ", str(raw.get("title") or "")).strip(),
        "url": url,
        "domain": dom,
        "outlet": outlet or dom,
        "kind": raw.get("kind") or ("local" if dom in cfg["local_outlets"] else "national"),
        "published": parse_dt(raw.get("published")),
        "x": {"posts": int(x.get("posts", 0) or 0), "engagement": int(x.get("engagement", 0) or 0)},
        "chatter": {"posts": int(ch.get("posts", 0) or 0), "engagement": int(ch.get("engagement", 0) or 0)},
        "valley": bool(raw.get("valley")),
        "text": raw.get("text") or raw.get("summary") or "",
        "ref": raw.get("ref"),
    }
    it["curl"] = canon_url(url) if domain_of(url) not in AGGREGATORS else ""
    it["tok"] = tokens(it["title"], it["outlet"])
    it["ttok"] = tokens(it["title"])
    return it


# ------------------------------------------------------------------ clustering
def _url_title_ok(a: dict, b: dict) -> bool:
    ta, tb = set(a["ttok"]), set(b["ttok"])
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    return inter >= 2 and (inter / len(ta | tb) >= 0.2 or inter / min(len(ta), len(tb)) >= 0.5)


def cluster(items: list[dict], cfg: dict) -> list[list[int]]:
    """Union-find clustering over normalized items. Deterministic: clusters ordered by first member."""
    n = len(items)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    inv: dict[str, list[int]] = {}
    for i, it in enumerate(items):
        cand = set()
        for t in it["tok"]:
            for j in inv.get(t, ()):
                cand.add(j)
        for j in sorted(cand):
            if find(i) != find(j) and similar(items[j], it, cfg):
                parent[find(i)] = find(j)
        for t in it["tok"]:
            inv.setdefault(t, []).append(i)
        if it["curl"]:
            for j in range(i):
                # same URL only merges when the headlines also overlap: a digest page (e.g. a daily briefing) is
                # linked by several different stories and must not collapse them into one
                if items[j]["curl"] == it["curl"] and find(i) != find(j) and _url_title_ok(items[j], it):
                    parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=lambda g: g[0])


# ------------------------------------------------------------------ google trends
def parse_trends_rss(xml_text: str, region: str) -> list[dict]:
    ns = {"ht": "https://trends.google.com/trending/rss"}
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for it in root.iter("item"):
        term = (it.findtext("title") or "").strip()
        traffic_s = (it.findtext("ht:approx_traffic", namespaces=ns) or "").strip()
        m = re.match(r"([\d,]+)(\+?)", traffic_s)
        traffic = int(m.group(1).replace(",", "")) if m else 0
        news = []
        for n in it.findall("ht:news_item", ns):
            news.append({"title": (n.findtext("ht:news_item_title", namespaces=ns) or "").strip(),
                         "url": (n.findtext("ht:news_item_url", namespaces=ns) or "").strip(),
                         "source": (n.findtext("ht:news_item_source", namespaces=ns) or "").strip()})
        if term:
            out.append({"term": term, "traffic": traffic, "traffic_s": traffic_s, "region": region,
                        "published": (it.findtext("pubDate") or "").strip(), "news": news, "tok": tokens(term)})
    return out


def fetch_url(url: str, timeout: int = 20, retries: int = 1) -> tuple[int, str]:
    last = (0, "")
    for k in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = (e.code, "")
            if e.code in (400, 401, 403, 404, 410):
                break
        except Exception as e:  # network
            last = (0, str(e)[:120])
    return last


def fetch_trends(regions=(("US-TX", "TX"), ("US", "US")), cache_path: str | None = None, max_age_h: float = 36.0) -> dict:
    """Return {"TX": [...], "US": [...], "fetchedAt": iso, "ok": {...}}. Falls back to cache if a fetch fails."""
    out = {"TX": [], "US": [], "ok": {}, "fetchedAt": None}
    cached = {}
    if cache_path and os.path.exists(cache_path):
        try:
            cached = json.load(open(cache_path))
        except Exception:
            cached = {}
    for geo, key in regions:
        code, body = fetch_url(f"https://trends.google.com/trending/rss?geo={geo}")
        items = parse_trends_rss(body, key) if code == 200 else []
        out["ok"][key] = {"status": code, "items": len(items)}
        if items:
            out[key] = items
    if any(out[k] for k in ("TX", "US")):
        out["fetchedAt"] = datetime.datetime.now(UTC).isoformat(timespec="seconds")
        if cache_path:
            ser = {k: [{kk: vv for kk, vv in t.items() if kk != "tok"} for t in out[k]] for k in ("TX", "US")}
            json.dump({"fetchedAt": out["fetchedAt"], **ser}, open(cache_path, "w"), indent=1)
    elif cached:
        fa = parse_dt(cached.get("fetchedAt"))
        if fa and (datetime.datetime.now(UTC) - fa).total_seconds() < max_age_h * 3600:
            for k in ("TX", "US"):
                out[k] = [dict(t, tok=tokens(t["term"])) for t in cached.get(k, [])]
            out["fetchedAt"] = cached.get("fetchedAt")
            out["fromCache"] = True
    return out


def load_trends_cache(path: str, max_age_h: float = 36.0) -> dict:
    out = {"TX": [], "US": [], "ok": {}, "fetchedAt": None}
    try:
        c = json.load(open(path))
    except Exception:
        return out
    fa = parse_dt(c.get("fetchedAt"))
    if fa and (datetime.datetime.now(UTC) - fa).total_seconds() < max_age_h * 3600:
        for k in ("TX", "US"):
            out[k] = [dict(t, tok=tokens(t["term"])) for t in c.get(k, [])]
        out["fetchedAt"] = c.get("fetchedAt")
        out["fromCache"] = True
    return out


GENERIC_TERMS = {"news", "today", "game", "score", "weather", "live", "update", "trump", "texas", "cowboys"}


def trend_match(c_tokens, c_titles, c_urls, trend_list, cfg):
    """Return the best matching trend dict or None."""
    best = None
    for t in trend_list or []:
        hit = False
        for n in t["news"]:
            cu = canon_url(n["url"])
            if cu and cu in c_urls:
                hit = True
                break
            nt = tokens(n["title"], n.get("source", ""))
            if len(nt & c_tokens) >= 3 and (jaccard(nt, c_tokens) >= 0.45 or containment(nt, c_tokens) >= 0.7):
                hit = True
                break
        if not hit and t["tok"]:
            tt = t["tok"]
            if len(tt) >= 2 and tt <= c_tokens:
                hit = True
            elif len(tt) == 1:
                w = next(iter(tt))
                if len(w) >= 6 and w not in GENERIC_TERMS and w in c_tokens:
                    hit = True
        if hit and (best is None or t["traffic"] > best["traffic"]):
            best = t
    return best


# ------------------------------------------------------------------ keyword matching
def _compile(terms):
    pats = []
    for t in terms or []:
        t = str(t).strip()
        if not t:
            continue
        stem = t.endswith("*")
        body = re.escape(t.rstrip("*")).replace(r"\ ", r"\s+").replace(r"\-", r"[-\s]?")
        pats.append((t, re.compile(r"(?<![A-Za-z0-9])" + body + (r"[A-Za-z]*" if stem else r"(?![A-Za-z0-9])"), re.I)))
    return pats


_kw_cache: dict = {}


def match_keywords(text: str, kw: dict, local_source: bool = True) -> dict:
    """Return {'geo': [...], 'urgent': [...], 'theme': [...], 'always': [...]} for a text."""
    key = repr(sorted((k, tuple(v) if isinstance(v, (list, tuple)) else v) for k, v in kw.items()))   # by content, not id(): ids get reused
    if key not in _kw_cache:
        amb = {a.lower() for a in (kw.get("geo_ambiguous") or [])}
        _kw_cache[key] = {
            "geo": _compile(kw.get("geo")), "urgent": _compile(kw.get("urgent")),
            "theme": _compile(kw.get("themes")), "always": _compile(kw.get("always_alert")), "amb": amb,
        }
    c = _kw_cache[key]
    out = {}
    for k in ("geo", "urgent", "theme", "always"):
        hits = []
        for t, p in c[k]:
            m = p.search(text or "")
            if m:
                hits.append(m.group(0).lower() if t.endswith("*") else t)
        out[k] = hits
    non_amb = [t for t in out["geo"] if t.lower() not in c["amb"]]
    if not non_amb and not local_source and not out["theme"]:
        out["geo"] = []  # ambiguous place names (Mission, Alamo...) only count from local outlets or with another hit
    return out


# ------------------------------------------------------------------ scoring
def _log_part(v: float, full_log: float) -> float:
    return min(1.0, math.log10(1 + max(0.0, v)) / full_log)


def score_cluster(members: list[dict], trends: dict | None, now: datetime.datetime, cfg: dict) -> dict:
    W = cfg["weights"]
    doms = {m["domain"] or m["outlet"].lower() for m in members}
    outlets = min(W["outlets"], cfg["per_outlet"] * len(doms))
    stamps = [m["published"] for m in members if m["published"]]
    if stamps:
        age_h = max(0.0, (now - max(stamps)).total_seconds() / 3600)
        recency = W["recency"] * 0.5 ** (age_h / cfg["half_life_hours"])
    else:
        age_h = None
        recency = cfg["no_timestamp_recency"]
    xp = sum(m["x"]["posts"] for m in members)
    xe = sum(m["x"]["engagement"] for m in members)
    xpts = W["x"] * _log_part(xe + cfg["x_post_weight"] * xp, cfg["x_full_log10"])
    cp = sum(m["chatter"]["posts"] for m in members)
    ce = sum(m["chatter"]["engagement"] for m in members)
    cpts = W["chatter"] * _log_part(ce + cfg["chatter_post_weight"] * cp, cfg["chatter_full_log10"])
    ctok = frozenset().union(*[m["tok"] for m in members]) if members else frozenset()
    curls = {m["curl"] for m in members if m["curl"]}
    tpts, tmatch = 0.0, None
    if trends:
        tx = trend_match(ctok, [m["title"] for m in members], curls, trends.get("TX"), cfg)
        us = trend_match(ctok, [m["title"] for m in members], curls, trends.get("US"), cfg)
        if tx:
            tpts, tmatch = cfg["trends_tx"], {"region": "TX", "term": tx["term"], "traffic": tx["traffic_s"]}
        elif us:
            tpts, tmatch = cfg["trends_us"], {"region": "US", "term": us["term"], "traffic": us["traffic_s"]}
    total = int(round(min(100, outlets + recency + xpts + tpts + cpts)))
    label = "Hot" if total >= cfg["hot"] else ("Trending" if total >= cfg["trending"] else "Active")
    parts = {"outlets": round(outlets, 1), "recency": round(recency, 1), "x": round(xpts, 1), "trends": round(tpts, 1), "chatter": round(cpts, 1)}
    bits = [f"{len(doms)} outlet{'s' if len(doms) != 1 else ''} {parts['outlets']:g}"]
    bits.append(f"recency {parts['recency']:g}" + (f" ({age_h:.0f}h old)" if age_h is not None else " (no timestamp)"))
    if xpts:
        bits.append(f"X {parts['x']:g}")
    if tmatch:
        bits.append(f"Trends {tmatch['region']} '{tmatch['term']}' {parts['trends']:g}")
    if cpts:
        bits.append(f"chatter {parts['chatter']:g}")
    return {"score": total, "label": label, "parts": parts, "why": f"Score {total}: " + " + ".join(bits),
            "trend": tmatch, "ageHours": None if age_h is None else round(age_h, 1),
            "x": {"posts": xp, "engagement": xe}, "chatter": {"posts": cp, "engagement": ce}}


def is_uncovered(members: list[dict], sc: dict, geo_hit: bool, local_pool: list[dict], cfg: dict) -> bool:
    """Community/social buzz + Valley relevance + no local outlet has it."""
    if any(m["domain"] in cfg["local_outlets"] or m["kind"] == "local" for m in members):
        return False
    cbuzz = sc["chatter"]["posts"] * cfg["chatter_post_weight"] + sc["chatter"]["engagement"]
    xbuzz = sc["x"]["posts"] * cfg["x_post_weight"] + sc["x"]["engagement"]
    trend_tx = bool(sc["trend"] and sc["trend"]["region"] == "TX")
    buzz = cbuzz >= cfg["uncovered_min_chatter"] or xbuzz >= cfg["uncovered_min_x"] or trend_tx
    social_only = any(m["kind"] == "community" for m in members) or xbuzz > 0
    if not buzz or not social_only:
        return False
    if not (geo_hit or any(m["valley"] for m in members)):
        return False
    tok = frozenset().union(*[m["tok"] for m in members])
    for lp in local_pool:  # loose check: is a local outlet already on it?
        sh = len(tok & lp["tok"])
        if sh >= 3 and (containment(tok, lp["tok"]) >= cfg["coverage_containment"] or jaccard(tok, lp["tok"]) >= cfg["coverage_jaccard"]):
            return False
    return True


def analyze(raw_items: list[dict], trends: dict | None = None, now: datetime.datetime | None = None,
            cfg: dict | None = None) -> list[dict]:
    """Cluster + score. Returns cluster dicts ordered by score desc (stable)."""
    cfg = cfg or load_config()
    now = now or datetime.datetime.now(UTC)
    items = [norm_item(r, cfg) for r in raw_items]
    local_pool = [i for i in items if i["domain"] in cfg["local_outlets"] or i["kind"] == "local"]
    out = []
    for idx_group in cluster(items, cfg):
        members = [items[i] for i in idx_group]
        sc = score_cluster(members, trends, now, cfg)
        kw = cfg["keywords"]
        text = " ".join(m["title"] + " " + (m["text"] or "") for m in members)
        geo_hit = bool(match_keywords(text, kw, True)["geo"])
        unc = is_uncovered(members, sc, geo_hit, local_pool, cfg)
        # representative: prefer a direct (non-aggregator) link, then a local outlet, then input order
        order = sorted(range(len(members)), key=lambda k: (members[k]["curl"] == "", members[k]["domain"] not in cfg["local_outlets"], k))
        rep = members[order[0]]
        sources, seen = [], set()
        for m in members:
            key = m["domain"] or m["outlet"]
            if key in seen:
                continue
            seen.add(key)
            sources.append({"name": m["outlet"], "domain": m["domain"], "url": m["url"], "local": m["domain"] in cfg["local_outlets"],
                            "published": m["published"].isoformat(timespec="seconds") if m["published"] else None})
        out.append({"rep": rep, "members": members, "index": idx_group, "sources": sources, **sc, "uncovered": unc})
    out.sort(key=lambda c: -c["score"])
    return out


# ------------------------------------------------------------------ packet integration
def _src_name(it):
    return (it.get("source") or "").split("\u00b7")[0].strip()


def score_packet(data: dict, trends: dict | None = None, now: datetime.datetime | None = None,
                 cfg: dict | None = None, sort: bool = True) -> dict:
    """Dedupe + score the packet's story lists IN PLACE. Returns a summary dict.

    List priority (a duplicate is kept in the earlier list): nationalDesk > headlines.rgv >
    headlines.texas > trending > leads. Adds to every kept item: sources[], score, label, uncovered,
    scoreWhy, ord. Duplicates merge their links/sources into the kept item.
    """
    cfg = cfg or load_config()
    now = now or datetime.datetime.now(UTC)
    H = data.get("headlines", {})
    lists = [("national", data.get("nationalDesk") or []), ("rgv", H.get("rgv") or []), ("texas", H.get("texas") or []),
             ("trending", data.get("trending") or []), ("leads", data.get("leads") or [])]
    raw, refs = [], []
    for ln, lst in lists:
        for i, it in enumerate(lst):
            extra_raw = []
            if ln == "national":
                links = it.get("links") or []
                url = links[0]["url"] if links else (it.get("url") or "")
                r = {"title": it["title"], "url": url, "source": _src_name(it) or (links[0]["label"] if links else ""), "kind": "national"}
                # every distinct outlet linked under a National Desk story is coverage of it
                extra_raw = [{"title": it["title"], "url": l["url"], "source": (l.get("label") or "").split(":")[0], "kind": "national"} for l in links[1:] if l.get("url")]
            elif ln in ("rgv", "texas"):
                r = {"title": it["title"], "url": it.get("url", ""), "source": it.get("source", ""), "kind": "local" if ln == "rgv" else "state"}
            elif ln == "trending":
                r = {"title": it["title"], "url": it.get("source_url", ""), "source": it.get("source", ""), "kind": "national"}
                extra_raw = [{"title": it["title"], "url": l["url"], "source": (l.get("label") or "").split(":")[0], "kind": "national"} for l in (it.get("links") or []) if l.get("url")]
            else:
                r = {"title": it["title"], "url": it.get("url") or it.get("source_url") or "", "source": it.get("source", ""),
                     "kind": "community"}
            r["published"] = it.get("published") or date_hint(it.get("source", ""), now)
            for k in ("x", "chatter", "valley"):
                if k in it:
                    r[k] = it[k]
            raw.append(r)
            refs.append((ln, i))
            for e in extra_raw:
                e["published"] = r["published"]
                raw.append(e)
                refs.append((ln, i))
    clusters = analyze(raw, trends, now, cfg)
    prio = {"national": 0, "rgv": 1, "texas": 2, "trending": 3, "leads": 4}
    dropped, merged = {n: set() for n in prio}, 0
    for c in clusters:
        seen_ref, idxs = set(), []
        for i in sorted(c["index"], key=lambda i: (prio[refs[i][0]], refs[i][1], i)):
            if refs[i] not in seen_ref:
                seen_ref.add(refs[i]); idxs.append(i)
        keep = idxs[0]
        kl, ki = refs[keep]
        kept = dict(lists)[kl][ki]
        for j in idxs[1:]:
            ln, i = refs[j]
            dup = dict(lists)[ln][i]
            if ln == "national":
                continue  # never drop a National Desk story
            # merge the duplicate's links into the kept item
            extra = []
            if ln == "trending":
                if dup.get("source_url"):
                    extra.append({"label": (dup.get("source") or "source") + ": " + dup["title"][:60], "url": dup["source_url"]})
                extra += dup.get("links") or []
            elif ln in ("rgv", "texas") and dup.get("url"):
                extra.append({"label": (dup.get("source") or "source").split("\u00b7")[0].strip() + ": " + dup["title"][:60], "url": dup["url"]})
            if extra and kl in ("national", "trending"):
                have = {l["url"] for l in kept.get("links", [])}
                kept.setdefault("links", []).extend(l for l in extra if l["url"] not in have)
            dropped[ln].add(i)
            merged += 1
        kept["sources"] = c["sources"]
        kept["score"], kept["label"], kept["uncovered"] = c["score"], c["label"], c["uncovered"]
        kept["scoreWhy"], kept["scoreParts"] = c["why"], c["parts"]
        kept["dupes"] = len(idxs) - 1
        if c["uncovered"]:
            kept["confirm"] = (kept.get("confirm") or "") or "Uncovered lead: social/community buzz, no local outlet has it. Verify before air."
    # rebuild lists without dropped duplicates, stable-sort by score
    summary = {"merged": merged, "items": 0, "hot": 0, "trending": 0, "active": 0, "uncovered": 0}
    for ln, lst in lists:
        keepers = [(i, it) for i, it in enumerate(lst) if i not in dropped[ln]]
        for pos, (i, it) in enumerate(keepers):
            it["ord"] = pos
        if sort:
            keepers.sort(key=lambda p: -p[1].get("score", 0))
        new = [it for _, it in keepers]
        lst[:] = new
        for it in new:
            summary["items"] += 1
            summary[it["label"].lower()] += 1
            summary["uncovered"] += 1 if it["uncovered"] else 0
    if trends:
        summary["trends"] = {"TX": len(trends.get("TX", [])), "US": len(trends.get("US", [])), "fetchedAt": trends.get("fetchedAt"),
                             "fromCache": bool(trends.get("fromCache"))}
    return summary


# ------------------------------------------------------------------ CLI
def _cli(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("trends")
    p1 = sub.add_parser("packet"); p1.add_argument("file"); p1.add_argument("--fetch-trends", action="store_true")
    p2 = sub.add_parser("stories"); p2.add_argument("file"); p2.add_argument("--fetch-trends", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_config()
    if a.cmd == "trends":
        t = fetch_trends()
        for k in ("TX", "US"):
            print(f"== Google Trends {k}: HTTP {t['ok'].get(k, {}).get('status')} · {len(t[k])} items")
            for x in t[k]:
                print(f"  {x['traffic_s']:>7}  {x['term']}  ({len(x['news'])} news items)")
        return 0 if (t["TX"] or t["US"]) else 1
    trends = fetch_trends() if a.fetch_trends else None
    if a.cmd == "stories":
        stories = json.load(open(a.file))
        for c in analyze(stories, trends, cfg=cfg):
            print(f"{c['score']:3d} {c['label']:<8} {'UNCOVERED ' if c['uncovered'] else ''}{c['rep']['title'][:90]}  [{len(c['sources'])} src]")
            print("      " + c["why"])
        return 0
    data = json.load(open(a.file))
    s = score_packet(data, trends, cfg=cfg)
    print(json.dumps(s))
    for ln, lst in (("national", data.get("nationalDesk", [])), ("rgv", data["headlines"]["rgv"]), ("texas", data["headlines"]["texas"]), ("trending", data.get("trending", []))):
        for it in lst:
            print(f"{it['score']:3d} {it['label']:<8} {ln:<8} {'UNCOVERED ' if it['uncovered'] else ''}{it['title'][:80]}  (+{it['dupes']} dup)")
            print("      " + it["scoreWhy"])
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
