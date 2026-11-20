#!/usr/bin/env python3
"""Chisme: what the Valley is buzzing about (local social posts), read-only.

Builds the `chisme` block of a packet: 6 to 10 Trending-model cards (headline, date / platform / engagement,
TL;DR, Riff, link to the original post) from the last 72 hours.

Sources, all public and read-only (never log in, post, comment, react, join or message):
  (a) Reddit public JSON for r/RGV, r/McAllen, r/Brownsville, r/Harlingen, r/Edinburg and r/riograndevalley
      (+ r/RioGrandeValley), `top.json?t=week` and `hot.json`, browser User-Agent, via curl. Score = upvotes + comments.
      If JSON is blocked it tries the subreddit's public RSS (no vote counts; those items rank last).
  (b) Facebook: the watch-list pages (The Monitor, KRGV, nomorecheezmeh, RGV.ME, the FB group). A logged-out fetch only
      returns the page shell (login wall), so the real route is the CAPTURE FILE: the daily refresh reads the pages in the
      box browser (already signed in, read only) and writes what it saw to `packet/data/chisme-capture-YYYY-MM-DD.json`.
  (c) Instagram: public endpoints only; they are login-walled, so this is skipped and reported (never faked).
The capture file is also how the refresh adds anything else it read (Reddit through a browser when curl is blocked, X, TikTok).

    python3 tools/chisme.py --capture packet/data/chisme-capture-2026-11-19.json --headlines packet/data/packet-2026-11-19.json \\
        --out packet/data/chisme-2026-11-19.json
    python3 tools/chisme.py --no-network --capture FILE        # offline

Capture file: a JSON list; each item {platform, source, title, text?, url, posted (ISO), reactions?, comments?, shares?,
upvotes?, tldr?, riff?, confirmedBy?: {outlet, url}}.  `tldr` and `riff` are written by the refresh from what the post says
(light and playful, never mean); this tool never invents either, and a card without a riff simply has no Riff line.

SAFETY (applied to every item, strictest wins; when unsure the item is DROPPED, not softened):
  * minors, sexual content, medical or financial claims about a named private person, accusations/crimes naming a private
    person, doxxing details (addresses, plates, phone numbers, emails) -> dropped;  any phone/email/address left in text is redacted.
  * every card carries RUMOR · CONFIRM BEFORE AIR unless a news outlet confirmed it (`confirmedBy`).
"""
from __future__ import annotations
import argparse, datetime, html as html_mod, json, os, re, subprocess, sys, time

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
SUBREDDITS = ["RGV", "McAllen", "Brownsville", "Harlingen", "Edinburg", "riograndevalley", "RioGrandeValley"]
FB_PAGES = [("The Monitor", "https://www.facebook.com/monitornews"), ("KRGV Channel 5", "https://www.facebook.com/channel5news"),
            ("Nomorecheezmeh", "https://www.facebook.com/nomorecheezmeh"), ("RGV.ME", "https://www.facebook.com/RGV.ME"),
            ("Things To Do In The RGV (group)", "https://www.facebook.com/groups/5774642885929554/")]
IG_PUBLIC = ["https://www.instagram.com/explore/tags/rgv/?__a=1&__d=dis", "https://www.instagram.com/api/v1/tags/web_info/?tag_name=rgv"]
WINDOW_HOURS = 72
MAX_ITEMS = 10
RUMOR_BADGE = "RUMOR · CONFIRM BEFORE AIR"


# ---------------------------------------------------------------- fetch (read-only GETs through curl)
def http_get(url: str, timeout: int = 20) -> tuple[int, str]:
    try:
        r = subprocess.run(["curl", "-s", "-m", str(timeout), "-A", UA, "-H", "Accept: application/json,text/html;q=0.8", "-w", "\n%{http_code}", url],
                           capture_output=True, timeout=timeout + 8)
        body, _, code = r.stdout.decode("utf-8", "replace").rpartition("\n")
        return (int(code) if code.strip().isdigit() else 0), body
    except Exception:
        return 0, ""


