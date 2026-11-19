#!/usr/bin/env python3
"""Breaking watch: poll public RSS feeds, score/dedupe, keep seen-state, write docs/breaking.json, send alerts.

Runs from .github/workflows/breaking-watch.yml (every 15 min 5-11 AM CT, hourly otherwise) or by hand:

    python3 tools/breaking_watch.py --dry-run          # real feeds, no files written, no alerts sent
    python3 tools/breaking_watch.py                     # real run (writes state/seen.json + docs/breaking.json)

Alerts (all optional, all off until configured; nothing secret lives in the repo):
  - docs/breaking.json         always (the studio dashboard strip reads it)
  - ntfy.sh push               only if env NTFY_TOPIC is set (+ optional NTFY_TOKEN, NTFY_SERVER)
  - GitHub issue labeled breaking   only if env BREAKING_ISSUES=true and GITHUB_TOKEN + GITHUB_REPOSITORY are set

No pip packages. Never posts anything except the ntfy / issue alerts above.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ditm_yaml  # noqa: E402
import trend_score as ts  # noqa: E402

UTC = datetime.timezone.utc
MAX_ITEM_AGE_H = 36
ALERT_MAX_AGE_H = 3          # only alert on items published within this many hours
STRIP_WINDOW_H = 24
STATE_KEEP_H = 72
STATE_HEAVY_H = 24
HEARTBEAT_MIN = 60
NTFY_PER_RUN = 5
ISSUES_PER_RUN = 5
ISSUES_PER_DAY = 15
BACKOFF_FAILS = 6
BACKOFF_HOURS = 6
DASH = "https://drew-codergv.github.io/Drew-In-The-Morning-OBS/"


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def now_utc() -> datetime.datetime:
    return datetime.datetime.now(UTC)


def iso(d) -> str | None:
    return d.astimezone(UTC).isoformat(timespec="seconds") if d else None


# ------------------------------------------------------------------ parsing
def _ln(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _clean(s: str, n: int = 300) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s)
    return re.sub(r"\s+", " ", s).strip()[:n]


def _safe_url(u: str) -> str:
    u = (u or "").strip()
    return u if re.match(r"^https?://", u, re.I) else ""


def parse_feed(xml_text: str, feed: dict) -> list[dict]:
    """RSS 2.0 / Atom -> list of raw story dicts for trend_score.analyze."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except ET.ParseError as e:
        raise ValueError(f"not XML ({str(e)[:60]})")
    out = []
    for el in root.iter():
        t = _ln(el.tag)
        if t not in ("item", "entry"):
            continue
        f: dict = {}
        link = ""
        for ch in el:
            k = _ln(ch.tag)
            if k == "link":
                link = ch.get("href") or (ch.text or "") if not link else link
            elif k in ("title", "pubDate", "published", "updated", "description", "summary", "encoded", "content"):
                f.setdefault(k, ch.text or "")
            elif k == "source":
                f["source"] = (ch.text or "").strip()
                f["source_url"] = ch.get("url") or ""
            elif k == "guid" and not link and (ch.text or "").startswith("http"):
                link = ch.text
        title = _clean(f.get("title", ""), 240)
        if not title or not _safe_url(link):
            continue
        outlet = f.get("source") or feed.get("name", "")
        dom_hint = ""
        if feed.get("aggregator") and f.get("source_url"):
            dom_hint = ts.canon_domain(urllib.parse.urlsplit(f["source_url"]).netloc)
        pub = f.get("pubDate") or f.get("published") or f.get("updated")
        title = ts.strip_outlet_suffix(title, outlet) if feed.get("aggregator") else title
        raw = {
            "title": title, "url": _safe_url(link).strip(), "outlet": outlet, "domain": dom_hint, "published": pub,
            "kind": feed.get("kind") if feed.get("kind") in ("local", "community", "state", "national", "wire", "regional", "specialist") else "national",
            # Google News descriptions are lists of OTHER headlines: never use them for keyword matching
            "text": "" if feed.get("aggregator") else _clean(f.get("description") or f.get("summary") or f.get("encoded") or f.get("content") or "", 300),
            "valley": bool(feed.get("valley")), "feed": feed["id"],
        }
        if feed.get("kind") == "community":
            raw["chatter"] = {"posts": 1, "engagement": 0}
            raw["outlet"] = feed.get("name", "Reddit")
            raw["domain"] = "reddit.com"
        out.append(raw)
        if len(out) >= int(feed.get("limit") or 50):
            break
    return out