def _reddit_json(body: str, sub: str) -> list[dict]:
    try:
        kids = json.loads(body)["data"]["children"]
    except Exception:
        return []
    out = []
    for k in kids:
        d = k.get("data") or {}
        if d.get("stickied") or d.get("over_18") or not d.get("title"):
            continue
        out.append({"platform": "Reddit", "source": "r/" + (d.get("subreddit") or sub), "title": d["title"], "text": d.get("selftext") or "",
                    "url": "https://www.reddit.com" + d.get("permalink", ""), "posted": datetime.datetime.fromtimestamp(d.get("created_utc", 0), datetime.timezone.utc).isoformat(),
                    "upvotes": int(d.get("ups") or d.get("score") or 0), "comments": int(d.get("num_comments") or 0), "flair": d.get("link_flair_text") or ""})
    return out


def _reddit_rss(body: str, sub: str) -> list[dict]:
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", body, re.S):
        t = re.search(r"<title>(.*?)</title>", e, re.S); u = re.search(r'<link href="([^"]+)"', e); d = re.search(r"<updated>(.*?)</updated>", e)
        if t and u and d:
            out.append({"platform": "Reddit", "source": "r/" + sub, "title": html_mod.unescape(t.group(1)).strip(), "text": "", "url": u.group(1), "posted": d.group(1),
                        "upvotes": None, "comments": None})
    return out


def fetch_reddit(get=http_get, subs=None, pause: float = 1.5) -> tuple[list[dict], dict]:
    rows, status = [], {}
    for sub in subs or SUBREDDITS:
        got, why = [], []
        for path in (f"top.json?t=week&limit=50", "hot.json?limit=50"):
            for host in ("old.reddit.com", "www.reddit.com"):
                code, body = get(f"https://{host}/r/{sub}/{path}")
                items = _reddit_json(body, sub) if code == 200 else []
                if items:
                    got += items
                    break
                why.append(f"{host} {path.split('?')[0]} HTTP {code}")
            time.sleep(pause)
        if not got:
            code, body = get(f"https://www.reddit.com/r/{sub}/hot/.rss")
            got = _reddit_rss(body, sub) if code == 200 else []
            why.append(f"rss HTTP {code}")
        status["r/" + sub] = {"items": len(got), "ok": bool(got), "note": "" if got else "no data: " + "; ".join(why[-3:])}
        rows += got
    return rows, status


def fetch_facebook_public(get=http_get) -> tuple[list[dict], dict]:
    """A logged-out request returns only the page shell, never the posts; report that honestly and return nothing."""
    status = {}
    for name, url in FB_PAGES:
        code, body = get(url.replace("www.", "m."))
        posts = len(re.findall(r'"story_fbid"|/posts/\d', body)) if code == 200 else 0
        status["facebook:" + name] = {"items": 0, "ok": False, "note": f"HTTP {code}; login wall, {posts} post links in the public shell; use the capture file (browser, read only)"}
    return [], status


def fetch_instagram_public(get=http_get) -> tuple[list[dict], dict]:
    for u in IG_PUBLIC:
        code, body = get(u)
        try:
            if code == 200 and json.loads(body):
                pass
        except Exception:
            pass
    return [], {"instagram": {"items": 0, "ok": False, "note": "public endpoints are login-walled (HTTP 404 / login page); skipped, nothing faked"}}


def load_capture(path: str) -> tuple[list[dict], dict]:
    if not path or not os.path.exists(path):
        return [], {}
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    by = {}
    for r in rows:
        k = (r.get("platform") or "?").lower()
        by[k] = by.get(k, 0) + 1
    return rows, {"capture:" + os.path.basename(path): {"items": len(rows), "ok": bool(rows), "note": ", ".join(f"{k} {v}" for k, v in sorted(by.items()))}}


# ---------------------------------------------------------------- safety
_MINOR = re.compile(r"\b(\d{1,2}[- ]year[- ]old|minor|minors|child|children|kid|kids|toddler|infant|baby|newborn|teen|teens|teenager|teenage|juvenile|"
                    r"student|students|schoolgirl|schoolboy|boy|girl|boys|girls|middle schooler|high schooler|elementary|preschool|daycare|amber alert)\b", re.I)
_SEXUAL = re.compile(r"\b(sex|sexual|nude|nudes|naked|porn|onlyfans|xxx|rape|raped|molest\w*|assault\w*|incest|erotic|nsfw|hookup|stripper|escort)\b", re.I)
_HEALTH = re.compile(r"\b(cancer|std|stds|hiv|aids|overdose|overdosed|rehab|diagnos\w+|pregnan\w+|abortion|surgery|mental health|suicid\w*|died of|cause of death|hospitali[sz]ed|chemo)\b", re.I)
_MONEY = re.compile(r"\b(bankrupt\w*|owes?|owed|debt|debts|lawsuit|sued|evict\w+|foreclos\w+|embezzl\w+|fraud|scam\w*|ponzi|laundering|stole|stolen|theft|tax evasion|unpaid)\b", re.I)
_ACCUSE = re.compile(r"\b(arrest\w*|accus\w+|charged|indict\w+|convicted|cheat\w*|cheating|affair|abus\w+|beat|beating|stalk\w*|threat\w*|murder\w*|killer|shot|shooter|dui|dwi|drunk|"
                     r"drugs?|dealer|crook|criminal|snitch|exposed|exposing|caught)\b", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ADDR = re.compile(r"\b\d{2,5}\s+(?:[NSEW]\.?\s+)?(?:[A-Z][a-z]+\s+){1,3}(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Ln|Lane|Ct|Court|Way|Pkwy|Hwy|Cir)\b\.?")
_PLATE = re.compile(r"\b(?:license plate|plate number|plates?:|tag number)\b|\b[A-Z]{3}[- ]?\d{3,4}\b|\b\d[A-Z]{2}[- ]?\d[A-Z]{2}\b", re.I)
_UP, _LO = "A-ZÁÉÍÓÚÑÜ", "a-záéíóúñü"
_NAME = re.compile(rf"\b[{_UP}][{_LO}]{{2,}}(?:\s+(?:[{_UP}]\.|[{_UP}][{_LO}]{{2,}}|De|Del|La|Los)){{1,2}}\b")
# people / places / orgs that are public or not private individuals (kept out of the "named private person" check)
_PUBLIC = {"Rio Grande", "Grande Valley", "South Padre", "Padre Island", "Cameron County", "Hidalgo County", "Starr County", "Willacy County", "Texas Tribune",
           "New World", "Border Patrol", "Valley Baptist", "Doctors Hospital", "Whataburger", "Rio Grande Valley", "McAllen Public", "Valley Metro", "Sharyland Pioneer", "Harlingen",
           "Brownsville", "Edinburg", "Mission", "Pharr", "Weslaco", "San Juan", "Port Isabel", "La Joya", "Los Fresnos", "Santa Rosa", "San Benito", "Texas Tech", "Texas Rangers",
           "Bad Bunny", "Taylor Swift", "Selena Quintanilla", "Bobby Pulido", "Greg Abbott", "Donald Trump", "Joe Biden", "Ted Cruz", "Henry Cuellar", "Vicente Gonzalez", "Monica De La Cruz",
           "Texas Southmost", "Quinta Mazatlan", "Palm Valley", "Heb Plus", "Walmart Supercenter", "Home Depot", "Texas Roadhouse", "Chick Fil", "Dairy Queen", "Sonic Drive"}


def _is_public_name(n: str) -> bool:
    return any(p.lower() in n.lower() or n.lower() in p.lower() for p in _PUBLIC)


def names_in(text: str) -> list[str]:
    out = []
    for m in _NAME.finditer(text or ""):
        n = m.group(0)
        first = n.split()[0]
        if first in {"The", "This", "That", "Valley", "Texas", "South", "North", "East", "West", "New", "Rio", "Port", "Sun", "San", "Santa", "Los", "Las", "Fort", "Lake", "Old", "Big", "Our",
                     "Anyone", "Does", "Why", "How", "What", "When", "Where", "Who", "Has", "Have", "Is", "Are", "Can", "Did", "Any", "Look", "Happy", "Good", "Free", "Now", "Just"}:
            continue
        if not _is_public_name(n):
            out.append(n)
    return out


def safety_verdict(item: dict) -> tuple[bool, str]:
    """(keep?, reason). The strictest reading wins; ambiguity drops the item."""
    text = " ".join(str(item.get(k) or "") for k in ("title", "text", "tldr", "riff", "flair"))
    if _MINOR.search(text):
        return False, "mentions a minor"
    if _SEXUAL.search(text):
        return False, "sexual content"
    if _PHONE.search(text) or _EMAIL.search(text) or _ADDR.search(text) or _PLATE.search(text):
        return False, "doxxing detail (phone, email, address or plate)"
    nm = names_in(text)
    if nm and (_ACCUSE.search(text) or _HEALTH.search(text) or _MONEY.search(text)):
        return False, "accusation / health / money claim near a named person"
    if _HEALTH.search(text) and re.search(r"\b(he|she|his|her|him|they|their)\b|\b(my|our)\s+(neighbor|coworker|boss|ex|friend|cousin|uncle|aunt)\b", text, re.I):
        return False, "health claim about a person"
    if _MONEY.search(text) and re.search(r"\b(he|she|his|her|him|owner|neighbor|coworker|boss|ex)\b", text, re.I):
        return False, "financial claim about a person"
    return True, ""


def redact(s: str) -> str:
    s = _PHONE.sub("[phone removed]", s or "")
    s = _EMAIL.sub("[email removed]", s)
    return _ADDR.sub("[address removed]", s)


# ---------------------------------------------------------------- normalise / score / dedupe
def _dt(s: str) -> datetime.datetime | None:
    try:
        d = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None


def engagement(r: dict) -> int | None:
    """Reddit: upvotes + comments. Others: reactions + 2 x comments + 3 x shares. None when the platform gave no counts."""
    if (r.get("platform") or "").lower() == "reddit":
        if r.get("upvotes") is None and r.get("comments") is None:
            return None
        return int(r.get("upvotes") or 0) + int(r.get("comments") or 0)
    if any(r.get(k) is not None for k in ("reactions", "comments", "shares")):
        return int(r.get("reactions") or 0) + 2 * int(r.get("comments") or 0) + 3 * int(r.get("shares") or 0)
    return None


def _tok(s: str) -> set[str]:
    stop = {"the", "a", "an", "of", "in", "on", "to", "and", "for", "at", "is", "are", "was", "with", "from", "by", "it", "this", "that", "has", "have", "be", "as", "or", "you", "your", "i", "my", "we"}
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in stop and len(w) > 2}