def fetch_all(feeds: list[dict], state: dict, now: datetime.datetime, fetch=ts.fetch_url, force: bool = False):
    """Fetch every enabled feed. Returns (stories, trends, status). Never raises for a bad feed."""
    status, stories = {}, []
    trends = {"TX": [], "US": [], "ok": {}, "fetchedAt": iso(now)}
    fstate = state.setdefault("feeds", {})
    todo = []
    for f in feeds:
        if f.get("enabled") is False:
            continue
        st = fstate.get(f["id"], {})
        last = ts.parse_dt(st.get("lastTry"))
        if not force and st.get("fails", 0) >= BACKOFF_FAILS and last and (now - last).total_seconds() < BACKOFF_HOURS * 3600:
            status[f["id"]] = {"ok": False, "status": "skipped (backing off after repeated failures)", "items": 0, "optional": bool(f.get("optional"))}
            continue
        todo.append(f)

    def work(f):
        code, body = fetch(f["url"])
        return f, code, body

    normal = [f for f in todo if f.get("kind") != "community"]
    community = [f for f in todo if f.get("kind") == "community"]
    results = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        results += list(ex.map(work, normal))
    for f in community:  # be gentle with Reddit
        results.append(work(f))
        time.sleep(2.0)
    for f, code, body in results:
        ok, n, err = False, 0, ""
        try:
            if code == 200 and body:
                if f.get("kind") == "trends":
                    items = ts.parse_trends_rss(body, f["region"])
                    trends[f["region"]] = items
                    n = len(items)
                else:
                    items = parse_feed(body, f)
                    stories += items
                    n = len(items)
                ok = n > 0
                if not ok:
                    err = "0 items"
            else:
                err = f"HTTP {code}" if code else (body or "network error")
        except Exception as e:
            err = str(e)[:80]
        if f.get("kind") == "trends":
            trends["ok"][f["region"]] = {"status": code, "items": n}
        status[f["id"]] = {"ok": ok, "status": "ok" if ok else err, "items": n, "optional": bool(f.get("optional"))}
        s = fstate.setdefault(f["id"], {})
        if ok:
            # only touch state when something changed (keeps commits quiet)
            lo = ts.parse_dt(s.get("lastOk"))
            if s.get("fails") or s.get("lastStatus") != "ok" or lo is None or (now - lo).total_seconds() > 24 * 3600:
                s.update({"fails": 0, "lastOk": iso(now), "lastStatus": "ok", "lastTry": iso(now)})
        else:
            s.update({"fails": s.get("fails", 0) + 1, "lastTry": iso(now), "lastStatus": status[f["id"]]["status"]})
    return stories, trends, status


# ------------------------------------------------------------------ state
def load_state(path: str) -> dict:
    try:
        st = json.load(open(path, encoding="utf-8"))
        if st.get("version") == 1:
            return st
    except Exception:
        pass
    return {"version": 1, "updated": None, "feeds": {}, "items": [], "issues": {"date": "", "n": 0}, "firstRun": True}


def item_key(raw: dict) -> str:
    cu = ts.canon_url(raw["url"]) if ts.domain_of(raw["url"]) not in ts.AGGREGATORS else ""
    return cu or "u:" + hashlib.sha1(raw["url"].encode()).hexdigest()[:14]


def seen_match(cl: dict, seen_items: list[dict], cfg: dict) -> dict | None:
    """Return the seen-state record this cluster corresponds to, or None if it is new."""
    keys = {item_key({"url": m["url"]}) for m in cl["members"]}
    for rec in seen_items:
        if keys & set(rec.get("keys", [])):
            return rec
    rep = {"curl": "", "tok": frozenset().union(*[m["tok"] for m in cl["members"]]), "published": cl["rep"]["published"]}
    for rec in seen_items:
        other = {"curl": "", "tok": frozenset(rec.get("tok", [])), "published": ts.parse_dt(rec.get("published"))}
        if ts.similar(rep, other, cfg):
            return rec
    return None