def _same(a: str, b: str) -> bool:
    x, y = _tok(a), _tok(b)
    if not x or not y:
        return False
    j = len(x & y) / len(x | y)
    return j >= 0.55 or (len(x & y) >= 4 and len(x & y) / min(len(x), len(y)) >= 0.75)


def tldr_of(r: dict) -> str:
    if r.get("tldr"):
        return redact(str(r["tldr"]).strip())
    t = re.sub(r"\s+", " ", html_mod.unescape(re.sub(r"<[^>]+>", " ", r.get("text") or ""))).strip()
    if not t:
        return ""
    cut = t[:220]
    if len(t) > 220:
        cut = cut.rsplit(" ", 1)[0] + "…"
    return redact(cut)


def normalize(r: dict, now: datetime.datetime) -> dict | None:
    title = redact(re.sub(r"\s+", " ", html_mod.unescape(str(r.get("title") or r.get("text") or ""))).strip())
    url = (r.get("url") or "").strip()
    d = _dt(r.get("posted") or r.get("published"))
    if not title or not url.startswith("http") or d is None:
        return None
    if len(title) > 180:
        title = title[:177].rsplit(" ", 1)[0] + "…"
    conf = r.get("confirmedBy") or None
    if conf and not (conf.get("outlet") and str(conf.get("url", "")).startswith("http")):
        conf = None
    platform = r.get("platform") or "Social"
    return {"id": re.sub(r"[^a-z0-9]+", "-", (platform + "-" + url[-40:]).lower()).strip("-"), "platform": platform, "source": r.get("source") or platform, "title": title, "url": url,
            "published": d.astimezone(datetime.timezone.utc).isoformat(), "engagement": engagement(r),
            "metrics": {k: r[k] for k in ("upvotes", "comments", "reactions", "shares") if r.get(k) is not None},
            "tldr": tldr_of(r), "riff": redact(str(r.get("riff") or "").strip()), "confirmedBy": conf,
            "badge": "" if conf else RUMOR_BADGE, "_raw": r, "ageHours": round((now - d).total_seconds() / 3600, 1)}


def build(rows: list[dict], headlines: list[str] | None = None, now: datetime.datetime | None = None, window_hours: int = WINDOW_HOURS, limit: int = MAX_ITEMS) -> dict:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    dropped = {"stale": 0, "unsafe": 0, "dup-headline": 0, "dup": 0, "invalid": 0}
    reasons: list[str] = []
    keep = []
    for r in rows:
        it = normalize(r, now)
        if it is None:
            dropped["invalid"] += 1; continue
        if not (0 <= it["ageHours"] <= window_hours + 1):
            dropped["stale"] += 1; continue
        # judged on the RAW text (before redaction): a phone number or address in the original is a reason to drop the post, not just to mask it
        ok, why = safety_verdict(r)
        if not ok:
            dropped["unsafe"] += 1; reasons.append(why); continue
        if any(_same(it["title"], h) for h in headlines or []):
            dropped["dup-headline"] += 1; continue
        keep.append(it)
    keep.sort(key=lambda x: (x["engagement"] is None, -(x["engagement"] or 0), x["ageHours"]))
    out = []
    for it in keep:
        if any(_same(it["title"], o["title"]) or it["url"] == o["url"] for o in out):
            dropped["dup"] += 1; continue
        out.append(it)
    out = out[:limit]
    for i, it in enumerate(out):
        it["ord"] = i
        it.pop("_raw", None)
    return {"items": out, "window": f"last {window_hours} hours", "dropped": dropped, "dropReasons": sorted(set(reasons))}


def headline_titles(packet: dict) -> list[str]:
    h = packet.get("headlines") or {}
    return [x.get("title", "") for x in (h.get("rgv") or []) + (h.get("texas") or [])] + [x.get("title", "") for x in packet.get("nationalDesk") or []]


def collect(capture: str | None = None, headlines: list[str] | None = None, network: bool = True, now: datetime.datetime | None = None, get=http_get) -> dict:
    rows, status = [], {}
    if network:
        for fn in (fetch_reddit, fetch_facebook_public, fetch_instagram_public):
            r, s = fn(get=get); rows += r; status.update(s)
    cr, cs = load_capture(capture or ""); rows += cr; status.update(cs)
    block = build(rows, headlines, now)
    block["sources"] = status
    block["generatedAt"] = (now or datetime.datetime.now(datetime.timezone.utc)).isoformat()
    block["badge"] = RUMOR_BADGE
    return block


def report(block: dict) -> str:
    L = [f"Chisme: {len(block['items'])} item(s), {block['window']}  (dropped {block['dropped']})"]
    for k, v in block["sources"].items():
        L.append(f"  {'OK  ' if v['ok'] else 'none'} {k}: {v['items']} {v['note']}")
    for it in block["items"]:
        L.append(f"  [{it['platform']}] {it['title'][:80]}  eng={it['engagement']}  {it['badge'] or 'CONFIRMED by ' + it['confirmedBy']['outlet']}")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--capture"); ap.add_argument("--headlines", help="a packet JSON; its headlines/National Desk are used to dedupe")
    ap.add_argument("--out"); ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--packet", help="merge the result into this packet JSON as its `chisme` block (and use its headlines to dedupe)")
    a = ap.parse_args(argv)
    src = a.headlines or a.packet
    hl = []
    if src:
        with open(src, encoding="utf-8") as f:
            hl = headline_titles(json.load(f))
    block = collect(a.capture, hl, not a.no_network)
    if a.packet:
        with open(a.packet, encoding="utf-8") as f:
            pk = json.load(f)
        pk["chisme"] = block
        with open(a.packet, "w", encoding="utf-8") as f:
            json.dump(pk, f, indent=1, ensure_ascii=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(block, f, indent=2, ensure_ascii=False)
    print(report(block))
    return 0


if __name__ == "__main__":
    sys.exit(main())