# ------------------------------------------------------------------ classification
def classify(cl: dict, cfg: dict) -> dict:
    """Keyword matches + level (alert/watch/None) for one scored cluster."""
    kw = cfg["keywords"]
    titles = " ".join(m["title"] for m in cl["members"])
    text = titles + " " + " ".join(m.get("text") or "" for m in cl["members"])
    local_src = any(m["kind"] == "local" or m["domain"] in cfg["local_outlets"] for m in cl["members"])
    k = ts.match_keywords(text, kw, local_src)
    # urgent words only count in the headline (an excerpt that mentions "flooding" in passing is not a flood)
    k["urgent"] = ts.match_keywords(titles, {"urgent": kw.get("urgent")}, True)["urgent"]
    k["always"] = ts.match_keywords(titles, {"always_alert": kw.get("always_alert")}, True)["always"]
    texas = bool(re.search(r"\btexas\b", text, re.I))
    always = bool(k["always"]) and (bool(k["geo"]) or texas)
    hot = cl["label"] == "Hot"
    level, reasons = None, []
    if hot:
        reasons.append("Hot")
    if always:
        reasons.append("always-alert: " + ", ".join(k["always"]))
    if k["geo"] and k["urgent"]:
        reasons.append("geo+urgent: " + ", ".join(k["geo"][:2] + k["urgent"][:2]))
    if reasons:
        level = "alert"
    elif k["theme"] or cl["uncovered"]:
        level = "watch"
        reasons.append("theme: " + ", ".join(k["theme"][:3]) if k["theme"] else "Uncovered lead")
    elif k["geo"] and cl["label"] == "Trending":
        level = "watch"
        reasons.append("Trending in the Valley")
    matches = sorted({*k["geo"], *k["urgent"], *k["theme"], *k["always"]}, key=str.lower)
    return {"level": level, "reasons": reasons, "matches": matches, "always": always}


# ------------------------------------------------------------------ alerts
def _post_json(url: str, payload: dict, headers: dict, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": ts.UA, **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return 0, str(e)[:200]


def send_ntfy(alerts: list[dict], env=os.environ, post=_post_json, dry: bool = False) -> int:
    topic = (env.get("NTFY_TOPIC") or "").strip()
    if not topic:
        return 0
    server = (env.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    headers = {"Authorization": "Bearer " + env["NTFY_TOKEN"]} if env.get("NTFY_TOKEN") else {}
    sent = 0
    for a in alerts[:NTFY_PER_RUN]:
        tags = ["rotating_light"] if a["always"] else (["fire"] if a["label"] == "Hot" else ["mega"])
        if a["uncovered"]:
            tags.append("mag")
        body = {"topic": topic, "title": f"{'Hot' if a['label'] == 'Hot' else 'Alert'} · {a['source']}"[:120],
                "message": f"{a['title']}\nScore {a['score']} · {', '.join(a['reasons'])}\nCONFIRM BEFORE AIR",
                "click": a["url"] or DASH, "tags": tags, "priority": 5 if a["always"] else (4 if a["label"] == "Hot" or "geo+urgent" in " ".join(a["reasons"]) else 3)}
        if dry:
            log(f"  [dry-run] would ntfy: {a['title'][:80]}")
            sent += 1
            continue
        code, msg = post(server, body, headers)
        if 200 <= code < 300:
            sent += 1
            a["alerted_ntfy"] = True
        else:
            log(f"  ntfy failed: HTTP {code} {msg[:80]}")  # never log the topic
    extra = len(alerts) - NTFY_PER_RUN
    if extra > 0 and not dry:
        post(server, {"topic": topic, "title": "Breaking watch", "message": f"+{extra} more alerts, open the dashboard", "click": DASH, "tags": ["mega"], "priority": 3}, headers)
    return sent


def _no_ping(s: str) -> str:
    return s.replace("@", "@\u200b")


def open_issues(alerts: list[dict], state: dict, env=os.environ, post=_post_json, dry: bool = False,
                today: str | None = None) -> int:
    if (env.get("BREAKING_ISSUES") or "").lower() not in ("1", "true", "yes", "on"):
        return 0
    token, repo = env.get("GITHUB_TOKEN"), env.get("GITHUB_REPOSITORY")
    if not (token and repo) and not dry:
        log("  issues: GITHUB_TOKEN/GITHUB_REPOSITORY missing, skipped")
        return 0
    api = (env.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    today = today or datetime.datetime.now(UTC).strftime("%Y-%m-%d")
    iss = state.setdefault("issues", {"date": "", "n": 0})
    if iss.get("date") != today:
        iss["date"], iss["n"] = today, 0
    top = [a for a in alerts if a["always"] or a["label"] == "Hot" or "geo+urgent" in " ".join(a["reasons"])]
    n = 0
    for a in top[:ISSUES_PER_RUN]:
        if iss["n"] >= ISSUES_PER_DAY:
            log("  issues: daily cap reached")
            break
        src = "\n".join(f"- {_no_ping(s['name'])}: {s['url']}" for s in a["sources"][:6])
        body = (f"**{_no_ping(a['title'])}**\n\n{a['label']} · score {a['score']} · {', '.join(a['reasons'])}\n\n{src}\n\n"
                f"{a['why']}\n\n**CONFIRM BEFORE AIR.** Opened automatically by the breaking watch (tools/breaking_watch.py). "
                f"Dashboard: {DASH}")
        payload = {"title": ("[breaking] " + _no_ping(a["title"]))[:140], "body": body, "labels": ["breaking"]}
        if dry:
            log(f"  [dry-run] would open issue: {payload['title'][:90]}")
            n += 1
            continue
        h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        code, msg = post(f"{api}/repos/{repo}/issues", payload, h)
        if code == 422:  # label problem: retry without it
            payload.pop("labels")
            code, msg = post(f"{api}/repos/{repo}/issues", payload, h)
        if 200 <= code < 300:
            n += 1
            iss["n"] += 1
            a["alerted_issue"] = True
        else:
            log(f"  issue failed: HTTP {code} {msg[:100]}")
    return n


# ------------------------------------------------------------------ main pipeline
def run(feeds_cfg: dict, cfg: dict, state: dict, now: datetime.datetime, fetch=ts.fetch_url, force: bool = False,
        bootstrap: bool = False) -> dict:
    """One watch cycle (no I/O except `fetch`). Returns {'breaking': dict, 'alerts': [...], 'status': {...}, 'state': state}."""
    feeds = feeds_cfg.get("feeds") or []
    stories, trends, status = fetch_all(feeds, state, now, fetch, force)
    cutoff = now - datetime.timedelta(hours=MAX_ITEM_AGE_H)
    stories = [s for s in stories if not (ts.parse_dt(s["published"]) and ts.parse_dt(s["published"]) < cutoff)]
    clusters = ts.analyze(stories, trends, now, cfg)
    first_run = bool(state.get("firstRun")) or not state.get("items") or bootstrap
    seen = state.setdefault("items", [])
    alerts, new_count = [], 0
    for cl in clusters:
        info = classify(cl, cfg)
        rep = cl["rep"]
        rec = seen_match(cl, seen, cfg)
        keys = sorted({item_key({"url": m["url"]}) for m in cl["members"]})
        pub = rep["published"]
        for m in cl["members"]:
            if m["published"] and (pub is None or m["published"] > pub):
                pub = m["published"]
        fresh = pub is None or (now - pub).total_seconds() <= ALERT_MAX_AGE_H * 3600
        if rec is None:
            new_count += 1
            rec = {"id": hashlib.sha1((keys[0] if keys else rep["title"]).encode()).hexdigest()[:12], "firstSeen": iso(now),
                   "alerted": bool(first_run or not fresh), "keys": keys, "tok": sorted(frozenset().union(*[m["tok"] for m in cl["members"]]))}
            seen.append(rec)
            is_new = True
        else:
            is_new = False
            rec["keys"] = sorted(set(rec.get("keys", [])) | set(keys))
            rec["tok"] = sorted(set(rec.get("tok", [])) | set(frozenset().union(*[m["tok"] for m in cl["members"]])))
        last = ts.parse_dt(rec.get("lastSeen"))
        stale_seen = last is None or (now - last).total_seconds() > 3 * 3600  # avoid rewriting lastSeen every run (commit churn)
        rec.update({"title": rep["title"], "url": rep["url"], "source": rep["outlet"], "published": iso(pub),
                    **({"lastSeen": iso(now)} if stale_seen else {}),
                    "level": info["level"], "score": cl["score"], "label": cl["label"], "uncovered": cl["uncovered"],
                    "matches": info["matches"], "why": cl["why"], "reasons": info["reasons"], "always": info["always"],
                    "sources": [{"name": s["name"], "url": s["url"]} for s in cl["sources"][:8]]})
        if info["level"] == "alert" and not rec["alerted"] and fresh:
            alerts.append({"id": rec["id"], "title": rep["title"], "url": rep["url"], "source": rep["outlet"], "score": cl["score"],
                           "label": cl["label"], "uncovered": cl["uncovered"], "reasons": info["reasons"], "always": info["always"],
                           "why": cl["why"], "sources": rec["sources"], "rec": rec})
    state["firstRun"] = False
    keep_from = now - datetime.timedelta(hours=STATE_KEEP_H)
    heavy_from = now - datetime.timedelta(hours=STATE_HEAVY_H)
    state["items"] = [r for r in seen if (ts.parse_dt(r.get("lastSeen")) or now) >= keep_from][-1200:]
    for r in state["items"]:  # old records only need keys + tokens for duplicate detection
        if (ts.parse_dt(r.get("firstSeen")) or now) < heavy_from:
            for k in ("why", "reasons", "matches", "sources", "url"):
                r.pop(k, None)
    alerts.sort(key=lambda a: -a["score"])
    # breaking.json strip
    win = now - datetime.timedelta(hours=STRIP_WINDOW_H)
    strip = []
    for r in state["items"]:
        if r.get("level") in ("alert", "watch") and (ts.parse_dt(r.get("firstSeen")) or now) >= win:
            strip.append({k: r.get(k) for k in ("id", "title", "url", "source", "sources", "published", "firstSeen", "score", "label", "uncovered", "level", "matches", "why")})
    strip.sort(key=lambda r: (r["level"] != "alert", -(ts.parse_dt(r["firstSeen"]) or now).timestamp()))
    ok = sum(1 for s in status.values() if s["ok"])
    breaking = {
        "version": 1, "generatedAt": iso(now), "window_hours": STRIP_WINDOW_H, "bootstrap": bool(first_run),
        "note": "Public headlines and links only. Everything here is a lead: CONFIRM BEFORE AIR.",
        "counts": {"alert": sum(1 for r in strip if r["level"] == "alert"), "watch": sum(1 for r in strip if r["level"] == "watch"), "stories": len(clusters), "new": new_count},
        "feeds": {"ok": ok, "failed": sum(1 for s in status.values() if not s["ok"]), "total": len(status)},
        "trends": {"TX": len(trends.get("TX", [])), "US": len(trends.get("US", []))},
        "items": strip[:40],
    }
    return {"breaking": breaking, "alerts": alerts, "status": status, "state": state, "clusters": clusters}


def material(b: dict) -> str:
    """Breaking.json content that matters (ignores timestamps) for the 'only commit if changed' rule."""
    return json.dumps([(i["id"], i["level"], i["label"], bool(i.get("uncovered"))) for i in b["items"]], sort_keys=True)


def write_json(path: str, obj, compact: bool = False):
    """compact=True writes the state file with one item per line (small, diff-friendly commits)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            head = {k: v for k, v in obj.items() if k != "items"}
            f.write("{" + ",".join(json.dumps(k) + ":" + json.dumps(v, ensure_ascii=False, separators=(",", ":")) for k, v in head.items()) + ',"items":[\n')
            f.write(",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in obj["items"]))
            f.write("\n]}\n")
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
    os.replace(tmp, path)


def in_window(now: datetime.datetime, window: str) -> bool:
    from zoneinfo import ZoneInfo
    a, b = window.split("-")
    ct = now.astimezone(ZoneInfo("America/Chicago"))
    mins = ct.hour * 60 + ct.minute
    sh, sm = map(int, a.split(":"))
    eh, em = map(int, b.split(":"))
    return sh * 60 + sm <= mins < eh * 60 + em


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Breaking watch")
    ap.add_argument("--feeds", default=os.path.join(ROOT, "feeds.yml"))
    ap.add_argument("--state", default=os.path.join(ROOT, "state", "seen.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "breaking.json"))
    ap.add_argument("--dry-run", action="store_true", help="fetch + score; write nothing, send nothing (prints what it would do)")
    ap.add_argument("--no-alerts", action="store_true", help="write files but send no ntfy/issues")
    ap.add_argument("--bootstrap", action="store_true", help="record everything as already seen (no alerts)")
    ap.add_argument("--force", action="store_true", help="ignore feed back-off")
    ap.add_argument("--window", default="05:00-11:00", help="CT window for 15-minute polling; outside it only the first run of each hour does work ('' = always)")
    ap.add_argument("--now", help="ISO time override (tests)")
    ap.add_argument("--print-clusters", type=int, default=0, help="print the top N clusters")
    a = ap.parse_args(argv)
    now = ts.parse_dt(a.now) if a.now else now_utc()
    if a.window and not a.force and not in_window(now, a.window) and now.minute >= 15:
        log(f"off-window ({a.window} CT) and not the top of the hour: nothing to do")
        return 0
    feeds_cfg = ditm_yaml.load(a.feeds) or {}
    cfg = ts.load_config(ROOT if a.feeds == os.path.join(ROOT, "feeds.yml") else os.path.dirname(a.feeds))
    state = load_state(a.state)
    res = run(feeds_cfg, cfg, state, now, force=a.force, bootstrap=a.bootstrap)
    br, alerts, status = res["breaking"], res["alerts"], res["status"]
    log(f"feeds ok {br['feeds']['ok']}/{br['feeds']['total']} · stories {br['counts']['stories']} · new {br['counts']['new']} · strip alert {br['counts']['alert']} watch {br['counts']['watch']} · alerts to send {len(alerts)}{' (bootstrap run, none sent)' if br['bootstrap'] else ''}")
    for fid, s in status.items():
        log(f"  {'OK  ' if s['ok'] else ('warn' if s['optional'] else 'FAIL')} {fid:<22} {s['items']:>3} items  {s['status']}")
    for c in res["clusters"][: a.print_clusters]:
        log(f"  {c['score']:3d} {c['label']:<8}{' UNCOV' if c['uncovered'] else '      '} [{len(c['sources'])}] {c['rep']['title'][:88]}")
    ntfy_n = issue_n = 0
    if not a.no_alerts and alerts:
        ntfy_n = send_ntfy(alerts, dry=a.dry_run)
        issue_n = open_issues(alerts, state, dry=a.dry_run)
        # Mark alerted when delivered, when no channel is configured, or when it was covered by the
        # "+N more" summary. A failed delivery stays un-alerted and is retried next run (while still fresh).
        configured = bool(os.environ.get("NTFY_TOPIC")) or (os.environ.get("BREAKING_ISSUES") or "").lower() in ("1", "true", "yes", "on")
        if not a.dry_run:
            for i, al in enumerate(alerts):
                if not configured or al.get("alerted_ntfy") or al.get("alerted_issue") or (os.environ.get("NTFY_TOPIC") and i >= NTFY_PER_RUN):
                    for r in state["items"]:
                        if r["id"] == al["id"]:
                            r["alerted"] = True
    elif not a.dry_run and alerts:
        for al in alerts:
            for r in state["items"]:
                if r["id"] == al["id"]:
                    r["alerted"] = True
    for al in alerts[:8]:
        log(f"  ALERT {al['label']} {al['score']} {al['title'][:80]}  <- {'; '.join(al['reasons'])}")
    if a.dry_run:
        log("dry-run: no files written")
        print(json.dumps({"counts": br["counts"], "feeds": br["feeds"], "alerts": len(alerts), "top": [i["title"] for i in br["items"][:5]]}))
        return 0
    old = {}
    try:
        old = json.load(open(a.out))
    except Exception:
        pass
    changed = material(br) != material(old) if old.get("items") is not None else True
    stale = True
    og = ts.parse_dt(old.get("generatedAt"))
    if og and (now - og).total_seconds() < HEARTBEAT_MIN * 60:
        stale = False
    if changed or stale:
        write_json(a.out, br)
        log(f"wrote {os.path.relpath(a.out, ROOT) if a.out.startswith(ROOT) else a.out} ({'changed' if changed else 'heartbeat'})")
    prev_state = {}
    try:
        prev_state = json.load(open(a.state))
    except Exception:
        pass
    state["updated"] = prev_state.get("updated") or iso(now)
    if json.dumps(state, sort_keys=True) != json.dumps(prev_state, sort_keys=True):
        state["updated"] = iso(now)
        write_json(a.state, state, compact=True)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a") as f:
            f.write(f"### Breaking watch {iso(now)}\n\nfeeds {br['feeds']['ok']}/{br['feeds']['total']} ok · new {br['counts']['new']} · alert {br['counts']['alert']} · watch {br['counts']['watch']} · ntfy {ntfy_n} · issues {issue_n}\n\n| feed | items | status |\n|---|---|---|\n")
            for fid, s in status.items():
                f.write(f"| {fid} | {s['items']} | {s['status']} |\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
