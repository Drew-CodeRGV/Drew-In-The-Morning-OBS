#!/usr/bin/env python3
"""DITM Monday show packet generator.

ONE command builds everything from ONE data file:
    python3 build_packet.py data/packet-2026-11-23.json [--refresh-weather] [--check-links] [--obs-data ../obs-data.json]

Outputs (out/DITM-packet-<date>[-SAMPLE].*):
    .json            normalized single source of truth (weather + show clock merged in, every item with its URL)
    .pdf             ONE-PAGE Letter-landscape infographic (print + attachment)
    .png             page-1 preview of the PDF
    .txt             plain text, every URL listed
    -email.html      inline-styled HTML email body (logo via cid:ditm-logo; attach assets/DITM_SunLogo.png inline)
    -email-preview.html   same with images embedded (for viewing in a browser)
    -studio.html     self-contained interactive studio page (inline CSS/JS, images embedded, works offline)
    -studio.png      screenshot of the studio page
    -sources.txt     every source URL grouped by section
Nothing is ever sent or posted by this script.
"""
import argparse, base64, concurrent.futures, datetime, hashlib, html, json, os, re, shutil, subprocess, sys, textwrap, urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
esc = lambda s: html.escape(str(s), quote=True)
UA = "DITM-packet/1.0 (drew@drewlentz.com)"
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser") or "google-chrome"

REPO = "Drew-CodeRGV/Drew-In-The-Morning-OBS"

# dedupe + trend score (tools/trend_score.py). Optional: the build still works without it.
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
try:
    import obituaries as OB
except Exception:  # the section then says nothing was loaded
    OB = None
try:
    import trend_score as TS
except Exception:  # pragma: no cover
    TS = None
OPTS = {"fetch_trends": False, "score": True, "enrich_synopses": False}

# ---------------------------------------------------------------- weather
def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/geo+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def icon_kind(short):
    s = short.lower()
    if "thunder" in s: return "storm"
    if "rain" in s or "shower" in s or "drizzle" in s: return "rain"
    if "partly" in s or "mostly sunny" in s or "mostly clear" in s: return "partly"
    if "cloud" in s or "overcast" in s: return "cloud"
    return "sun"

def current_conditions(pts):
    """Build-time current temperature: KMFE latest observation, else the NWS hourly forecast (same logic as the studio clock widget)."""
    try:
        o = fetch_json("https://api.weather.gov/stations/KMFE/observations/latest")["properties"]
        c = o["temperature"]["value"]
        if c is not None:
            return {"tempF": round(c * 9 / 5 + 32), "cond": o.get("textDescription") or "", "icon": icon_kind(o.get("textDescription") or ""), "at": o["timestamp"], "source": "KMFE observation"}
    except Exception:
        pass
    try:
        h = fetch_json(pts["forecastHourly"])["properties"]; p0 = h["periods"][0]
        return {"tempF": p0["temperature"], "cond": p0["shortForecast"], "icon": icon_kind(p0["shortForecast"]), "at": p0["startTime"], "source": "NWS hourly forecast"}
    except Exception:
        return None

def refresh_weather(w, start_date=None):
    pts = fetch_json(f"https://api.weather.gov/points/{w['lat']},{w['lon']}")["properties"]
    fc = fetch_json(pts["forecast"])["properties"]
    periods = fc["periods"]
    days, i = [], 0
    byday = {}
    for p in periods:
        d = p["startTime"][:10]
        byday.setdefault(d, {})["day" if p["isDaytime"] else "night"] = p
    for d in sorted(byday):
        x = byday[d]
        if "day" not in x: continue
        dt = datetime.date.fromisoformat(d)
        days.append({"date": d, "label": dt.strftime("%a"), "dateLabel": dt.strftime("%b %-d"),
                     "hi": x["day"]["temperature"], "lo": x.get("night", {}).get("temperature"),
                     "short": x["day"]["shortForecast"], "icon": icon_kind(x["day"]["shortForecast"]),
                     "pop": max([(x[k]["probabilityOfPrecipitation"]["value"] or 0) for k in x]),
                     "wind": f"{x['day']['windDirection']} {x['day']['windSpeed']}"})
    try:
        al = fetch_json(f"https://api.weather.gov/alerts/active?point={w['lat']},{w['lon']}")
        alerts = [a["properties"]["event"] for a in al.get("features", [])]
    except Exception:
        alerts = None
    w["now"] = current_conditions(pts)
    w.update({"office": pts["gridId"], "city": pts["relativeLocation"]["properties"]["city"], "updated": fc["updateTime"],
              "days": days, "alerts": alerts,
              "pageUrl": f"https://forecast.weather.gov/MapClick.php?lat={w['lat']}&lon={w['lon']}",
              "officeUrl": f"https://www.weather.gov/{pts['gridId'].lower()}/", "apiUrl": pts["forecast"],
              "source": f"National Weather Service {pts['gridId']} (api.weather.gov)"})
    return w

# ---------------------------------------------------------------- prep
def prepare(data, obs_path, do_weather):
    m = data["meta"]
    d = datetime.date.fromisoformat(m["date"])
    mode = m.get("mode") or ("monday" if d.weekday() == 0 else "daily")
    assert mode in ("monday", "daily"), "meta.mode must be monday or daily"
    m["mode"] = mode
    m["dateLabel"] = d.strftime("%A, %B %-d, %Y")
    nm = d + datetime.timedelta(days=(7 - d.weekday()) % 7 or 7)
    m["nextShow"] = {"date": nm.isoformat(), "label": nm.strftime("%A, %B %-d"), "short": nm.strftime("%a %b %-d")}
    if mode == "monday":
        m["title"] = "Drew in the Morning · Monday Show Packet"; m["kicker"] = "Monday Show Packet · 8 AM CT"
        m["recap"] = m.get("recap") or "Week and weekend recap"; m["hlSub"] = "week + weekend"; m["todayLabel"] = "Show morning"
        prefix, subj = "DITM-packet", f"Monday Show Packet · {m['dateLabel']} (8 AM CT)"
    else:
        m["title"] = "Drew in the Morning · Daily Briefing"; m["kicker"] = "Daily Briefing · 6 AM CT"
        m["recap"] = m.get("dailyRecap") or ("The weekend" if d.weekday() >= 5 else "Last 24 hours")
        m["hlSub"] = m["recap"].lower(); m["todayLabel"] = "Today"
        prefix, subj = "DITM-briefing", f"Daily Briefing · {m['dateLabel']}"
    m["fileStem"] = f"{prefix}-{m['date']}" + ("-SAMPLE" if m.get("sample") else "")
    m["emailSubject"] = ("[SAMPLE] " if m.get("sample") else "") + subj
    m["headline"] = (f"DAILY BRIEFING · {m['dateLabel']}" if mode == "daily" else f"MONDAY SHOW PACKET · {m['dateLabel']}")
    w = data["weather"]
    if do_weather or "days" not in w:
        refresh_weather(w)
    w["monday"] = m["date"]
    # show clock + rundown from the run-of-show source of truth
    if obs_path and os.path.exists(obs_path):
        obs = json.load(open(obs_path))
        nxt = {x["fromLetter"]: x["line"] for x in obs["segues"] if x.get("kind") == "adjacent"}
        data["showClock"] = [{"letter": s["letter"], "id": s["id"], "title": s["title"], "short": s.get("shortName") or s["title"][:12],
                              "start": s["start"], "end": s["end"], "timeRange": s["timeRange"], "minutes": s["durationMinutes"], "offset": s["offsetMinutes"],
                              "flex": s["flex"], "trimTo": s["canTrimToMinutes"], "stretchTo": s["canStretchToMinutes"],
                              "jess": s["jessDropIn"], "signature": s["signature"], "color": s["color"]} for s in obs["segments"]]
        data["rundown"] = [{"letter": s["letter"], "title": s["title"], "short": s.get("shortName") or s["title"][:12], "subject": s["subject"], "timeRange": s["timeRange"],
                            "minutes": s["durationMinutes"], "offset": s["offsetMinutes"], "flex": s["flex"], "trimTo": s["canTrimToMinutes"], "stretchTo": s["canStretchToMinutes"],
                            "color": s["color"], "jess": s["jessDropIn"], "signature": s["signature"], "weave": s.get("weave"),
                            "talkingPoints": s["talkingPoints"], "followUps": s["followUpQuestions"], "transitions": s["transitionLines"], "segueNext": nxt.get(s["letter"], ""),
                            "chyrons": s["chyrons"], "links": s["links"], "confirm": s["needsVerification"]} for s in obs["segments"]]
        data["segues"] = [x["line"] for x in obs["segues"] if x.get("kind") == "jump"][:8]
    assert sum(s["minutes"] for s in data.get("showClock", [])) in (0, 60), "show clock must total 60 minutes"
    # every item needs a URL, else flag
    def fix(item):
        if isinstance(item, dict) and "title" in item and not item.get("url") and not item.get("links"):
            item["confirm"] = (item.get("confirm") or "") + " NO VERIFIED LINK: CONFIRM BEFORE AIR"
    for k in ("rgv", "texas"): [fix(i) for i in data["headlines"][k]]
    for n in data["nationalDesk"]: fix(n)
    hs = data["sports"]["highSchool"]
    [fix(i) for i in hs["results"] + hs["next"]]
    m["showDate"] = m["date"] if mode == "monday" else m["nextShow"]["date"]
    prep_up_to(data); prep_trending(data); prep_tech(data); prep_obituaries(data); prep_chisme(data); score_stage(data); data["coldOpen"] = build_cold_open(data)
    for r in data.get("rundown", []):
        if r["letter"] == "A":
            r["talkingPoints"] = ["TODAY'S COLD OPEN (auto-filled, read aloud): " + data["coldOpen"]["text"], "JINGLE: " + data["coldOpen"]["jingle"]] + r["talkingPoints"]
        if r["letter"] == "B":
            ev = upto_lines(data)
            r["talkingPoints"] = (["READ ALOUD (auto-built from the family calendar, generic wording): " + data["up_to_script"]]
                                  + ([f"FROM THE CALENDAR: {x}" for x in ev] if ev else ["QUIET WEEK on the family calendar; the script above says so and gives Jess an easy riff. Do not make something up."])
                                  + r["talkingPoints"])
        if r["letter"] == "L" and data["obituaries"]["script"]:
            tp = r["talkingPoints"]
            at = next((i for i, x in enumerate(tp) if x.startswith("REMEMBERING OUR NEIGHBORS")), len(tp) - 1) + 1
            tp.insert(at, "READ ALOUD, SLOWLY (auto-built from The Monitor's obituaries; CONFIRM name pronunciations): " + data["obituaries"]["script"])
    return data


# ---------------------------------------------------------------- dedupe + trend score
SCORE_FORMULA = ("score = outlets(6 per distinct outlet, max 30) + recency(20 x 0.5^(age_h/12)) + X(20 x min(1, log10(1+eng+25 posts)/4)) "
                 "+ Google Trends(20 TX / 12 US) + chatter(10 x min(1, log10(1+eng+5 posts)/2.5)); Hot >= 45, Trending >= 27, else Active")


def score_stage(data):
    """Cluster near-duplicate stories, score them, label Hot/Trending/Active, flag Uncovered; sort lists by score."""
    data["scoring"] = None
    if TS is None or not OPTS["score"] or data["meta"].get("score") is False:
        return
    cache = os.path.join(HERE, "data", "trends-cache.json")
    trends = TS.fetch_trends(cache_path=cache) if OPTS["fetch_trends"] else TS.load_trends_cache(cache)
    if not (trends.get("TX") or trends.get("US")):
        trends = None
    cfg = TS.load_config(os.path.join(HERE, ".."))
    hl = data["headlines"]; img = hl.get("image")
    printable = [x for x in hl["rgv"] if not x.get("noprint")]
    target = printable[img["forItem"]] if img and isinstance(img.get("forItem"), int) and img["forItem"] < len(printable) else None
    summ = TS.score_packet(data, trends, cfg=cfg, sort=False)   # keeps the editorial order; the studio sorts by score itself
    # PDF / email / txt keep the editorial order (and the thumbnail stays on ITS story), except Hot items go to the front
    for lst in (data["nationalDesk"], hl["rgv"], hl["texas"], data.get("trending") or [], data.get("leads") or []):
        lst.sort(key=lambda it: (0 if it.get("label") == "Hot" else 1, it.get("ord", 0)))
    if target is not None:
        printable = [x for x in hl["rgv"] if not x.get("noprint")]
        img["forItem"] = next((k for k, x in enumerate(printable) if x is target), -1)
    summ["formula"] = SCORE_FORMULA
    summ["trendsNote"] = ("Google Trends not available (no fetch, no fresh cache): trends signal = 0" if trends is None else
                          f"Google Trends US-TX {len(trends['TX'])} + US {len(trends['US'])} items, fetched {trends.get('fetchedAt')}{' (cache)' if trends.get('fromCache') else ''}")
    data["scoring"] = summ


SBL = {"Hot": ("HOT", "h", "#c1121f"), "Trending": ("TREND", "t", "#e4572e"), "Active": ("ACT", "a", "#9aa6b2")}


def sc_print(it):
    # the one-page PDF only marks what matters: HOT / TREND / UNCOV (Active items stay unmarked so the page stays quiet)
    if not it.get("label"): return ""
    t, c, _ = SBL[it["label"]]
    mk = {"Hot": "HOT", "Trending": "\u25b2"}.get(it["label"], "")   # ▲ keeps the national lines short enough that CONFIRM does not wrap
    return (f'<span class="sb {c}">{mk}</span>' if mk else "") + ('<span class="sb u">UNCOV</span>' if it.get("uncovered") else "")


def sc_email(it):
    if not it.get("label"): return ""
    t, _, col = SBL[it["label"]]
    st = "font:700 10px Arial,sans-serif;padding:1px 5px;border-radius:3px;color:#fff;vertical-align:1px"
    return (f'<span style="background:{col};{st}">{t} {it["score"]}</span> ' +
            (f'<span style="background:#6f42c1;{st}">UNCOVERED</span> ' if it.get("uncovered") else ""))


def sc_txt(it):
    if not it.get("label"): return ""
    return f"[{SBL[it['label']][0]} {it['score']}] " + ("[UNCOVERED LEAD: CONFIRM BEFORE AIR] " if it.get("uncovered") else "")


def sc_studio(it):
    if not it.get("label"): return ""
    t, c, _ = SBL[it["label"]]
    srcs = it.get("sources") or []
    more = f'<span class="src" title="{esc(", ".join(x["name"] for x in srcs))}"> +{len(srcs) - 1} source{"s" if len(srcs) > 2 else ""}</span>' if len(srcs) > 1 else ""
    return (f'<span class="sb {c}" title="{esc(it.get("scoreWhy", ""))}">{t} {it["score"]}</span>' +
            ('<span class="sb u" title="Social/community buzz, no local outlet has it. Verify before air.">UNCOVERED</span>' if it.get("uncovered") else "") + more)


def sc_agg(items):
    """(count, badge html) for a section header: Hot/Trend/Uncovered/Confirm tallies."""
    items = [i for i in items if i]
    hot = sum(1 for i in items if i.get("label") == "Hot"); trd = sum(1 for i in items if i.get("label") == "Trending")
    unc = sum(1 for i in items if i.get("uncovered")); cf = sum(1 for i in items if i.get("confirm"))
    b = (f'<span class="sb h">{hot} HOT</span>' if hot else "") + (f'<span class="sb t">{trd} TREND</span>' if trd else "") + \
        (f'<span class="sb u">{unc} UNCOVERED</span>' if unc else "") + (f'<span class="cf">{cf} CONFIRM</span>' if cf else "")
    return len(items), b


# ---------------------------------------------------------------- rolling 7-day news window (studio dashboard only; never invents items)
WEEK_DAYS = 7

def norm_story_url(url):
    """Canonical URL for dedupe and remove-ids: host lowercased, no www, no trailing slash, no tracking params."""
    u = (url or "").strip()
    if not u:
        return ""
    try:
        p = urllib.parse.urlparse(u)
        q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid", "ocid", "mc_cid", "mc_eid")]
        path = (p.path or "").rstrip("/")
        netloc = (p.netloc or "").lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return urllib.parse.urlunparse(((p.scheme or "https").lower(), netloc, path, "", urllib.parse.urlencode(q), ""))
    except Exception:
        return u.rstrip("/").lower()

def norm_story_headline(title):
    return re.sub(r"\s+", " ", (title or "").casefold()).strip()

def _story_url(it):
    if it.get("url"):
        return it["url"]
    if it.get("source_url"):
        return it["source_url"]
    links = it.get("links") or []
    if links and isinstance(links, list) and isinstance(links[0], dict):
        return links[0].get("url") or ""
    return ""

def story_dedupe_key(it):
    u = norm_story_url(_story_url(it))
    if u:
        return ("u", u)
    t = norm_story_headline(it.get("title") or it.get("headline") or it.get("short") or "")
    return ("t", t)

def story_remove_id(it):
    """Stable across days and rebuilds: r- + sha1 of URL or normalized headline."""
    kind, val = story_dedupe_key(it)
    if not val:
        val = "empty"
    return "r-" + hashlib.sha1(f"{kind}:{val}".encode("utf-8")).hexdigest()[:16]

def story_when(it, packet_date=None):
    raw = it.get("published") or ""
    if raw:
        try:
            dt = datetime.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-6)))
            return dt.astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
        except Exception:
            pass
    if packet_date:
        if isinstance(packet_date, str):
            packet_date = datetime.date.fromisoformat(packet_date[:10])
        return datetime.datetime(packet_date.year, packet_date.month, packet_date.day, 12, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-6)))
    return None

def story_date_tag(it, packet_date=None):
    when = story_when(it, packet_date)
    return when.strftime("%b %-d") if when else ""

# Studio synopsis: 2–3 sentences, ~250–400 characters, from real article text only. Never invent.
SYNOPSIS_LIMIT = 400
_SYNOPSIS_FIELDS = ("tldr", "summary", "description", "dek", "excerpt", "one_line", "text", "body", "what", "_fetched_desc")


def _plain_text(t):
    t = re.sub(r"<[^>]+>", " ", str(t or ""))
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def _norm_cmp(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def _is_title_echo(text, title):
    """True when the text is just the headline (or a shorter rewrite), not a synopsis."""
    a, b = _norm_cmp(text), _norm_cmp(title)
    if not a:
        return True
    if not b:
        return False
    if a == b:
        return True
    if a in b and len(a) <= len(b) + 10:
        return True
    if b in a and len(a) <= len(b) + 10:
        return True
    return False


def trim_synopsis(text, limit=SYNOPSIS_LIMIT):
    """Keep up to 3 sentences or `limit` characters, breaking at a sentence or word."""
    text = _plain_text(text)
    if not text or len(text) <= limit:
        return text
    sents = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for sent in sents:
        if not sent:
            continue
        nxt = (" ".join(out + [sent])).strip()
        if len(nxt) <= limit and len(out) < 3:
            out.append(sent)
            continue
        break
    if out and (len(" ".join(out)) >= min(180, limit // 2) or len(sents) <= 3):
        return " ".join(out)
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-–—")
    return (cut or text[:limit]) + "…"


def story_synopsis(it, limit=SYNOPSIS_LIMIT):
    """Best real synopsis already on the item. Empty if only a headline exists. Never invents."""
    if not isinstance(it, dict):
        return ""
    title = _plain_text(it.get("title") or it.get("headline") or "")
    cands = []
    for key in _SYNOPSIS_FIELDS:
        val = _plain_text(it.get(key) or "")
        if val and not _is_title_echo(val, title):
            cands.append(val)
    for key in ("short", "teaser"):
        val = _plain_text(it.get(key) or "")
        if val and len(val) >= 80 and not _is_title_echo(val, title):
            cands.append(val)
    if not cands:
        return ""
    text = max(cands, key=len)
    return trim_synopsis(text, limit)


def _meta_content(html_text, names):
    """Read a meta content= value for any of the given property/name tokens."""
    for name in names:
        name_re = re.escape(name)
        pats = (
            rf'<meta\b[^>]+(?:property|name)=["\']{name_re}["\'][^>]*?content=["\']([^"\']+)["\']',
            rf'<meta\b[^>]+content=["\']([^"\']+)["\'][^>]*?(?:property|name)=["\']{name_re}["\']',
        )
        for pat in pats:
            m = re.search(pat, html_text, re.I)
            if m:
                val = _plain_text(m.group(1))
                if val:
                    return val
    return ""


def fetch_story_description(url, timeout=8):
    """Read-only public fetch of og:description / meta description. Empty on failure. Never invents."""
    if not str(url or "").startswith("https://"):
        return ""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if getattr(r, "status", 200) >= 400:
                return ""
            raw = r.read(200_000)
    except Exception:
        return ""
    try:
        body = raw.decode("utf-8", "replace")
    except Exception:
        return ""
    desc = _meta_content(body, ("og:description", "twitter:description", "description"))
    return desc


def enrich_synopses(items, fetch=fetch_story_description, min_len=250, limit=SYNOPSIS_LIMIT):
    """Fill short synopses from a public page description. Mutates items in place. Soft-fails."""
    jobs = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        have = story_synopsis(it, limit)
        if len(have) >= min_len:
            continue
        url = it.get("url") or it.get("source_url") or _story_url(it)
        if str(url).startswith("https://"):
            jobs.append((it, url, have))
    if not jobs:
        return 0
    filled = 0

    def one(job):
        it, url, have = job
        desc = fetch(url) or ""
        return it, have, desc

    workers = min(6, len(jobs))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for it, have, desc in pool.map(one, jobs):
            desc = _plain_text(desc)
            if desc and len(desc) > len(have) and not _is_title_echo(desc, it.get("title") or it.get("headline") or ""):
                it["_fetched_desc"] = desc
                filled += 1
    return filled

def _packet_file_for_day(root, day):
    iso = day.isoformat() if hasattr(day, "isoformat") else str(day)
    for path in (
        os.path.join(root, "packet", "data", f"packet-{iso}.json"),
        os.path.join(root, "packet", "out", f"DITM-briefing-{iso}.json"),
    ):
        if os.path.isfile(path) and "SAMPLE" not in os.path.basename(path):
            return path
    return None

def extract_news_lists(pkt):
    """News desks only (not obits, memes, sports, weather, or the family calendar)."""
    hl = pkt.get("headlines") or {}
    tech = pkt.get("tech") or {}
    items = tech.get("items") if isinstance(tech, dict) else (tech or [])
    ch = pkt.get("chisme") or {}
    return {
        "rgv": list(hl.get("rgv") or []),
        "texas": list(hl.get("texas") or []),
        "national": list(pkt.get("nationalDesk") or []),
        "trending": list(pkt.get("trending") or []),
        "tech": list(items or []),
        "chisme": list(ch.get("items") or []),
    }

def merge_week_news(data, root, today, days=WEEK_DAYS):
    """Merge news story items from today plus the prior (days-1) days of packets already on disk.
    Dedupes by URL / normalized headline (keeps the newest copy). Drops stories older than the window.
    Does not invent items and does not mutate `data`. Missing days are listed in the result."""
    if isinstance(today, str):
        today = datetime.date.fromisoformat(today[:10])
    start = today - datetime.timedelta(days=days - 1)
    found, missing, paths = [], [], []
    for i in range(days):
        day = today - datetime.timedelta(days=i)
        path = _packet_file_for_day(root, day)
        if path:
            found.append(day)
            paths.append((day, path))
        else:
            missing.append(day)
    buckets = {k: [] for k in ("rgv", "texas", "national", "trending", "tech", "chisme")}
    seen = {k: set() for k in buckets}

    def add(kind, it, packet_date):
        if not isinstance(it, dict):
            return
        if not (it.get("title") or it.get("headline") or it.get("short")):
            return
        when = story_when(it, packet_date)
        if when and when.date() < start:
            return
        key = story_dedupe_key(it)
        if not key[1] or key in seen[kind]:
            return
        row = dict(it)
        row["_packet_date"] = packet_date.isoformat() if hasattr(packet_date, "isoformat") else str(packet_date)
        row["_date_tag"] = story_date_tag(it, packet_date)
        row["_when"] = int(when.timestamp()) if when else 0
        row["_rmid"] = story_remove_id(it)
        buckets[kind].append(row)
        seen[kind].add(key)

    # Newest first so an older packet cannot replace today's copy of the same story.
    today_lists = extract_news_lists(data or {})
    if today not in found:
        found.insert(0, today)
    for kind, items in today_lists.items():
        for it in items:
            add(kind, it, today)
    for day, path in paths:
        if day == today:
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                pkt = json.load(fh)
        except Exception:
            if day not in missing:
                missing.append(day)
            continue
        for kind, items in extract_news_lists(pkt).items():
            for it in items:
                add(kind, it, day)
    for kind in buckets:
        buckets[kind].sort(key=lambda r: (r.get("_when") or 0, r.get("title") or ""), reverse=True)
    return {**buckets, "found": found, "missing": missing, "window": (start, today)}


# ---------------------------------------------------------------- assign existing headlines to rundown blocks D–I (best fit, no duplicates)
# Family & Kids (H) is stories that apply to kids and teens 6–18 and their parents, family-friendly only.
# Lifestyle is the newspaper-style page: obituaries, marriages, births, student honors (not a lettered A–L block).
_SEG_H_NO = re.compile(r"\b(murder|homicide|killing|killings|killed|sentenced|wrongful-?death|shooting|rape|assault|suicide|overdose|died|death suit)\b", re.I)
_SEG_H_YES = re.compile(r"\b(library|holiday parade|parade|festival|thanksgiving celebration|friends['’] thanksgiving|palenque|community celebration|public park|city park|parks department|how we['’]d talk|youth program|family night)\b", re.I)
_SEG_H_KIDS = re.compile(
    r"\b(uber)\b.{0,50}\b(kid|kids|teen|teens|child|children|minor|minors|as young as)\b"
    r"|\b(kid|kids|teen|teens|child|children|minor|minors|as young as)\b.{0,50}\buber\b"
    r"|\brides for (kids|teens|children)\b"
    r"|\bgta\s*(vi|6|v)?\b|\bgrand theft auto\b"
    r"|\b(roblox|fortnite|minecraft|nintendo|playstation|\bxbox\b|switch 2)\b"
    r"|\bvideo games?\b|\bconsole games?\b"
    r"|\btiktok\b.{0,40}\b(kid|kids|teen|teens|minor|minors|child|children|parental)\b"
    r"|\b(kid|kids|teen|teens|minor|minors|child|children)\b.{0,40}\btiktok\b"
    r"|\bsocial media\b.{0,40}\b(kid|kids|teen|teens|minor|minors|child|children)\b"
    r"|\bparental controls?\b|\bscreen time\b|\bback-?to-?school\b"
    r"|\byouth (sports|program|league|soccer|baseball|football|basketball)\b"
    r"|\b(toys?|toy fair)\b|\bpercy jackson\b"
    r"|\bas young as \d{1,2}\b|\bkids as young as\b",
    re.I,
)
_SEG_LIFE = re.compile(
    r"\b(student of the week|students of the week|athlete of the week|athletes of the week|"
    r"honor roll|principal['’]?s list|dean['’]?s list|"
    r"birth announcement|welcome[sd]? a (baby|son|daughter)|baby (boy|girl)|"
    r"weddings?|engagements?|got engaged|anniversar(?:y|ies)|golden anniversary|"
    r"community milestone)\b",
    re.I,
)

def _story_title(it):
    return ((it.get("title") or "") + " " + (it.get("short") or "")).lower()

def _story_key(it):
    return (str(it.get("id") or "").strip() + "|" + (it.get("title") or "").strip()).lower()

def _first_url(it):
    if it.get("url"):
        return it["url"]
    if it.get("source_url"):
        return it["source_url"]
    links = it.get("links") or []
    if links and isinstance(links, list) and isinstance(links[0], dict):
        return links[0].get("url") or ""
    return ""

def _normalize_story(it, desk, extra=None):
    row = dict(it)
    row["_desk"] = desk
    if extra:
        row.update(extra)
    if not row.get("url"):
        row["url"] = _first_url(row)
    if not (row.get("tldr") or row.get("summary")):
        row["tldr"] = row.get("one_line") or row.get("short") or row.get("what") or ""
    return row

def is_lifestyle_story(it):
    """Newspaper lifestyle items: weddings, births, honor rolls, students/athletes of the week. Not crime, not invented."""
    T = _story_title(it)
    return bool(_SEG_LIFE.search(T)) and not _SEG_H_NO.search(T)

def is_family_kids_story(it):
    """Stories that apply to kids/teens 6–18 and their parents. Family-friendly only; no crime or death stories."""
    T = _story_title(it)
    if _SEG_H_NO.search(T):
        return False
    if _SEG_H_YES.search(T) or _SEG_H_KIDS.search(T):
        return True
    # teen/kid + school/safety, but not a local ISD board vote (those stay in School Boards)
    if re.search(r"\b(teens?|kids?|children|youth)\b", T) and re.search(r"\b(school|students?|safety)\b", T):
        if re.search(r"\bisd\b|\bcisd\b|school board|trustees?", T):
            return False
        return True
    return False

def _meme_moves_to_h(it):
    """Only news-like meme items (e.g. GTA VI is out) move to Family & Kids; joke/trend memes stay in L."""
    if not is_family_kids_story(it):
        return False
    T = _story_title(it)
    if re.search(r"\b(gta|grand theft auto)\b", T):
        return True
    return bool(re.search(r"\b(is out|launches?|released?|premiere[sd]?)\b", T))

def classify_story(it):
    """Best-fit letter for a headline: C local news, D local politics, E school boards, F city hall, G economic development, H family & kids, I statewide.
    Returns 'LIFE' for newspaper-lifestyle honors. One story, one segment. Never invents a story. Family & Kids is family-friendly only and does not use stories that name kids in a crime or death."""
    T = _story_title(it)
    if is_lifestyle_story(it):
        return "LIFE"
    if is_family_kids_story(it):
        return "H"
    if re.search(r"texas public schools|\btea\b", T) and not re.search(r"\bisd\b|\bcisd\b", T):
        return "I"
    if re.search(r"\bisd\b|\bcisd\b|school board|trustees?|superintendent|school district|closing (three |more )?campuses|campus clos", T):
        if re.search(r"\b(jeti|tax break|tax abatement|plant|tesla|factory|\d+ jobs|investment)\b", T):
            return "G"
        return "E"
    if re.search(r"\b(runoffs?|election administrator|elections administrator|ballots?|precinct|congressman-elect|congresswoman-elect|commissioners court)\b", T):
        return "D"
    if re.search(r"\b(mayor|council)\b.{0,50}\b(races?|candidates?|runoffs?|campaign)\b", T) or re.search(r"\b(races?|candidates?|runoffs?)\b.{0,50}\b(mayor|council)\b", T):
        return "D"
    if re.search(r"\brep(?:resentative|\.)\s", T) and re.search(r"\b(act|bill|committee|legislation)\b", T):
        return "D"
    if re.search(r"\b(abbott|paxton|comptroller|legislature|txdmv|gov(?:ernor|\.|-elect)|gerrymander|high courts|razor wire|sen\.?\s+john cornyn|texas republicans|democrats['’] statewide)\b", T):
        return "I"
    if re.search(r"\b(city manager|city attorney|councilwoman|councilman|city council)\b", T) and not re.search(r"\b(races?|runoffs?|candidates?)\b", T):
        return "F"
    if re.search(r"food truck park", T):
        return "F"
    if re.search(r"\b(edc|rioplex|tax break|tax abatement|jeti|data center|industrial|investment|factory|polysilicon|sales tax|retail sales|truck port|health education building)\b", T) or (re.search(r"spacex", T) and re.search(r"\b(tax|abatement|data center|jobs|investment|edc|permit)\b", T)):
        return "G"
    if re.search(r"\b(city commission|commission seat|ordinance|rezoning|comprehensive plan)\b", T):
        return "F"
    if re.search(r"\b(mayor and council|approves|bans|sworn in)\b", T) and re.search(r"\b(mayor|council|commission|ordinance|city attorney|managers|hens|roosters|barking)\b", T):
        return "F"
    if re.search(r"\b(mcallen|mission|pharr|alton|edinburg|weslaco|brownsville|harlingen|starbase)\b.{0,40}\b(bans|approves|ordinance|rezoning|comprehensive plan)\b", T):
        return "F"
    if it.get("valley") or it.get("_desk") == "rgv":
        return "C"
    return "I"

def assign_segment_stories(rgv, texas, national=None, trending=None, tech=None, memes=None):
    """Split headlines into C–I plus LIFE. Optional national/trending/tech/meme lists contribute only Family & Kids or Lifestyle items (removed from their original desks). Each story is used once. Does not invent items."""
    buckets = {L: [] for L in "CDEFGHI"}
    lifestyle = []
    def place(row, extras=False):
        letter = classify_story(row)
        if extras and letter not in ("H", "LIFE"):
            return
        if extras and row.get("_desk") == "meme" and letter == "H" and not _meme_moves_to_h(row):
            return
        if letter == "LIFE":
            lifestyle.append(row)
        else:
            buckets[letter].append(row)
    for desk, items in (("rgv", rgv or []), ("texas", texas or [])):
        for it in items:
            place(_normalize_story(it, desk), extras=False)
    for desk, items in (("national", national or []), ("trending", trending or []), ("tech", tech or [])):
        for it in items:
            place(_normalize_story(it, desk), extras=True)
    for it in memes or []:
        place(_normalize_story(it, "meme"), extras=True)
    buckets["LIFE"] = lifestyle
    return buckets

def plus_confirm(html, n):
    html = html or ""
    n = int(n or 0)
    if not n:
        return html
    m = re.search(r'(<span class="cf">)(\d+)( CONFIRM</span>)', html)
    if m:
        return html[:m.start(2)] + str(int(m.group(2)) + n) + html[m.end(2):]
    return html + f'<span class="cf">{n} CONFIRM</span>'


# ---------------------------------------------------------------- What I've Been Up To (block B)
def prep_up_to(data):
    """Block B comes ONLY from the family calendar (tools/family_calendar.py). Items are {date, label, category, count} in generic
    wording; there are no names, links or CONFIRM tags unless the tool says something is ambiguous."""
    for k in ("up_to", "up_to_coming"):
        out = []
        for e in data.get(k) or []:
            if not (e.get("label") and e.get("date")):
                continue
            e.setdefault("category", "family"); e["count"] = int(e.get("count") or 1)
            out.append(e)
        data[k] = out
    ev, coming = data["up_to"], data["up_to_coming"]
    meta = data.get("up_to_meta") or {}
    if not ev and not coming:
        data["up_to_script"] = data.get("up_to_script") or "Quiet week on the family calendar. Jess, what's the best thing you did with your free time lately? Okay, let's get into the Valley."
    meta.setdefault("calendar", "Family calendar (iCloud, published feed)")
    meta["status"] = "found" if (ev or coming) else "none"
    n = len(ev) + len(coming)
    meta["banner"] = (f"{len(ev)} from the week" + (f" + {len(coming)} coming up" if coming else "") if n else "Quiet week on the family calendar")
    meta.setdefault("internal", "")
    data["up_to_meta"] = meta

def upto_when(e):
    d = datetime.date.fromisoformat(e["date"])
    return ({2: "twice", 3: "three times"}.get(e["count"], f"{e['count']} times") if e["count"] > 1 else d.strftime("%a %b %-d"))

def upto_lines(data):
    out = []
    for e in data["up_to"]:
        out.append(f'{e["label"]} · {upto_when(e)}')
    for e in data.get("up_to_coming", []):
        out.append(f'COMING UP: {e["label"]} · {upto_when(e)}')
    return out

# ---------------------------------------------------------------- Trending News (what's trending around the nation)
def prep_trending(data):
    tr = data.get("trending") or []
    for t in tr:
        t.setdefault("links", []); t.setdefault("verified", True)
        if t.get("source_url") and not any(l["url"] == t["source_url"] for l in t["links"]):
            pass
        if not t.get("source_url"): t["confirm"] = (t.get("confirm") or "") + " NO VERIFIED LINK: CONFIRM BEFORE AIR"
        t["isConfirm"] = bool(t.get("confirm")) or not t.get("verified", True)
    data["trending"] = tr

# ---------------------------------------------------------------- Tech ("What's Happening in Tech", sub-segment of block J)
TECH_WIRES = "tech wires (The Verge, TechCrunch, Ars Technica)"

def prep_tech(data):
    """Normalise data["tech"] = {origin, items[...]}. origin: "fast-company-daily" (the morning email) or "wires" (fallback,
    only when no issue from the last 48 h exists). Every item is labelled with where it came from; anything without a link or
    flagged unverified is marked CONFIRM BEFORE AIR."""
    t = data.get("tech")
    if not isinstance(t, dict):
        t = {"origin": "none", "items": []}
    t.setdefault("items", []); t.setdefault("issue", None); t.setdefault("note", "")
    origin = t.get("origin") or "none"
    issue = t.get("issue") or {}
    if origin == "fast-company-daily":
        t["badge"] = "FAST COMPANY DAILY" + (f" · {issue['date']}" if issue.get("date") else "")
        t["originLabel"] = "From Drew's Fast Company Daily email" + (f" ({issue['date']})" if issue.get("date") else "")
    elif origin == "wires":
        t["badge"] = "FALLBACK: TECH WIRES"
        t["originLabel"] = "FALLBACK: " + TECH_WIRES + ". No Fast Company Daily issue from the last 48 hours was found in Gmail."
    else:
        t["badge"] = "NO TECH ITEMS"
        t["originLabel"] = "No Fast Company Daily issue from the last 48 hours and no tech-wire fallback were loaded."
    t["origin"] = origin
    for it in t["items"]:
        it.setdefault("links", []); it.setdefault("verified", True); it.setdefault("angle", ""); it.setdefault("confirm", "")
        it["basis"] = it.get("basis") or (t["badge"] if origin != "none" else "")
        if not it.get("source_url"):
            it["confirm"] = (it["confirm"] + " NO VERIFIED LINK: CONFIRM BEFORE AIR").strip()
        if not it["verified"] and not it["confirm"]:
            it["confirm"] = "Not independently verified"
        it["isConfirm"] = bool(it["confirm"])
    t["items"] = t["items"][:5]
    data["tech"] = t

# ---------------------------------------------------------------- Obituaries ("Remembering Our Neighbors", read near the close, block L)
CHISME_BADGE = "RUMOR · CONFIRM BEFORE AIR"
OBIT_PAGE = "https://www.legacy.com/us/obituaries/local/texas/mcallen?publisher=The+Monitor"

def fmt_day(iso):
    try:
        d = datetime.date.fromisoformat(iso)
        return f"{d.strftime('%b')} {d.day}"
    except Exception:
        return ""

def prep_obituaries(data):
    """Normalise data["obituaries"] (the block tools/obituaries.py writes). Only fields that Legacy listed are kept; there is no
    cause of death anywhere. Adds weekly groups (newest first), the short on-air read and which names it uses."""
    o = data.get("obituaries")
    o = o if isinstance(o, dict) else {}
    seen, items = set(), []
    for r in o.get("items") or []:
        url = r.get("url") or ""
        if not (r.get("name") and url.startswith("https://www.legacy.com/") and r.get("published")) or url in seen:
            continue
        seen.add(url)
        items.append({k: r.get(k) for k in ("id", "name", "age", "city", "died", "published", "funeralHome", "url")})
    win = o.get("window") or {}
    to = win.get("to") or (max(r["published"] for r in items) if items else "")
    start = win.get("from") or (min(r["published"] for r in items) if items else "")
    groups = OB.week_groups(items, to or None, start or None) if OB and items else []
    picks = OB.read_picks(items, to or None) if OB and items else []
    script = OB.read_script(items, to or None) if OB and items else ""
    data["obituaries"] = {
        "items": items, "count": len(items), "groups": groups, "script": script, "pickUrls": [r["url"] for r in picks],
        "window": win, "windowLabel": (OB.span_label(datetime.date.fromisoformat(start), datetime.date.fromisoformat(to)) if OB and start and to else ""),
        "source": o.get("source") or "Legacy.com · The Monitor (McAllen, TX)", "sourceUrl": o.get("sourceUrl") or OBIT_PAGE, "fetchedAt": o.get("fetchedAt") or "",
        "note": o.get("note") or "",
    }

def prep_chisme(data):
    """Normalise data["chisme"] (the block tools/chisme.py writes into the packet). Missing or empty is fine: the section then says so."""
    c = data.get("chisme")
    c = c if isinstance(c, dict) else {}
    items = []
    for r in c.get("items") or []:
        if r.get("title") and str(r.get("url", "")).startswith("http"):
            items.append(dict(r, badge=r.get("badge", CHISME_BADGE)))
    data["chisme"] = {"items": items[:10], "sources": c.get("sources") or {}, "window": c.get("window") or "last 72 hours", "generatedAt": c.get("generatedAt") or "", "dropped": c.get("dropped") or {}}

def obit_line(r):
    """One notice as plain text, only what the notice lists."""
    bits = [r["name"] + (f", {r['age']}" if r.get("age") else "")]
    if r.get("city"): bits.append(r["city"])
    if r.get("died"): bits.append("died " + fmt_day(r["died"]))
    bits.append("ran " + fmt_day(r["published"]))
    if r.get("funeralHome"): bits.append(r["funeralHome"])
    return " · ".join(bits)

def trend_item_conf(t):
    return t.get("confirm") or ("Not independently verified" if not t.get("verified", True) else "")

# ---------------------------------------------------------------- Cold open + jingle (cold-open.md)
def ordinal(n): return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"

def cold_templates():
    md = open(os.path.join(HERE, "..", "cold-open.md")).read()
    def block(head):
        i = md.index(head); j = md.index("```text", i) + 7; k = md.index("```", j)
        return md[j:k].strip()
    return {"monday": block("## TEMPLATE: MONDAY"), "daily": block("## TEMPLATE: DAILY BRIEFING"), "jingle": block("## JINGLE (primary"),
            "alternates": [x.strip() for x in block("## JINGLE ALTERNATES").splitlines() if x.strip()]}

def trim_words(t, n=12):
    t = re.sub(r"\s*\[?CONFIRM[^\].]*\]?", "", t or "").strip()
    w = t.split()
    return " ".join(w[:n]).rstrip(",;:- ") if w else ""

def weather_short(data):
    w, m = data["weather"], data["meta"]
    nowc = w.get("now")
    if m["mode"] == "daily" and m["date"] == datetime.date.today().isoformat() and nowc:
        return f'{nowc["tempF"]} and {nowc["cond"].lower()}'
    day = next((x for x in w.get("days", []) if x["date"] == m["date"]), (w.get("days") or [None])[0])
    if not day: return ""
    cond = re.sub(r"^((?:slight )?chance)\s+", r"a \1 of ", day["short"].lower())
    return f'{day["hi"]} and {cond}'

def build_cold_open(data):
    m = data["meta"]; T = cold_templates()
    d = datetime.date.fromisoformat(m["date"])
    rgv = data["headlines"]["rgv"]
    loc = [x for x in rgv if x.get("open")]
    loc += [x for x in rgv if x.get("teaser") and x not in loc]
    loc += [x for x in rgv if x not in loc]
    loc = loc[:2]
    teased = [("RGV", x) for x in loc]
    spoken = lambda x: trim_words(x.get("teaser") or x.get("short") or x["title"])
    nat = next((n for n in data["nationalDesk"] if n.get("teaser")), (data["nationalDesk"] or [None])[0])
    trend = next((t for t in data.get("trending", []) if t.get("print") and t.get("teaser")), next((t for t in data.get("trending", []) if t.get("teaser")), None))
    vals = {"DAY": d.strftime("%A"), "MONTH": d.strftime("%B"), "DATE_ORDINAL": ordinal(d.day),
            "LOCAL_1": spoken(loc[0]) if loc else "", "LOCAL_2": spoken(loc[1]) if len(loc) > 1 else "",
            "NATIONAL_1": trim_words(nat.get("teaser") or nat.get("ptitle") or nat["title"]) if nat else "",
            "TRENDING_1": trim_words(trend.get("teaser") or trend.get("short") or trend["title"]) if trend else "",
            "KIDS_TOPIC": trim_words(m.get("kidsTopic", ""), 16), "WEATHER_SHORT": weather_short(data)}
    if nat: teased.append(("National Desk", nat))
    if trend: teased.append(("Trending", trend))
    tpl = T["monday"] if m["mode"] == "monday" else T["daily"]
    if not vals["LOCAL_2"]: tpl = tpl.replace(", plus {LOCAL_2}", "")
    sents = re.split(r"(?<=[.!?])\s+", " ".join(tpl.split()))
    out = []
    for sn in sents:
        keys = re.findall(r"\{([A-Z_0-9]+)\}", sn)
        if any(not vals.get(k) for k in keys): continue
        out.append(re.sub(r"\{([A-Z_0-9]+)\}", lambda mm: vals[mm.group(1)], sn))
    text = " ".join(out)
    conf = []
    for lab, x in teased:
        c = x.get("confirm") if isinstance(x.get("confirm"), (str, list)) else ""
        if c or x.get("verified") is False:
            conf.append(f'{lab}: {x.get("short") or x.get("ptitle") or x["title"]}')
    return {"text": text, "jingle": T["jingle"], "alternates": T["alternates"], "confirm": conf, "words": len(text.split()), "template": m["mode"]}


def all_urls(data):
    out = []
    def add(section, label, url):
        if url and url.startswith("http"): out.append((section, label, url))
    for k, name in (("rgv", "Top headlines: RGV"), ("texas", "Top headlines: Texas")):
        for i in data["headlines"][k]: add(name, i["title"], i.get("url"))
    for n in data["nationalDesk"]:
        for l in n["links"]: add("National Desk", l["label"], l["url"])
    w = data["weather"]; add("Weather", "NWS forecast page (McAllen)", w["pageUrl"]); add("Weather", "NWS Brownsville office", w["officeUrl"]); add("Weather", "NWS API forecast (JSON)", w["apiUrl"])
    hs = data["sports"]["highSchool"]
    for i in hs["results"] + hs["next"] + [hs["college"]]: add("High school sports", i["title"], i.get("url"))
    for g in ("nfl", "nba", "mlb"):
        s = data["sports"][g]
        if s.get("scoreSource"): add(s["title"], s["scoreSource"]["title"], s["scoreSource"]["url"])
        for i in s.get("notable", []): add(s["title"], i["title"], i.get("url"))
    for lv in data["memes"]["levels"]:
        for i in lv["items"]:
            for l in i["links"]: add("Meme of the Week: " + lv["level"], l["label"], l["url"])
    for t in data.get("trending", []):
        add("Trending News", t["title"], t.get("source_url"))
        for l in t.get("links", []): add("Trending News", l["label"], l["url"])
    for r in data.get("rundown", []):
        for l in r["links"]: add("Run of show: " + r["letter"], l["label"], l["url"])
    for c in (data.get("chisme") or {}).get("items", []):
        add("Chisme", c["title"], c.get("url"))
    ob = data.get("obituaries") or {}
    if ob.get("items"):
        add("Remembering Our Neighbors", "Legacy.com: The Monitor obituaries, McAllen", ob["sourceUrl"])
        for r in ob["items"]: add("Remembering Our Neighbors", r["name"], r["url"])
    seen, res = set(), []
    for s, l, u in out:
        if (s, u) in seen: continue
        seen.add((s, u)); res.append({"section": s, "label": l, "url": u})
    return res

# ---------------------------------------------------------------- link check
def check_links(urls):
    def one(u):
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(u, method=method, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
                with urllib.request.urlopen(req, timeout=20) as r: return u, r.status
            except urllib.error.HTTPError as e:
                if method == "HEAD" and e.code in (403, 405, 400, 404, 501): continue
                return u, e.code
            except Exception as e:
                if method == "GET": return u, 0
        return u, 0
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(one, urls))
    out = {}
    for u, c in res.items():
        out[u] = {"status": c, "result": "ok" if 200 <= c < 400 else ("blocked-by-site" if c in (401, 403, 429, 999) else ("dead" if c in (404, 410) else "unreachable"))}
    return out

# ---------------------------------------------------------------- shared bits
def b64(path, mime):
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()

def asset(p): return os.path.join(HERE, p)

ICONS = {
 "sun": '<svg viewBox="0 0 48 48" width="{s}" height="{s}"><g stroke="#f2a900" stroke-width="3" stroke-linecap="round"><path d="M24 4v6M24 38v6M4 24h6M38 24h6M9.9 9.9l4.2 4.2M33.9 33.9l4.2 4.2M9.9 38.1l4.2-4.2M33.9 14.1l4.2-4.2"/></g><circle cx="24" cy="24" r="9" fill="#ffd23f" stroke="#f2a900" stroke-width="2"/></svg>',
 "partly": '<svg viewBox="0 0 48 48" width="{s}" height="{s}"><g stroke="#f2a900" stroke-width="3" stroke-linecap="round"><path d="M17 3v5M5 15h5M8.5 6.5l3.5 3.5M28.5 6.5L25 10"/></g><circle cx="17" cy="16" r="7" fill="#ffd23f" stroke="#f2a900" stroke-width="2"/><path d="M16 40h21a8 8 0 0 0 0-16 11 11 0 0 0-21 3 6.5 6.5 0 0 0 0 13z" fill="#e8eef5" stroke="#8aa0b8" stroke-width="2"/></svg>',
 "cloud": '<svg viewBox="0 0 48 48" width="{s}" height="{s}"><path d="M13 38h22a9 9 0 0 0 0-18 12 12 0 0 0-23 3 7.5 7.5 0 0 0 1 15z" fill="#dbe4ee" stroke="#8aa0b8" stroke-width="2.2"/></svg>',
 "rain": '<svg viewBox="0 0 48 48" width="{s}" height="{s}"><path d="M13 30h22a8 8 0 0 0 0-16 11 11 0 0 0-21 3 6.5 6.5 0 0 0-1 13z" fill="#cfd9e6" stroke="#6f87a3" stroke-width="2.2"/><g stroke="#2a7de1" stroke-width="3" stroke-linecap="round"><path d="M16 36l-2 6M25 36l-2 6M34 36l-2 6"/></g></svg>',
 "storm": '<svg viewBox="0 0 48 48" width="{s}" height="{s}"><path d="M13 28h22a8 8 0 0 0 0-16 11 11 0 0 0-21 3 6.5 6.5 0 0 0-1 13z" fill="#b8c4d3" stroke="#5f7490" stroke-width="2.2"/><path d="M26 28l-6 10h5l-3 8 9-12h-5z" fill="#ffd23f" stroke="#f2a900" stroke-width="1.5"/></svg>',
}
EMOJI = {"sun": "☀️", "partly": "⛅", "cloud": "☁️", "rain": "🌧️", "storm": "⛈️"}
icon = lambda k, s=30: ICONS[k].format(s=s)

def conf_text(item):
    c = item.get("confirm")
    if isinstance(c, list): return "; ".join(c)
    return c or ""

def date_parts(m):
    d = datetime.date.fromisoformat(m["date"]); return d

def hs_texts(hs):
    return hs.get("scoreLabel", "latest results"), hs.get("nextLabel", "Upcoming games"), hs.get("noResults", "No new results in this window."), hs.get("noNext", "No upcoming games listed.")

def sport_title(s, extra=True):
    return (s["title"] + (" " + s["window"] if extra and s.get("window") else "")).strip()

def next_show_chips(data):
    return "".join(f'<span><i style="background:{c["color"]}">{c["letter"]}</i>{esc(c["short"])}</span>' for c in data.get("showClock", []))

def jess_star(s): return " ★" if s.get("signature") else ""

# ---------------------------------------------------------------- PRINT (one page)
PRINT_CSS = """
@page { size: 11in 8.5in; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
html, body { width: 11in; height: 8.5in; background: #fff }
body { font-family: Inter, 'Helvetica Neue', Arial, sans-serif; color: #1b2430; font-size: 8pt; line-height: 1.18; -webkit-print-color-adjust: exact; print-color-adjust: exact }
a { color: inherit; text-decoration: none }
.page { width: 11in; height: 8.5in; padding: 0.15in 0.2in 0.12in; display: flex; flex-direction: column; gap: 5px; background: #fffdf6 }
header { display: flex; align-items: center; gap: 12px; height: 0.68in; flex: none }
.logo { height: 0.64in; background: #fff; border-radius: 10px; padding: 2px 8px; border: 2px solid #1b2430 }
.title { flex: 1 }
.title .k { font-size: 8.5pt; letter-spacing: .14em; font-weight: 800; color: #b5651d; text-transform: uppercase }
.title .d { font-size: 20pt; font-weight: 900; line-height: 1.05; letter-spacing: -.01em }
.title .t { font-size: 8.8pt; font-weight: 600; color: #4a5a6b }
.badge { text-align: right; font-size: 8pt; font-weight: 700 }
.badge .s { display: inline-block; background: #e4572e; color: #fff; padding: 3px 9px; border-radius: 99px; font-size: 8.4pt; font-weight: 800 }
.badge .n { margin-top: 3px; color: #4a5a6b; font-weight: 600 }
.clock { flex: none }
.clockbar { display: flex; height: 0.27in; border-radius: 7px; overflow: hidden; border: 1.5px solid #1b2430 }
.clockbar div { display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 8pt; color: #fff; border-right: 1px solid rgba(255,255,255,.7); white-space: nowrap }
.clockbar div:last-child { border-right: 0 }
.clockleg { display: flex; justify-content: space-between; margin-top: 2px; font-size: 7.6pt; font-weight: 700; color: #33404f }
.clockleg span { white-space: nowrap }
.clockleg i { font-style: normal; font-weight: 800; padding: 0 3px; border-radius: 3px; color: #fff; margin-right: 2px }
.grid { flex: 1; display: grid; grid-template-columns: 3.4in 3.45in 3.6in; gap: 6px; min-height: 0 }
.col { display: flex; flex-direction: column; gap: 5px; min-height: 0 }
.card { background: #fff; border: 1.5px solid #1b2430; border-radius: 9px; overflow: hidden; display: flex; flex-direction: column; min-height: 0 }
.card > h2 { font-size: 9.2pt; letter-spacing: .08em; text-transform: uppercase; font-weight: 900; color: #fff; padding: 2px 8px; flex: none; display: flex; justify-content: space-between }
.card > h2 small { font-weight: 600; letter-spacing: 0; text-transform: none; font-size: 7.6pt; opacity: .95 }
.card .b { padding: 4px 7px 4px; flex: 1 1 auto; min-height: 0; overflow: hidden }
ul { list-style: none }
li { margin-bottom: 1.5px }
.hl li { padding-left: 9px; position: relative }
.hl li:before { content: ''; position: absolute; left: 0; top: 4px; width: 5px; height: 5px; border-radius: 50%; background: #e4572e }
.hl a b { font-weight: 800 }
.src { color: #66788c; font-weight: 600; font-size: 7.4pt }
.thumb { float: right; width: .95in; margin: 0 0 3px 6px; border-radius: 6px; border: 1px solid #1b2430 }
.cap { font-size: 6.6pt; color: #66788c; clear: both }
.wk { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; text-align: center }
.wk div { border-radius: 6px; padding: 1px 0; border: 1px solid #d5dde6 }
.wk .mon { background: #fff3c4; border: 2px solid #f2a900 }
.wk .dd { font-weight: 800; font-size: 8pt }
.wk .hi { font-weight: 900; font-size: 10.5pt }
.wk .lo { color: #66788c; font-weight: 700; font-size: 8pt }
.wk .pp { color: #2a7de1; font-weight: 800; font-size: 7.8pt }
.wnote { margin-top: 3px; font-weight: 600 }
.scores { columns: 2; column-gap: 8px }
.scores li { break-inside: avoid; margin-bottom: 1.5px; font-weight: 600 }
.chip { display: inline-block; font-weight: 900; font-size: 7.6pt; padding: 0 4px; border-radius: 4px; background: #1b2430; color: #fff; margin-right: 3px }
.nat li { margin-bottom: 4px }
.nat .nt { font-weight: 800 }
.nat .lab { font-weight: 900; font-size: 7.6pt; text-transform: uppercase; letter-spacing: .04em }
.lv { margin-bottom: 3px; border-left: 4px solid; padding-left: 6px }
.lv h3 { font-size: 8.6pt; font-weight: 900; text-transform: uppercase; letter-spacing: .05em }
.mi { margin-bottom: 2px }
.mi b { font-weight: 800 }
.mi .tip { font-weight: 700 }
.cf { display: inline-block; font-size: 7.2pt; font-weight: 900; color: #fff; background: #c1121f; padding: 0 4px; border-radius: 3px }
.motw { background: #fff1e8; border: 1.5px dashed #e4572e; border-radius: 6px; padding: 2px 5px; margin-bottom: 4px }
.tag { font-weight: 900; font-size: 7.4pt; color: #fff; background: #e4572e; padding: 0 4px; border-radius: 3px; text-transform: uppercase }
.ns { background: #264653; color: #fff; border-radius: 7px; padding: 3px 9px; font-weight: 800; font-size: 8.8pt; margin-bottom: 3px }
.ns b { color: #ffd23f; letter-spacing: .06em }
.co { flex: none; background: #fff8e0; border: 1.5px solid #f2b705; border-radius: 7px; padding: 1px 8px; font-size: 7.4pt; line-height: 1.17 }
.co b { font-weight: 900; letter-spacing: .06em; color: #8a5a00 }
.co .jg { font-weight: 800; color: #8a5a00 }
.tr1 li { padding-left: 0; margin-bottom: 1.5px }
.tr1 .cat { display: inline-block; font-weight: 900; font-size: 6.6pt; text-transform: uppercase; padding: 0 3px; border-radius: 3px; background: #577590; color: #fff; margin-right: 3px }
.up li { margin-bottom: 1px }
footer { flex: none; font-size: 7.2pt; color: #4a5a6b; font-weight: 600; display: flex; justify-content: space-between; gap: 10px }
"""

PRINT_CSS += """
.sb{display:inline-block;font-size:5.3pt;font-weight:900;letter-spacing:.03em;line-height:1;padding:1px 2.5px;border-radius:2px;margin-right:2px;vertical-align:1px;color:#fff}
.sb.h{background:#c1121f}.sb.t{background:#e4572e}.sb.a{background:#9aa6b2}.sb.u{background:#6f42c1}
"""

def card(name, color, title, sub, inner, extra_style=""):
    return f'<section class="card" data-name="{esc(name)}" style="{extra_style}"><h2 style="background:{color}"><span>{title}</span><small>{sub}</small></h2><div class="b">{inner}</div></section>'

def lnk(item, text=None, cls=""):
    t = text or item.get("short") or item["title"]
    if item.get("url"): return f'<a href="{esc(item["url"])}" class="{cls}">{esc(t)}</a>'
    return esc(t)

def print_html(data):
    m, w = data["meta"], data["weather"]
    d = date_parts(m)
    logo = b64(asset("assets/DITM_SunLogo.png"), "image/png")
    clock = data.get("showClock", [])
    bar = "".join(f'<div style="width:{c["minutes"]/60*100:.3f}%;background:{c["color"]}">{c["letter"]}{"★" if c["signature"] else ""}</div>' for c in clock)
    leg = "".join(f'<span><i style="background:{c["color"]}">{c["letter"]}</i>{esc(c["short"])}</span>' for c in clock)
    ns = m["nextShow"]
    if m["mode"] == "monday":
        clockhtml = f'<div class="clock"><div class="clockbar">{bar}</div><div class="clockleg"><span><b>8:00</b></span>{leg}<span><b>9:00</b></span></div></div>'
    else:
        clockhtml = f'<div class="clock"><div class="ns"><b>NEXT SHOW</b> · {esc(ns["label"])} · 8:00-9:00 AM CT · 60 min · Monday 8 AM rundown (story bank below feeds it)</div><div class="clockleg">{leg}</div></div>'
    # headlines
    hl = data["headlines"]; img = hl.get("image")
    items = ""
    for i, it in enumerate([x for x in hl["rgv"] if not x.get("noprint")][:6]):
        pre = ""
        if img and img.get("forItem") == i:
            pre = f'<img class="thumb" src="{b64(asset(img["file"]), "image/jpeg")}">'
        items += f'<li>{pre}<a href="{esc(it["url"])}">{sc_print(it)}<b>{esc(it["short"])}</b> <span class="src">{esc(it["source"])}</span></a></li>'
    tx = "".join(f'<li><a href="{esc(it["url"])}">{sc_print(it)}{esc(it["short"])} <span class="src">{esc(it["source"].split(" · ")[0])}</span></a></li>' for it in hl["texas"][:1])
    headlines = card("headlines", "#e4572e", "Top Headlines · RGV First", esc(m["hlSub"]), f'<ul class="hl">{items}</ul><div class="cap">{esc(img["caption"]) if img else ""}</div><div style="font-weight:900;font-size:7.8pt;letter-spacing:.06em;margin-top:2px;color:#33404f">TEXAS</div><ul class="hl">{tx}</ul>')
    # national
    nat = ""
    for n in [x for x in data["nationalDesk"] if x.get("print")][:4]:
        conf = '<span class="cf">CONFIRM</span> ' if n.get("confirm") else ""
        nat += f'<li><a href="{esc(n["links"][0]["url"])}">{sc_print(n)}<span class="nt">{esc(n.get("ptitle") or n["title"])}</span></a> {conf}<br>{esc(n.get("pfact") or n["summary"])}<br><span class="lab" style="color:#6d597a">Take:</span> {esc(n.get("pangle") or n["angle"])} <span class="lab" style="color:#2a6f97">Valley:</span> {esc(n.get("pvalley") or n["valley"])}</li>'
    national = card("national", "#6d597a", "The National Desk", "smaller · local leads", f'<ul class="nat">{nat}</ul>')
    co = data["coldOpen"]
    coldstrip = f'<div class="co"><b>COLD OPEN</b> {esc(co["text"])} <span class="jg">♪ {esc(co["jingle"])}</span>{(" <span class=cf>CONFIRM</span>") if co["confirm"] else ""}</div>'
    um = data["up_to_meta"]
    if data["up_to"] or data["up_to_coming"]:
        upl = "".join(f'<li><span class="chip" style="background:#d1495b">{esc(e["category"][0].upper())}</span>{esc(e["label"])} <span class="src">{esc(upto_when(e))}</span></li>' for e in data["up_to"][:5])
        if data["up_to_coming"]:
            upl += '<li><b>Coming up:</b> ' + esc(", ".join(e["label"] for e in data["up_to_coming"][:3])) + '</li>'
        upbody = f'<ul class="up">{upl}</ul><div class="src">From Drew\'s family calendar, generic wording.</div>'
    else:
        upbody = '<div class="wnote"><b>Quiet week on the family calendar.</b> The script says so and moves on.</div>'
    upto = card("upto", "#d1495b", "What I've Been Up To", esc(um["banner"]), upbody)
    trl = "".join(f'<li><span class="cat">{esc(t["category"].split("/")[0])}</span><a href="{esc(t["source_url"])}">{sc_print(t)}<b>{esc(t.get("short") or t["title"])}</b></a>' + (' <span class="cf">CONFIRM</span>' if t.get("isConfirm") else "") + '</li>' for t in [x for x in data.get("trending", []) if x.get("print")][:4])
    tk = [x for x in data["tech"]["items"]][:2]
    if tk:
        trl += '<li><span class="cat">TECH</span>' + ('<span class="sb a">WIRES</span>' if data["tech"]["origin"] == "wires" else "") + " · ".join(f'<a href="{esc(x["source_url"])}"><b>{esc(x.get("short") or x["title"])}</b></a>' if x.get("source_url") else esc(x.get("short") or x["title"]) for x in tk) \
               + (' <span class="cf">CONFIRM</span>' if any(x["isConfirm"] for x in tk) else "") + '</li>'
    trend = card("trending", "#577590", "Trending News", "around the nation", f'<ul class="tr1">{trl}</ul>')
    # weather
    cells = ""
    for dday in w["days"][:7]:
        mon = ' class="mon"' if dday["date"] == w["monday"] else ""
        cells += f'<div{mon}><div class="dd">{dday["label"]} {dday["dateLabel"].split()[1]}</div>{icon(dday["icon"], 20)}<div class="hi">{dday["hi"]}°</div><div class="lo">{dday["lo"] if dday["lo"] is not None else "–"}°</div><div class="pp">{dday["pop"]}%</div></div>'
    mon_day = next((x for x in w["days"] if x["date"] == w["monday"]), None)
    mon_txt = f'<b>{m["todayLabel"]} ({mon_day["label"]} {mon_day["dateLabel"]}):</b> {esc(mon_day["short"])}, high {mon_day["hi"]}°, rain {mon_day["pop"]}%, wind {esc(mon_day["wind"])}. ' if mon_day else ""
    upd = datetime.datetime.fromisoformat(w["updated"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
    alerts = "No NWS alerts." if w.get("alerts") == [] else ("Alerts: " + ", ".join(w["alerts"]) if w.get("alerts") else "")
    nowc = w.get("now")
    if nowc: mon_txt = f'<b>Now {nowc["tempF"]}°F</b> ({esc(nowc["cond"].lower())}). ' + mon_txt
    weather = card("weather", "#2a7de1", "McAllen / RGV Weather", "hi / lo / rain %", f'<div class="wk">{cells}</div><div class="wnote">{mon_txt}{alerts} <span class="src">NWS {esc(w["office"])} · updated {upd.strftime("%b %-d %-I:%M %p")} CT · <a href="{esc(w["pageUrl"])}">forecast</a></span></div>')
    # sports
    hs = data["sports"]["highSchool"]
    ab = {"Brownsville Vets": "B'ville Vets", "Brownsville Pace": "B'ville Pace", "McAllen Memorial": "Memorial", "Mission Vets": "M. Vets", "Gregory-Portland": "Greg-Portland", "Flour Bluff": "Flour Bluff"}
    def abv(t):
        for k, v in ab.items(): t = t.replace(k, v)
        return t
    res = "".join(f'<li><a href="{esc(r["url"])}">{esc(abv(r["short"]))}</a></li>' for r in hs["results"][:7])
    nxt = "".join(f'<li><a href="{esc(r["url"])}">{esc(r["short"])}</a></li>' for r in hs["next"])
    sl, nl, nores, nonext = hs_texts(hs)
    if not hs["results"]: res = f'<div class="wnote">{esc(nores)}</div>'
    else: res = f'<ul class="scores">{res}</ul>'
    if not hs["next"]: nxt = f'<li>{esc(nonext)}</li>'
    hsc = card("hs", "#2a9d8f", "RGV High School Football", esc(sl.lower()), f'{res}<div style="font-weight:900;font-size:7.8pt;margin-top:2px">{esc(nl.upper())}</div><ul>{nxt}</ul>')
    nfl = data["sports"]["nfl"]; nba = data["sports"]["nba"]; mlb = data["sports"]["mlb"]
    nf = "".join(f'<li>{esc(b)}</li>' for a, b in nfl["scores"]) or '<li>No NFL games in this window.</li>'
    nb = ("".join(f'<li>{esc(b)}</li>' for a, b in nba["scores"]) or '<li>No NBA games in this window.</li>') + "".join(f'<li><b>{esc(b)}</b></li>' for a, b in nba["texas"])
    nn = lambda g, k: "".join(f'<li><a href="{esc(n["url"])}">{esc(n["short"])}</a></li>' for n in g["notable"][:k])
    H = lambda t, extra="": f'<div style="font-weight:900;font-size:7.8pt;letter-spacing:.06em;margin:2px 0 1px;color:#33404f">{t} {extra}</div>'
    pro = card("pro", "#264653", "NFL · NBA · MLB", "scores + notable", H(esc(sport_title(nfl).upper()), f'<a class="src" href="{esc(nfl["scoreSource"]["url"])}">NFL.com</a>') + f'<ul class="scores">{nf}</ul>' + H(esc(sport_title(nba).upper() + " + TEXAS TEAMS"), f'<a class="src" href="{esc(nba["scoreSource"]["url"])}">Basketball-Ref</a>') + f'<ul class="scores">{nb}</ul>')
    mlbc = card("mlb", "#003f88", "MLB · Offseason, no scores", "hot stove", f'<ul>{nn(mlb, 2)}</ul>')
    # memes
    lvls = ""
    colors = {"Elementary": "#2a9d8f", "Middle School": "#8e6bbf", "High School": "#e76f51"}
    for lv in data["memes"]["levels"]:
        c = colors.get(lv["level"], "#333")
        mi = ""
        pick = [x for x in lv["items"] if x["id"] == data["memes"].get("memeOfTheWeek")] or lv["items"][:1]
        for it in pick:
            is_motw = it["id"] == data["memes"].get("memeOfTheWeek")
            conf = '<span class="cf">CONFIRM</span> ' if it.get("confirm") else ""
            tag = '<span class="tag">Meme of the Week</span> ' if is_motw else ""
            body = f'<a href="{esc(it["links"][0]["url"])}"><b>{esc(it["title"].replace(" (Meme of the Week)", ""))}</b></a> {tag}{conf}<br>{esc(it.get("pwhat") or it["what"])}<br><span class="tip" style="color:{c}">Say:</span> <span class="tip">{esc(it.get("ptip") or it["tip"])}</span>'
            mi += f'<div class="mi{" motw" if is_motw else ""}">{body}</div>'
        lvls += f'<div class="lv" style="border-color:{c}"><h3 style="color:{c}">{lv["icon"]} {esc(lv["level"])}</h3>{mi}</div>'
    memes = card("memes", "#ff7f50", "Meme of the Week", "what the kids are talking about", f'{lvls}')
    ob = data["obituaries"]
    obit_pdf = (f'Obituaries: {ob["count"]} on studio page · ' if ob["count"] else "")
    foot_src = "Sources: NWS · RGVSports · KRGV · Texas Tribune · ABC · NFL.com · Basketball-Ref · MLB.com · Know Your Meme · full list in sources file"
    chk = data.get("linkCheck")
    chk_s = f" · Links {chk['ok']} ok / {chk['blocked']} bot-blocked / {chk['dead']+chk['unreachable']} bad" if chk else ""
    html_ = f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(m["emailSubject"])}</title><style>{PRINT_CSS}</style></head><body><div class="page">
<header><img class="logo" src="{logo}"><div class="title"><div class="k">{esc(m["kicker"])}</div><div class="d">{esc(m["dateLabel"])}</div><div class="t">{esc(m["recap"])} · Live from McAllen, Texas</div></div><div class="badge">{('<span class="s">'+esc(m["sampleLabel"])+'</span>') if m.get("sample") else ''}<div class="n">{esc(m["tagline"])}</div><div class="n">{esc(m["handles"])}</div></div></header>
{clockhtml}
{coldstrip}
<div class="grid"><div class="col" style="flex:1">{headlines}{national}{mlbc}</div><div class="col">{weather}{hsc}{pro}</div><div class="col">{trend}{memes}{upto}</div></div>
<footer><span>{esc(foot_src.replace(" · full list in sources file","") if chk else foot_src)}{esc(chk_s)}</span><span>{obit_pdf}Links clickable · CONFIRM = verify</span></footer>
</div><script>window.addEventListener('load',function(){{var o=[].slice.call(document.querySelectorAll('.card')).filter(function(c){{var b=c.querySelector('.b');return b.scrollHeight>b.clientHeight+1}}).map(function(c){{return c.dataset.name}});document.body.setAttribute('data-overflow',o.join(','));}});</script></body></html>"""
    return html_

# ---------------------------------------------------------------- EMAIL
def email_html(data, preview=False):
    m, w = data["meta"], data["weather"]
    logo_src = b64(asset("assets/DITM_SunLogo.png"), "image/png") if preview else "cid:ditm-logo"
    thumb = data["headlines"].get("image")
    thumb_src = (b64(asset(thumb["file"]), "image/jpeg") if preview else "cid:ditm-story-photo") if thumb else None
    F = "font-family:Arial,Helvetica,sans-serif;"
    def h(t, c): return f'<tr><td style="background:{c};color:#ffffff;{F}font-size:14px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;padding:6px 12px">{t}</td></tr>'
    def sec(t, c, body): return f'<tr><td style="padding:8px 0 0"><table width="100%" cellpadding="0" cellspacing="0" style="border:2px solid #1b2430;border-radius:8px;border-collapse:separate">{h(t, c)}<tr><td style="padding:8px 12px;{F}font-size:14px;line-height:1.4;color:#1b2430">{body}</td></tr></table></td></tr>'
    A = lambda it, t=None: f'<a href="{esc(it["url"])}" style="color:#1b2430;text-decoration:underline">{esc(t or it["title"])}</a>' if it.get("url") else esc(t or it["title"])
    li = lambda x: f'<li style="margin-bottom:4px">{x}</li>'
    clock = "".join(f'<td style="background:{c["color"]};color:#fff;{F}font-size:12px;font-weight:bold;text-align:center;padding:5px 0" width="{max(c["minutes"]/60*100,3):.1f}%" title="{esc(c["title"])}">{c["letter"]}{"★" if c["signature"] else ""}</td>' for c in data.get("showClock", []))
    ns = m["nextShow"]
    clock_leg = " · ".join(f'<b>{c["letter"]}</b> {esc(c["short"])} {c["start"]}' for c in data.get("showClock", []))
    rgv = "".join(li(sc_email(i) + A(i, i["title"]) + f' <span style="color:#66788c;font-size:12px">{esc(i["source"])}</span>') for i in data["headlines"]["rgv"])
    tx = "".join(li(sc_email(i) + A(i) + f' <span style="color:#66788c;font-size:12px">{esc(i["source"])}</span>') for i in data["headlines"]["texas"])
    img_html = f'<img src="{thumb_src}" width="160" align="right" style="border-radius:6px;margin:0 0 6px 10px" alt="Starship"><div style="font-size:11px;color:#66788c;clear:both">{esc(thumb["caption"])}</div>' if thumb else ""
    nat = ""
    for n in data["nationalDesk"]:
        conf = f' <b style="color:#c1121f">[CONFIRM BEFORE AIR: {esc(conf_text(n))}]</b>' if n.get("confirm") else ""
        lks = " · ".join(f'<a href="{esc(l["url"])}" style="color:#6d597a">{esc(l["label"])}</a>' for l in n["links"][:3])
        nat += f'<p style="margin:0 0 8px">{sc_email(n)}<b>{esc(n["title"])}</b>{conf}<br>{esc(n["summary"])}<br><b style="color:#6d597a">Our take:</b> {esc(n["angle"])}<br><b style="color:#2a6f97">Why it matters in the Valley:</b> {esc(n["valley"])}<br><span style="font-size:12px">{lks}</span></p>'
    cells = "".join(f'<td align="center" style="{F}font-size:12px;padding:4px;border:1px solid #d5dde6;{"background:#fff3c4;" if d["date"]==w["monday"] else ""}"><b>{d["label"]} {d["dateLabel"].split()[1]}</b><br><span style="font-size:22px">{EMOJI[d["icon"]]}</span><br><b style="font-size:16px">{d["hi"]}°</b> / {d["lo"] if d["lo"] is not None else "–"}°<br><span style="color:#2a7de1">{d["pop"]}% rain</span></td>' for d in w["days"][:7])
    upd = datetime.datetime.fromisoformat(w["updated"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
    weather = f'<table width="100%" cellpadding="0" cellspacing="2"><tr>{cells}</tr></table><div style="font-size:12px;color:#4a5a6b;margin-top:4px">Source: <a href="{esc(w["pageUrl"])}">NWS {esc(w["office"])} forecast for McAllen</a>, updated {upd.strftime("%b %-d %-I:%M %p")} CT.</div>'
    hs = data["sports"]["highSchool"]
    sl, nl, nores, nonext = hs_texts(hs)
    hsb = (f"<b>{esc(sl.capitalize())}:</b><ul style='margin:0;padding-left:18px'>" + ("".join(li(A(r)) for r in hs["results"]) or f"<li>{esc(nores)}</li>") + f"</ul><b>{esc(nl)}:</b><ul style='margin:0;padding-left:18px'>" + ("".join(li(A(r)) for r in hs["next"]) or f"<li>{esc(nonext)}</li>") + f"</ul><div style='font-size:12px'>{A(hs['college'])}</div>")
    def lst(g, key="scores"):
        s = data["sports"][g]
        sc = "<br>".join(esc(b) for a, b in s.get("scores", []))
        nn = "<ul style='margin:6px 0 0;padding-left:18px'>" + "".join(li(A(i, i["short"] if False else i["title"])) for i in s["notable"]) + "</ul>"
        return sc, nn
    nfl = data["sports"]["nfl"]; nba = data["sports"]["nba"]; mlb = data["sports"]["mlb"]
    nflb = ("<br>".join(esc(b) for a, b in nfl["scores"]) or "No NFL games in this window.") + f"<br><span style='font-size:12px'>Source: {A(nfl['scoreSource'], 'NFL.com')}</span>" + lst("nfl")[1]
    nbab = ("<br>".join(esc(b) for a, b in nba["scores"]) or "No NBA games in this window.") + "<br><b>Texas teams:</b> " + ", ".join(esc(b) for a, b in nba["texas"]) + f"<br><span style='font-size:12px'>Source: {A(nba['scoreSource'], 'Basketball-Reference')}</span>" + lst("nba")[1]
    mlbb = f"<i>{esc(mlb['note'])}</i>" + lst("mlb")[1]
    memes = f'<div style="font-weight:bold;margin-bottom:6px">{esc(data["memes"]["tagline"])}. {esc(data["memes"]["intro"])}</div>'
    for lv in data["memes"]["levels"]:
        memes += f'<div style="font-weight:bold;font-size:15px;margin:8px 0 4px">{lv["icon"]} {esc(lv["level"])}</div>'
        for it in lv["items"]:
            tag = ' <span style="background:#e4572e;color:#fff;font-size:11px;padding:1px 5px;border-radius:3px">MEME OF THE WEEK</span>' if it["id"] == data["memes"].get("memeOfTheWeek") else ""
            conf = f' <b style="color:#c1121f">[CONFIRM BEFORE AIR: {esc(conf_text(it))}]</b>' if it.get("confirm") else ""
            lk = " · ".join(f'<a href="{esc(l["url"])}" style="color:#1b2430">{esc(l["label"])}</a>' for l in it["links"])
            memes += f'<p style="margin:0 0 8px"><b>{esc(it["title"])}</b>{tag}{conf}<br>{esc(it["what"])} <i>{esc(it["means"])}</i><br><b>How to bring it up:</b> {esc(it["tip"])}<br><span style="font-size:12px">{lk}</span></p>'
    rundown = '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">' + "".join(
        f'<tr><td style="{F}font-size:14px;padding:3px 0;border-bottom:1px dashed #c9d2dc"><b style="background:{c["color"]};color:#fff;padding:0 5px;border-radius:3px">{c["letter"]}</b> {esc(c["title"])} <span style="color:#66788c;font-size:12px">({c["minutes"]} min{", flex" if c["flex"] else ""}{", Jess" if c["jess"] else ""})</span></td>'
        f'<td align="right" width="92" style="{F}font-size:14px;font-weight:bold;white-space:nowrap;padding:3px 0;border-bottom:1px dashed #c9d2dc;font-variant-numeric:tabular-nums">{esc(c["timeRange"])}</td></tr>' for c in data.get("showClock", [])) + "</table>"
    co = data["coldOpen"]
    coldopen_b = (f'<p style="margin:0 0 6px;font-size:16px;line-height:1.5">{esc(co["text"])}</p><p style="margin:0;background:#fff8e0;border-left:5px solid #f2b705;padding:5px 9px"><b>Jingle:</b> {esc(co["jingle"])}</p>'
                  + (f'<p style="margin:6px 0 0"><b style="color:#c1121f">[CONFIRM BEFORE AIR: {esc("; ".join(co["confirm"]))}]</b> (not part of the spoken text)</p>' if co["confirm"] else ""))
    um = data["up_to_meta"]
    ev_li = "".join(li(f'<b>{esc(e["label"])}</b> · {esc(upto_when(e))}') for e in data["up_to"]) + "".join(li(f'<b>Coming up:</b> {esc(e["label"])} · {esc(upto_when(e))}') for e in data["up_to_coming"])
    upto_b = (f'<p style="margin:0 0 6px">{esc(data["up_to_script"])}</p>' + (f"<ul style='margin:0;padding-left:18px'>{ev_li}</ul>" if ev_li else '<p style="margin:0"><b>Quiet week on the family calendar.</b></p>')
              + f'<div style="font-size:12px;color:#66788c;margin-top:4px">{esc(um.get("calendar", ""))}, {esc(um.get("window", ""))}. Family-friendly items only, in generic wording.</div>')
    trend_b = ""
    for t in [x for x in data.get("trending", []) if x.get("print")][:6]:
        c = trend_item_conf(t)
        trend_b += (f'<p style="margin:0 0 6px">{sc_email(t)}<b>{A({"url": t["source_url"], "title": t["title"]}) if t.get("source_url") else esc(t["title"])}</b> <span style="background:#577590;color:#fff;font-size:11px;padding:0 5px;border-radius:3px">{esc(t["category"].upper())}</span>'
                    + (f' <b style="color:#c1121f">[CONFIRM BEFORE AIR: {esc(c)}]</b>' if c else "") + f'<br>{esc(t["one_line"])}<br><b style="color:#577590">Riff:</b> {esc(t["suggested_angle"])}</p>')
    tech_b = ""
    for t in data["tech"]["items"]:
        tech_b += (f'<p style="margin:0 0 6px"><b>{A({"url": t["source_url"], "title": t["title"]}) if t.get("source_url") else esc(t["title"])}</b> <span style="background:#3d5a80;color:#fff;font-size:11px;padding:0 5px;border-radius:3px">{esc(t.get("source", "TECH").upper())}</span>'
                   + (f' <b style="color:#c1121f">[CONFIRM BEFORE AIR: {esc(t["confirm"])}]</b>' if t["confirm"] else "") + f'<br>{esc(t["one_line"])}<br><b style="color:#3d5a80">On-air angle:</b> {esc(t["angle"])}</p>')
    tech_b = f'<p style="margin:0 0 6px;font-size:12px;color:#66788c"><b>{esc(data["tech"]["badge"])}</b>. {esc(data["tech"]["originLabel"])}</p>' + (tech_b or '<p style="margin:0">Nothing loaded today.</p>')
    chd = data["chisme"]
    if chd["items"]:
        chisme_b = f'<p style="margin:0 0 6px;font-size:12px;color:#b00020"><b>{esc(CHISME_BADGE)}</b>. Local social buzz, last 72 hours. Tease it as "people are talking about…", never as fact.</p>'
        for c in chd["items"]:
            tag = (f'<span style="background:#e4572e;color:#fff;font-size:11px;padding:0 5px;border-radius:3px">CONFIRMED · {esc(c["confirmedBy"]["outlet"])}</span>' if c.get("confirmedBy") else f'<b style="color:#c1121f">[{esc(CHISME_BADGE)}]</b>')
            chisme_b += (f'<p style="margin:0 0 6px"><b><a href="{esc(c["url"])}" style="color:#0b5cad">{esc(c["title"])}</a></b> <span style="color:#66788c;font-size:12px">{esc(c["platform"])} · {esc(c["source"])}</span> {tag}'
                         + (f'<br>{esc(c["tldr"])}' if c.get("tldr") else "") + (f'<br><b style="color:#b5179e">Riff:</b> {esc(c["riff"])}' if c.get("riff") else "") + '</p>')
    else:
        chisme_b = '<p style="margin:0">Nothing passed the safety filter today (or the sources could not be read). Nothing is made up.</p>'
    ob = data["obituaries"]
    if ob["count"]:
        obit_b = f'<p style="margin:0 0 6px;font-size:12px;color:#66788c">{ob["count"]} obituaries The Monitor ran on Legacy.com, {esc(ob["windowLabel"])}. Names, ages, towns and funeral homes are only what each notice lists. Read near the close, block L.</p>'
        obit_b += f'<p style="margin:0 0 8px"><b>On-air read:</b> {esc(ob["script"])}</p>'
        for g in ob["groups"][:1]:
            obit_b += f'<p style="margin:8px 0 2px"><b>{esc(g["label"])}</b> ({len(g["items"])})</p><ul style="margin:0;padding-left:18px">' + "".join(
                f'<li><a href="{esc(r["url"])}" style="color:#0b5cad">{esc(r["name"])}</a>' + esc(obit_line(r)[len(r["name"]):]) + '</li>' for r in g["items"]) + "</ul>"
        _prev = sum(len(g["items"]) for g in ob["groups"][1:])
        if _prev: obit_b += f'<p style="margin:6px 0 0;font-size:12px;color:#66788c">Plus {_prev} from the week before: on the studio page, under "Show the previous week".</p>'
        obit_b += f'<p style="margin:8px 0 0;font-size:12px"><a href="{esc(ob["sourceUrl"])}">{esc(ob["source"])}</a></p>'
    else:
        obit_b = '<p style="margin:0">No obituaries loaded today. The on-air read is skipped.</p>'
    if m["mode"] == "monday":
        clock_block = f'''<tr><td><table width="100%" cellpadding="0" cellspacing="0" style="border:1.5px solid #1b2430;border-radius:6px;border-collapse:separate"><tr>{clock}</tr></table><div style="{F}font-size:12px;color:#33404f;padding:3px 0">{clock_leg} (★ = signature segment; full 60-minute plan, blocks marked flex can be trimmed or stretched)</div></td></tr>'''
    else:
        clock_block = f'''<tr><td><div style="background:#264653;color:#ffffff;{F}font-size:13px;font-weight:bold;padding:6px 10px;border-radius:6px"><span style="color:#ffd23f;letter-spacing:1px">NEXT SHOW</span> · {esc(ns["label"])} · 8:00-9:00 AM CT · 60 min · Monday 8 AM rundown</div><div style="{F}font-size:12px;color:#33404f;padding:3px 0">{clock_leg}</div></td></tr>'''
    body = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{esc(m["emailSubject"])}</title></head><body style="margin:0;padding:0;background:#fffdf6"><table width="100%" cellpadding="0" cellspacing="0" style="background:#fffdf6"><tr><td align="center"><table width="680" cellpadding="0" cellspacing="0" style="width:680px;max-width:100%">
<tr><td style="padding:12px 0"><table width="100%" cellpadding="0" cellspacing="0"><tr><td width="190"><img src="{logo_src}" width="180" alt="Drew in the Morning" style="background:#fff;border:2px solid #1b2430;border-radius:10px;padding:4px"></td><td style="{F}padding-left:12px"><div style="font-size:12px;letter-spacing:2px;font-weight:bold;color:#b5651d">{esc(m["kicker"].upper())}</div><div style="font-size:26px;font-weight:bold;color:#1b2430">{esc(m["dateLabel"])}</div><div style="font-size:13px;color:#4a5a6b">{esc(m["recap"])}</div>{('<div style="margin-top:4px"><span style="background:#e4572e;color:#fff;font-size:12px;font-weight:bold;padding:3px 9px;border-radius:99px">'+esc(m["sampleLabel"])+'</span></div>') if m.get("sample") else ''}</td></tr></table></td></tr>
{clock_block}
{sec("Cold Open &amp; Jingle", "#f2b705", coldopen_b).replace("color:#ffffff;", "color:#1b2430;", 1)}
{sec("What I've Been Up To This Week", "#d1495b", upto_b)}
{sec("Top Headlines · RGV First", "#e4572e", img_html + "<ul style='margin:0;padding-left:18px'>" + rgv + "</ul><b>Texas:</b><ul style='margin:0;padding-left:18px'>" + tx + "</ul>")}
{sec("Chisme · what the Valley is buzzing about", "#b5179e", chisme_b)}
{sec("Trending News", "#577590", trend_b + '<div style="font-size:12px;color:#66788c">What\'s trending around the nation, separate from the National Desk. The studio page has all of them with links.</div>')}
{sec("McAllen / RGV Weather", "#2a7de1", weather)}
{sec("RGV High School Football", "#2a9d8f", hsb)}
{sec(esc(sport_title(nfl).replace("NFL ", "NFL · ", 1)), "#264653", nflb)}
{sec(esc(sport_title(nba, False) + (" · " + nba["window"] if nba.get("window") else "")), "#c1121f", nbab)}
{sec("MLB · Offseason (no scores)", "#003f88", mlbb)}
{sec("Meme of the Week · What the Kids Are Talking About", "#ff7f50", memes)}
{sec("The National Desk", "#6d597a", nat)}
{sec("What's Happening in Tech", "#3d5a80", tech_b)}
{sec("Remembering Our Neighbors", "#5c6b7a", obit_b)}
{sec("On the Show: Monday's 60-minute plan (times as planned from 8:00; Show Start on the studio page shifts them)" if m["mode"] == "monday" else "Next show: Monday 8 AM rundown (" + esc(ns["label"]) + ")", "#264653", rundown + '<div style="font-size:12px;color:#4a5a6b">Studio page and run of show have notes and links for every block.</div>')}
<tr><td style="{F}font-size:11px;color:#66788c;padding:10px 0">Every fact is sourced and linked above. CONFIRM BEFORE AIR means verify before saying it on air. Weather: NWS. Scores: sources linked in each section. Not sent automatically unless the Monday routine is approved.</td></tr>
</table></td></tr></table></body></html>"""
    return body

# ---------------------------------------------------------------- TXT / SOURCES
def txt(data):
    m, w = data["meta"], data["weather"]
    o = []
    W = lambda s="": o.append(s)
    wrap = lambda s, ind="  ": textwrap.fill(s, 92, initial_indent=ind, subsequent_indent=ind + "  ")
    bar = "=" * 92
    W(bar); W("DREW IN THE MORNING"); W(m["headline"] + (" · 8:00 AM CT show · Live from McAllen, Texas" if m["mode"] == "monday" else " · updated 6 AM CT"))
    if m.get("sample"): W("*** " + m["sampleLabel"] + " ***")
    W(m["recap"]); W(m["tagline"]); W(bar); W()
    ns = m["nextShow"]
    W("SHOW CLOCK (60 minutes; FLEX = can trim/stretch; * = signature segment)" if m["mode"] == "monday" else f"NEXT SHOW: {ns['label'].upper()}, 8:00-9:00 AM CT · Monday 8 AM rundown (this briefing is the story bank for it)")
    for c in data.get("showClock", []):
        W(f"  {c['timeRange']:<11} {c['letter']}  {c['title']} ({c['minutes']} min{', FLEX ' + str(c['trimTo']) + '-' + str(c['stretchTo']) if c['flex'] else ''}{', Jess' if c['jess'] else ''}){' *' if c['signature'] else ''}")
    W()
    co = data["coldOpen"]
    W("COLD OPEN (read aloud, about 45 seconds)"); W(textwrap.fill(co["text"], 92, initial_indent="  ", subsequent_indent="  ")); W("  JINGLE: " + co["jingle"])
    if co["confirm"]: W(wrap("CONFIRM BEFORE AIR (teased, unconfirmed; not part of the spoken text): " + "; ".join(co["confirm"])))
    W()
    um = data["up_to_meta"]
    W("WHAT I'VE BEEN UP TO THIS WEEK (block B, 2-3 min, from the family calendar) · " + um["banner"])
    W(textwrap.fill(data["up_to_script"], 92, initial_indent="  ", subsequent_indent="  "))
    for x in upto_lines(data): W(wrap("- " + x))
    if not data["up_to"] and not data["up_to_coming"]: W("  Quiet week on the family calendar.")
    W(wrap(f"Window {um.get('window', 'past 7 days')}" + (f"; coming up {um['comingWindow']}" if um.get("comingWindow") else "") + f". Calendar: {um.get('calendar', '')}. Family-friendly items only, generic wording."))
    if um.get("internal"): W(wrap("INTERNAL NOTE (not for air): " + um["internal"]))
    W()
    sc = data.get("scoring")
    if sc: W(wrap(f"STORY SCORES: HOT / TREND / ACT label + score per item (formula in packet/README.md). {sc['items']} stories, {sc['merged']} duplicate(s) merged, {sc['hot']} hot, {sc['trending']} trending, {sc['uncovered']} uncovered lead(s). {sc['trendsNote']}.", "")); W()
    W("TOP HEADLINES · RGV FIRST")
    for i in data["headlines"]["rgv"]:
        W(wrap("- " + sc_txt(i) + i["title"] + f" ({i['source']})" + (f" +{len(i['sources']) - 1} more source(s)" if len(i.get("sources") or []) > 1 else ""))); W("    " + i["url"])
    W("  Texas:")
    for i in data["headlines"]["texas"]:
        W(wrap("- " + sc_txt(i) + i["title"] + f" ({i['source']})")); W("    " + i["url"])
    W("  Photo: " + data["headlines"]["image"]["caption"] + " " + data["headlines"]["image"]["credit_url"]); W()
    W(f"CHISME · what the Valley is buzzing about · {CHISME_BADGE} · last 72 hours")
    for c in data["chisme"]["items"]:
        W(wrap("- " + c["title"] + f" ({c['platform']} · {c['source']})" + (f" [CONFIRMED by {c['confirmedBy']['outlet']}]" if c.get("confirmedBy") else f" [{CHISME_BADGE}]"))); W("    " + c["url"])
        if c.get("tldr"): W(wrap("    TL;DR: " + c["tldr"]))
        if c.get("riff"): W(wrap("    Riff: " + c["riff"]))
    if not data["chisme"]["items"]: W("  (nothing passed the safety filter today, or the sources could not be read)")
    W()
    W("TRENDING NEWS · what's trending around the nation (separate from the National Desk)")
    for t in data.get("trending", []):
        c = trend_item_conf(t)
        W(f"- {sc_txt(t)}{t['title']}  [{t['category']}]" + (f"  [CONFIRM BEFORE AIR: {c}]" if c else ""))
        W(wrap("SUMMARY: " + t["one_line"], "    ")); W(wrap("RIFF: " + t["suggested_angle"], "    "))
        if t.get("source_url"): W(f"    {t.get('source', 'Source')}: {t['source_url']}")
        for l in t.get("links", []): W(f"    {l['label']}: {l['url']}")
    W()
    W("THE NATIONAL DESK (smaller; local leads)")
    for n in data["nationalDesk"]:
        W(f"- {sc_txt(n)}{n['title'].upper()}"); W(wrap("FACT: " + n["summary"], "    ")); W(wrap("OUR TAKE: " + n["angle"], "    ")); W(wrap("WHY IT MATTERS IN THE VALLEY: " + n["valley"], "    "))
        if n.get("detail"): W(wrap("DETAIL: " + n["detail"], "    "))
        if n.get("confirm"): W(wrap("CONFIRM BEFORE AIR: " + conf_text(n), "    "))
        for l in n["links"]: W(f"    {l['label']}: {l['url']}")
    W()
    tk = data["tech"]
    W("WHAT'S HAPPENING IN TECH (sub-segment of block J, after the National Desk) [" + tk["badge"] + "]")
    W(wrap(tk["originLabel"], "  "))
    for t in tk["items"]:
        W(f"- {t['title']}  ({t.get('source', '')})" + (f"  [CONFIRM BEFORE AIR: {t['confirm']}]" if t["confirm"] else ""))
        W(wrap("SUMMARY: " + t["one_line"], "    ")); W(wrap("ON-AIR ANGLE: " + t["angle"], "    "))
        if t.get("source_url"): W(f"    Link: {t['source_url']}")
        for l in t.get("links", []): W(f"    {l['label']}: {l['url']}")
    if not tk["items"]: W("  (nothing loaded today)")
    W()
    ob = data["obituaries"]
    W(f"REMEMBERING OUR NEIGHBORS (read near the close, block L) · {ob['count']} obituaries from The Monitor on Legacy.com, {ob['windowLabel']}")
    if ob["count"]:
        W(wrap("Only what each notice lists: no cause of death. CONFIRM name pronunciations before reading.", "  "))
        W(wrap("ON-AIR READ: " + ob["script"], "  "))
        for g in ob["groups"][:1]:
            W(f"  {g['label']} ({len(g['items'])})")
            for r in g["items"]:
                W("    - " + obit_line(r)); W("      " + r["url"])
        _prev = sum(len(g["items"]) for g in ob["groups"][1:])
        if _prev: W(f"  Plus {_prev} from the week before: on the studio page, under 'Show the previous week'.")
        W(f"  Source page: {ob['sourceUrl']}")
    else:
        W("  (no obituaries loaded today; skip the read)")
    W()
    W("WEATHER · McALLEN / RGV (" + w["source"] + ")")
    for d in w["days"][:7]:
        W(f"  {d['label']} {d['dateLabel']:<7} {'<< SHOW DAY ' if d['date']==w['monday'] else ''}{d['short']}, high {d['hi']}F / low {d['lo'] if d['lo'] is not None else '--'}F, rain {d['pop']}%, wind {d['wind']}")
    W("  Alerts: " + ("none active" if w.get("alerts") == [] else (", ".join(w["alerts"]) if w.get("alerts") else "not checked")))
    W(f"  Updated {w['updated']} (UTC). Forecast page: {w['pageUrl']}"); W(f"  NWS Brownsville office: {w['officeUrl']}"); W(f"  API: {w['apiUrl']}"); W()
    hs = data["sports"]["highSchool"]
    sl, nl, nores, nonext = hs_texts(hs)
    W("RGV HIGH SCHOOL FOOTBALL · " + hs["round"] + " · " + sl)
    if not hs["results"]: W("  " + nores)
    for r in hs["results"]:
        W(f"  - {r['title']}" + (f"  [CONFIRM BEFORE AIR: {conf_text(r)}]" if r.get("confirm") else "")); W("      " + r["url"])
    W("  " + nl + ":")
    if not hs["next"]: W("    " + nonext)
    for r in hs["next"]:
        W(wrap("- " + r["title"], "    ")); W("      " + r["url"])
    W("  College: " + hs["college"]["title"] + "  " + hs["college"]["url"]); W()
    for g, label in (("nfl", sport_title(data["sports"]["nfl"]).upper().replace("NFL ", "NFL · ", 1)), ("nba", sport_title(data["sports"]["nba"]).upper())):
        s = data["sports"][g]
        W(label + "  (scores: " + s["scoreSource"]["url"] + ")")
        if not s["scores"]: W(f"  No {g.upper()} games in this window.")
        for a, b in s["scores"]: W(f"  {a}: {b}")
        if g == "nba":
            for a, b in s["texas"]: W(f"  Texas teams, {a}: {b}")
        for i in s["notable"]:
            W(wrap("- " + i["title"], "  ")); W("    " + i["url"])
        W()
    s = data["sports"]["mlb"]
    W("MLB · OFFSEASON (no scores in November; news instead)"); W(wrap(s["note"]))
    for i in s["notable"]:
        W(wrap("- " + i["title"], "  ")); W("    " + i["url"])
    W()
    W("MEME OF THE WEEK · WHAT THE KIDS ARE TALKING ABOUT"); W(data["memes"]["tagline"]); W(data["memes"]["intro"])
    for lv in data["memes"]["levels"]:
        W(); W(f"  {lv['level'].upper()}")
        for it in lv["items"]:
            tag = "  [MEME OF THE WEEK]" if it["id"] == data["memes"].get("memeOfTheWeek") else ""
            W(f"  - {it['title']}{tag}"); W(wrap("What: " + it["what"], "      ")); W(wrap("Means: " + it["means"], "      ")); W(wrap("How to bring it up: " + it["tip"], "      "))
            if it.get("confirm"): W(wrap("CONFIRM BEFORE AIR: " + conf_text(it), "      "))
            for l in it["links"]: W(f"      {l['label']}: {l['url']}")
    W(); W("ON THE SHOW: see run-of-show-monday.md (12 blocks A-L, 60 minutes) and the studio page for notes, follow-up questions and links." if m["mode"] == "monday" else f"NEXT SHOW: {ns['label']}, 8 AM CT. The Monday 8 AM rundown (12 blocks A-L, 60 minutes) is in the studio page and run-of-show-monday.md.")
    W(); W(bar); W("Every fact above has a source URL. CONFIRM BEFORE AIR = verify before saying it on air. Generated " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M CT") + ".")
    if data.get("linkCheck"): c = data["linkCheck"]; W(f"Links checked {c['date']}: {c['ok']} ok, {c['blocked']} blocked by the site's bot protection (verified in a browser/search), {c['dead']} dead, {c['unreachable']} unreachable.")
    return "\n".join(o) + "\n"

def sources_txt(data):
    o = ["Sources for " + data["meta"]["fileStem"], ""]
    cur = None
    for u in all_urls(data):
        if u["section"] != cur: cur = u["section"]; o += ["", cur]
        lc = data.get("linkCheckDetail", {}).get(u["url"], {}).get("result", "")
        o.append(f"  - {u['label']}: {u['url']}" + (f"  [{lc}]" if lc else ""))
    return "\n".join(o) + "\n"

# ---------------------------------------------------------------- STUDIO
STUDIO_CSS = """
:root{--bg:#fffdf6;--fg:#1b2430;--card:#fff;--line:#1b2430;--mut:#5a6b7d;--acc:#e4572e;--link:#0b5cad;--chip:#f1ece0;--ok:#1f9d55;
--fs:clamp(13px,1.1vw + 5px,16px);--hh:108px;--sl:env(safe-area-inset-left,0px);--sr:env(safe-area-inset-right,0px);--st:env(safe-area-inset-top,0px);--sb:env(safe-area-inset-bottom,0px)}
[data-theme=dark]{--bg:#10151c;--fg:#eef2f6;--card:#1a222d;--line:#4c5d70;--mut:#9fb0c2;--link:#7cc0ff;--chip:#263140;--ok:#37c97a}
*{box-sizing:border-box;-webkit-tap-highlight-color:rgba(228,87,46,.28)}
html{font-size:var(--fs);-webkit-text-size-adjust:100%;text-size-adjust:100%;touch-action:manipulation;scroll-padding-top:calc(var(--hh) + 8px);color-scheme:light}
[data-theme=dark]{color-scheme:dark}
[id]{scroll-margin-top:calc(var(--hh) + 8px)}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Inter,-apple-system,BlinkMacSystemFont,'SF Pro Text','Segoe UI',Roboto,Arial,sans-serif;line-height:1.28;overflow-wrap:break-word;touch-action:manipulation}
a,button,summary{touch-action:manipulation}
img,svg{max-width:100%;height:auto}
a{color:var(--link)}
header{position:relative;z-index:6;background:var(--bg);border-bottom:2px solid var(--line);padding:max(6px,var(--st)) max(12px,var(--sr)) 6px max(12px,var(--sl));display:flex;gap:clamp(6px,1.2vw,12px);align-items:center;flex-wrap:wrap}
header>img{height:clamp(44px,6vw,64px);width:auto;max-width:34vw;background:#fff;border-radius:10px;border:2px solid #1b2430;padding:2px 8px;flex:none}
.ht{flex:1 1 300px;min-width:0}.ht .k{font-size:clamp(.66rem,.5vw + .5rem,.78rem);letter-spacing:.14em;font-weight:800;color:#b5651d;text-transform:uppercase}
.ht .d{font-size:clamp(1.3rem,2.4vw + .5rem,2rem);font-weight:900;line-height:1.05}.ht .t{font-size:clamp(.74rem,.6vw + .55rem,.9rem);color:var(--mut);font-weight:600}
.sample{background:var(--acc);color:#fff;border-radius:99px;padding:2px 10px;font-weight:800;font-size:.8rem;text-transform:none;letter-spacing:0;display:inline-block}
.tools{margin:6px 0 0;display:flex;gap:6px;flex-wrap:wrap}
button{font:inherit;cursor:pointer;border:2px solid var(--line);background:var(--chip);color:var(--fg);border-radius:10px;padding:4px 12px;font-weight:700;min-height:44px;min-width:44px;touch-action:manipulation}
button:active{transform:scale(.97)}
:focus-visible{outline:3px solid var(--link);outline-offset:2px}
@media (hover:hover){button:hover{background:var(--acc);color:#fff;border-color:var(--acc)}a:hover{text-decoration:underline}nav a:hover,.clock a:hover{filter:brightness(1.1)}}
#clockw{margin-left:auto;text-align:right;background:var(--card);border:2px solid var(--line);border-radius:12px;padding:clamp(3px,.5vw,6px) clamp(8px,1.4vw,14px) clamp(3px,.6vw,7px);min-width:clamp(190px,24vw,290px);max-width:100%;line-height:1.15;font-variant-numeric:tabular-nums;flex:none}
#cw-time{font-size:clamp(1.55rem,2.6vw + .5rem,2.45rem);font-weight:900;letter-spacing:.01em;white-space:nowrap}
.cwd{font-size:clamp(.74rem,.6vw + .5rem,.88rem);font-weight:700}
.cwx{font-size:clamp(.82rem,.6vw + .6rem,.98rem);font-weight:800;margin-top:3px;display:flex;gap:6px;justify-content:flex-end;align-items:baseline;flex-wrap:wrap}
.cwx small{color:var(--mut);font-weight:600;font-size:.72rem}#cw-ico{font-size:1.1em}#cw-cond{font-weight:600;font-size:.82em;color:var(--mut)}
#usedbar{background:var(--chip);border-bottom:2px solid var(--line);padding:4px max(12px,var(--sr)) 4px max(12px,var(--sl));display:flex;align-items:center;gap:4px 8px;flex-wrap:wrap}
#usedbar .ubl{font-weight:800}#usedbar .ubl b{display:inline-block;min-width:1.6em;text-align:center;background:var(--ok);color:#fff;border-radius:99px;padding:0 8px}
#ustatus{color:var(--mut);font-size:.8rem;font-weight:600;flex:1 1 160px}
#usedbar .ubb{display:flex;gap:8px;margin-left:auto;flex-wrap:wrap}
.btnlike{display:inline-flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;padding:4px 12px;border:2px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg);font-weight:700;text-decoration:none}
nav{display:flex;gap:4px;flex-wrap:wrap;padding:4px max(12px,var(--sr)) 4px max(12px,var(--sl))}
nav a{background:var(--chip);border-radius:99px;padding:6px 10px;min-height:44px;display:inline-flex;align-items:center;font-weight:700;font-size:.78rem;text-decoration:none;color:var(--fg);border:1px solid var(--line)}
.clock{display:flex;position:relative;margin:2px max(12px,var(--sr)) 0 max(12px,var(--sl));height:32px;border-radius:8px;overflow:hidden;border:2px solid var(--line)}
.clock a{display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;font-weight:900;text-decoration:none;border-right:1px solid rgba(255,255,255,.6);font-size:clamp(.85rem,1vw + .4rem,1.15rem);line-height:1;min-width:0}.clock a small{font-size:clamp(.55rem,.5vw + .35rem,.7rem);font-weight:700;opacity:.95}
main{padding:4px max(12px,var(--sr)) calc(28px + var(--sb)) max(12px,var(--sl));display:grid;grid-template-columns:minmax(0,1fr);gap:6px;align-items:stretch}
details{background:var(--card);border:2px solid var(--line);border-radius:8px;overflow:hidden;min-width:0}
summary{cursor:pointer;list-style:none;padding:6px 10px;min-height:44px;color:#fff;font-weight:900;letter-spacing:.05em;text-transform:uppercase;display:flex;justify-content:space-between;align-items:center;gap:4px 10px;flex-wrap:wrap;font-size:clamp(.92rem,.8vw + .65rem,1.15rem)}
summary::-webkit-details-marker{display:none}summary small{font-weight:600;text-transform:none;letter-spacing:0;opacity:.95;font-size:.78em}
summary:after{content:'\\25BE';margin-left:auto;font-size:1.2em;padding-left:6px}details:not([open])>summary:after{content:'\\25B8'}
.body{padding:6px clamp(8px,1.2vw,12px);min-width:0}
.item{display:flex;gap:6px;align-items:center;padding:4px 0;border-bottom:1px dashed var(--line)}.item:last-child{border:0}
.item .tx{flex:1 1 auto;min-width:0}.item .tx>a{font-weight:700}.src{color:var(--mut);font-size:.8rem;font-weight:600}
.acts{display:flex;gap:6px;flex:none;align-items:center}
.cp{font-size:.74rem;padding:2px 8px;flex:none}.cf{display:inline-block;background:#c1121f;color:#fff;font-size:.7rem;font-weight:900;border-radius:4px;padding:0 5px}
.gp{display:contents}
.gp>summary{cursor:pointer;font-weight:800;padding:10px 14px;min-height:44px;display:flex;align-items:center}
.gpb{display:flex;gap:14px;flex-wrap:wrap;padding:4px 14px 12px}.gpc{flex:1 1 300px;min-width:0;display:flex;flex-direction:column;gap:6px}
.gpc h4{margin:0;font-size:.95rem}.gpc label{display:flex;flex-direction:column;font-size:.72rem;font-weight:700;color:var(--mut);gap:2px}
.gpc input[type=text],.gpc input[type=url]{font:inherit;font-size:1rem;min-height:44px;padding:6px 10px;border:2px solid var(--line);border-radius:10px;background:var(--bg);color:var(--fg);width:100%;box-sizing:border-box}
.gpa{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.gpa button,.upl{min-height:44px;min-width:44px;padding:0 14px;font-size:.85rem;font-weight:800}
.upl{display:inline-flex!important;flex-direction:row!important;align-items:center;border:2px solid var(--line);border-radius:10px;cursor:pointer;color:var(--fg)!important;background:var(--card);position:relative;overflow:hidden}.upl input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
#c-prev{width:44px;height:44px;object-fit:cover;border-radius:8px}.gpm{font-size:.78rem;color:var(--mut)}
.chysend{display:none;align-items:center;gap:4px;min-height:44px;min-width:44px;padding:0 10px;border-radius:12px;border-width:3px;font-size:.78rem;font-weight:800;flex:none;background:var(--card);white-space:nowrap}
body.chy-on .chysend{display:inline-flex}.chysend .ci{font-size:.8em}
.chysend[aria-pressed=true]{background:#e4572e;border-color:#e4572e;color:#fff}
.onair{outline:3px solid #e4572e;outline-offset:-1px;background:rgba(228,87,46,.10)!important;position:relative}
.onair:before{content:"ON AIR";position:absolute;top:-9px;right:10px;background:#e4572e;color:#fff;font-size:.62rem;font-weight:900;letter-spacing:.08em;border-radius:4px;padding:1px 6px}
.ob .obn{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.ob .chysend{margin-left:auto}
.use{width:48px;height:48px;min-width:48px;min-height:48px;padding:0;border-radius:12px;border-width:3px;display:inline-flex;align-items:center;justify-content:center;flex:none;background:var(--card)}
.use .ck{width:26px;height:26px;border-radius:7px;border:3px solid var(--mut);display:block;background:transparent center/85% no-repeat}
.use[aria-pressed=true]{background:var(--ok);border-color:var(--ok);color:#fff}
.use[aria-pressed=true] .ck{border-color:#fff;background-color:#fff;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M5 12.5l4.5 4.5L19 7' fill='none' stroke='%231f9d55' stroke-width='3.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")}
@media (hover:hover){.use:hover{border-color:var(--ok);background:var(--card)}.use[aria-pressed=true]:hover{background:var(--ok);filter:brightness(1.1)}}
.used{background:rgba(31,157,85,.14)}.item.used .tx>a{text-decoration:line-through;opacity:.75}
.upill{display:none;background:var(--ok);color:#fff;font-size:.68rem;font-weight:900;border-radius:4px;padding:0 5px;margin-left:4px}.used>.tx .upill,.used>.uhead .upill,.uhead.used .upill{display:inline-block}
.ub{display:inline-block;background:#6b7785;color:#fff;font-size:.68rem;font-weight:800;border-radius:4px;padding:0 5px}
.uhead{display:flex;align-items:center;gap:10px;justify-content:space-between;margin:0 0 6px;font-weight:800;border-bottom:1px dashed var(--line);padding-bottom:6px}
.wk{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:6px;text-align:center}.wk div{border:2px solid var(--line);border-radius:10px;padding:4px;min-width:0}.wk .mon{background:#fff3c4;border-color:#f2a900;color:#1b2430}
.hi{font-size:1.25rem;font-weight:900}.mut{color:var(--mut)}.pp{color:#2a7de1;font-weight:800}
.scores{columns:3 210px;column-gap:20px;margin:0;padding:0;list-style:none}.scores li,.scores .item{break-inside:avoid;padding:1px 0}
.lvl{border-left:6px solid;padding-left:10px;margin:8px 0}.lvl h3{margin:0 0 4px;text-transform:uppercase;letter-spacing:.05em;font-size:clamp(.9rem,.6vw + .7rem,1.05rem)}
.motw{background:#fff1e8;color:#1b2430;border:2px dashed #e4572e;border-radius:10px;padding:4px 8px}.motw a{color:#0b5cad}
.tag{background:#e4572e;color:#fff;font-weight:900;font-size:.7rem;padding:1px 6px;border-radius:4px}
.mbox{margin:0 0 10px}.mbox.used{border-radius:10px;padding:4px 6px}
.rdgrid{display:flex;flex-direction:column;gap:6px}

.rd{border:2px solid var(--line);border-radius:8px;margin:4px 0;background:var(--card)}.rdgrid>.rd{margin:0}.rd>summary{border-radius:0;min-height:48px}
.rd .bl{display:inline-flex;align-items:center;justify-content:center;width:2.5rem;height:2.5rem;border-radius:10px;background:rgba(255,255,255,.25);font-size:1.6rem;font-weight:900;margin-right:8px;flex:none;letter-spacing:0}
.rd .rt{display:flex;align-items:center;min-width:0;flex:1 1 220px}
.rd h4{margin:8px 0 3px;font-size:.85rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}.rd ul{margin:0;padding-left:20px}
.chy{display:inline-block;background:#1b2430;color:#fff;border-radius:6px;padding:2px 8px;margin:2px;font-size:.85rem}.chy b{color:#ffd23f}
#usedul{margin:0;padding-left:20px}#usedul li{margin-bottom:4px}
#toast{position:fixed;bottom:calc(18px + var(--sb));left:50%;transform:translateX(-50%);background:#1b2430;color:#fff;padding:8px 16px;border-radius:99px;font-weight:700;opacity:0;transition:.25s;pointer-events:none;z-index:9;max-width:92vw}#toast.on{opacity:1}
.obl{list-style:none;margin:0 0 8px;padding:0}.obl li{padding:5px 0;border-bottom:1px dashed var(--line)}.obh{margin:10px 0 2px;font-size:1rem}
footer{padding:10px max(16px,var(--sr)) calc(30px + var(--sb)) max(16px,var(--sl));color:var(--mut);font-size:.8rem}
@media (pointer:coarse){.cp{min-height:44px;min-width:56px}}
@media print{#pin{position:static}#minibar,#ph{display:none}header,#usedbar{position:static}.cp,.use,#clockw,#usedbar,.tools{display:none}}
"""
CLOCK_JS = r"""
(function(){var w=document.getElementById('clockw');if(!w)return;var TZ='America/Chicago';
var tf=new Intl.DateTimeFormat('en-US',{timeZone:TZ,hour:'numeric',minute:'2-digit',second:'2-digit',hour12:true}),
wf=new Intl.DateTimeFormat('en-US',{timeZone:TZ,weekday:'long'}),df=new Intl.DateTimeFormat('en-US',{timeZone:TZ,month:'long',day:'numeric',year:'numeric'}),
hm=new Intl.DateTimeFormat('en-US',{timeZone:TZ,hour:'numeric',minute:'2-digit'}),hh=new Intl.DateTimeFormat('en-US',{timeZone:TZ,hour:'numeric',hour12:false});
var $=function(i){return document.getElementById(i)},live=false,OBS=w.dataset.obs,HR=w.dataset.hourly;
function tick(){var n=new Date();$('cw-time').textContent=tf.format(n);$('cw-dow').textContent=wf.format(n);$('cw-date').textContent=df.format(n)}
tick();setInterval(tick,1000);
function ico(t){t=(t||'').toLowerCase();var h=parseInt(hh.format(new Date()),10)%24,night=h<6||h>=19;
if(/thunder|t-storm/.test(t))return'\u26C8\uFE0F';if(/rain|shower|drizzle/.test(t))return'\uD83C\uDF27\uFE0F';if(/snow|sleet|ice|freezing/.test(t))return'\u2744\uFE0F';
if(/fog|mist|haze|smoke/.test(t))return'\uD83C\uDF2B\uFE0F';if(/partly|mostly sunny|mostly clear|few clouds|scattered/.test(t))return night?'\u2601\uFE0F':'\u26C5';
if(/cloud|overcast/.test(t))return'\u2601\uFE0F';return night?'\uD83C\uDF19':'\u2600\uFE0F'}
function put(f,c,note,title){$('cw-temp').textContent=f+'\u00B0F';$('cw-cond').textContent=c||'';$('cw-ico').textContent=ico(c);$('cw-note').textContent=note;w.title=title||''}
function build(){var f=w.dataset.buildTemp;if(f==='')return put('--','','as of build','No current reading');put(f,w.dataset.buildCond,'as of build','Build-time reading ('+w.dataset.buildAt+'; '+w.dataset.buildSrc+')')}
function get(u){var c=window.AbortController?new AbortController():null,t=setTimeout(function(){c&&c.abort()},9000);
return fetch(u,{cache:'no-store',signal:c?c.signal:undefined,headers:{Accept:'application/geo+json'}}).then(function(r){clearTimeout(t);if(!r.ok)throw new Error('HTTP '+r.status);return r.json()},function(e){clearTimeout(t);throw e})}
function ok(f,c,ts,src){live=true;put(f,c,'updated '+hm.format(ts?new Date(ts):new Date()),src+' via api.weather.gov')}
function load(){w.dataset.state=live?'refreshing':'loading';
get(OBS).then(function(j){var p=j.properties,c=p&&p.temperature&&p.temperature.value;if(c==null)throw new Error('null temp');ok(Math.round(c*9/5+32),p.textDescription,p.timestamp,'KMFE observation');w.dataset.state='observation'})
.catch(function(){return get(HR).then(function(j){var q=j.properties.periods[0],f=q.temperature;if(q.temperatureUnit==='C')f=Math.round(f*9/5+32);ok(f,q.shortForecast,j.properties.updateTime||q.startTime,'NWS hourly forecast');w.dataset.state='hourly'})})
.catch(function(){w.dataset.state=live?'stale':'build';if(!live)build();else $('cw-note').textContent=$('cw-note').textContent.replace(/ \(stale\)$/,'')+' (stale)'})}
build();load();setInterval(load,600000);
var pin=$('pin'),mb=$('minibar');
function hh2(){document.documentElement.style.setProperty('--hh',(pin?pin.offsetHeight:0)+'px')}hh2();addEventListener('resize',hh2);if(window.ResizeObserver&&pin)new ResizeObserver(hh2).observe(pin);
/* pinned bar: mirrors the big clock + countdown, and has its own Show Start */
function mini(){var t=$('cw-time'),n=$('cwnext');if(!mb||!t)return;$('mb-time').textContent=t.textContent.replace(/:\d\d(?= [AP]M)/,'');var x=n?[].map.call(n.children,function(e){return e.style.display==='none'?'':e.textContent}).join(' ').replace(/\s+/g,' ').trim():'';$('mb-next').textContent=x;mb.classList.toggle('amber',!!(n&&/amber/.test(n.className)));mb.classList.toggle('red',!!(n&&/red/.test(n.className)))}
var ms=$('mb-start');if(ms)ms.onclick=function(){var b=$('ssbtn');if(b)b.click()};
mini();setInterval(mini,1000);
})();
"""
STUDIO_JS = r"""
(function(){
var r=document.documentElement,mem={},persist=true;
var store={get:function(k){try{var v=localStorage.getItem(k);return v===null?(mem[k]===undefined?null:mem[k]):v}catch(e){return mem[k]===undefined?null:mem[k]}},
 set:function(k,v){mem[k]=v;try{localStorage.setItem(k,v)}catch(e){persist=false}}};
try{localStorage.setItem('ditm-t','1');localStorage.removeItem('ditm-t')}catch(e){persist=false}
var $=function(i){return document.getElementById(i)};
function toast(m){var e=$('toast');e.textContent=m;e.className='on';clearTimeout(toast.t);toast.t=setTimeout(function(){e.className=''},1600)}
var t=store.get('ditm-theme')||(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');r.setAttribute('data-theme',t);
var sfs=parseFloat(store.get('ditm-fs'));
if(sfs){if(sfs>=17&&!store.get('ditm-fs-v14')){sfs=Math.max(13,sfs-4);store.set('ditm-fs',sfs);store.set('ditm-fs-v14','1')}r.style.setProperty('--fs',sfs+'px')}
function curfs(){return parseFloat(getComputedStyle(r).fontSize)||15}
$('theme').onclick=function(){t=t==='dark'?'light':'dark';r.setAttribute('data-theme',t);store.set('ditm-theme',t)};
$('bigger').onclick=function(){var n=Math.min(24,curfs()+2);r.style.setProperty('--fs',n+'px');store.set('ditm-fs',n)};
$('smaller').onclick=function(){var n=Math.max(13,curfs()-2);r.style.setProperty('--fs',n+'px');store.set('ditm-fs',n)};
/* ---- collapsed by default; this session's open/closed state lives in sessionStorage (a fresh tab starts collapsed) ---- */
var OK='ditm-open-v1',opn={},sm={get:function(k){try{return sessionStorage.getItem(k)}catch(e){return mem['s'+k]===undefined?null:mem['s'+k]}},set:function(k,v){mem['s'+k]=v;try{sessionStorage.setItem(k,v)}catch(e){}}};
try{opn=JSON.parse(sm.get(OK)||'{}')||{}}catch(e){opn={}}
var DET=[].slice.call(document.querySelectorAll('details[id]'));
DET.forEach(function(d){if(opn[d.id])d.open=true});
var lastTap=0;document.addEventListener('click',function(e){if(e.target.closest&&e.target.closest('summary'))lastTap=Date.now()},true);
DET.forEach(function(d){d.addEventListener('toggle',function(){if(window.ditmSearchOpening)return;if(d.open)opn[d.id]=1;else delete opn[d.id];sm.set(OK,JSON.stringify(opn));if(d.open&&Date.now()-lastTap<500&&d.classList.contains('sec')){lastTap=0;setTimeout(function(){d.scrollIntoView({behavior:'smooth',block:'start'})},30)}})});
function setAll(v){[].forEach.call(document.querySelectorAll('details'),function(d){d.open=v})}
$('expand').onclick=function(){setAll(true)};
$('collapse').onclick=function(){setAll(false)};
if(location.hash.length>1){var hh=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(hh){var hp=hh.closest('details.sec');if(hp)hp.open=true;if(hh.tagName==='DETAILS')hh.open=true}}
/* ---- order items by trend score (default) or editorial order ---- */
var SORT=sm.get('ditm-sort')||'when';
function sortAll(){[].forEach.call(document.querySelectorAll('.sortbox'),function(b){var k=[].slice.call(b.children).filter(function(c){return c.dataset.ord!==undefined});
 k.sort(function(a,c){var aw=+(a.dataset.when||0),cw=+(c.dataset.when||0);
  if(SORT==='ord')return a.dataset.ord-c.dataset.ord;
  if(SORT==='score')return (c.dataset.sc-a.dataset.sc)||(cw-aw)||(a.dataset.ord-c.dataset.ord);
  return (cw-aw)||(c.dataset.sc-a.dataset.sc)||(a.dataset.ord-c.dataset.ord)});k.forEach(function(c){b.appendChild(c)})});
 $('sortbtn').textContent='Sort: '+(SORT==='ord'?'Editorial':SORT==='score'?'Score':'Newest')}
$('sortbtn').onclick=function(){SORT=SORT==='when'?'score':SORT==='score'?'ord':'when';sm.set('ditm-sort',SORT);sortAll()};
sortAll();
function copy(u,msg){function fb(){var a=document.createElement('textarea');a.value=u;a.setAttribute('readonly','');a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();try{a.setSelectionRange(0,99999);document.execCommand('copy');toast(msg||'Link copied')}catch(e){toast('Copy failed: long-press the link instead')}a.remove()}
if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(u).then(function(){toast(msg||'Link copied')},fb)}else fb()}
/* ---- used on show ---- */
var KEY='ditm-used-v1',used={};try{used=JSON.parse(store.get(KEY)||'{}')||{}}catch(e){used={}}
var ctd=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'}),ctt=new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',hour:'numeric',minute:'2-digit'});
function today(){return ctd.format(new Date())}
function save(){store.set(KEY,JSON.stringify(used))}
function paint(){var n=0,td=today(),keys=Object.keys(used);
 [].forEach.call(document.querySelectorAll('.use'),function(b){var on=!!used[b.dataset.key];b.setAttribute('aria-pressed',on?'true':'false');
  var box=b.closest('.item,.mbox,.uhead');if(box)box.classList.toggle('used',on)});
 keys.forEach(function(k){if(ctd.format(new Date(used[k].t))===td)n++});
 $('ucount').textContent=n;var uc=$('cnt-used');if(uc)uc.textContent=n+' used';
 var ul=$('usedul');ul.innerHTML='';keys.sort(function(a,b){return used[b].t<used[a].t?-1:1});
 if(!keys.length){var li=document.createElement('li');li.textContent='Nothing marked yet. Tap the box next to an item when it is used on the show.';ul.appendChild(li)}
 keys.forEach(function(k){var u=used[k],li=document.createElement('li');li.appendChild(document.createTextNode(ctd.format(new Date(u.t))+' '+ctt.format(new Date(u.t))+' CT · '));
  if(u.url){var a=document.createElement('a');a.href=u.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=u.title;li.appendChild(a)}else li.appendChild(document.createTextNode(u.title));
  li.appendChild(document.createTextNode(' ('+u.sec+')'));ul.appendChild(li)});
 $('ustatus').textContent=persist?'Saved on this device. Log them to the repo after the show.':'Private mode: marks last only until this tab closes.'}
function lines(todayOnly){var td=today(),o=[];Object.keys(used).forEach(function(k){var u=used[k];if(todayOnly&&ctd.format(new Date(u.t))!==td)return;o.push({key:k,usedAt:u.t,title:u.title,url:u.url||'',section:u.sec})});o.sort(function(a,b){return a.usedAt<b.usedAt?-1:1});return o}
function issueBody(l){var h='Used on show, logged from the studio dashboard.\n\nDate (CT): '+today()+'\nItems: '+l.length+'\n\n';
 l.forEach(function(x){h+='- ['+ctt.format(new Date(x.usedAt))+' CT] '+x.title+' ('+x.section+')'+(x.url?' '+x.url:'')+'\n'});
 return h+'\n```json\n'+JSON.stringify(l)+'\n```\n'}
$('ulog').onclick=function(){var l=lines(true);if(!l.length){toast('Nothing marked used today yet');return}
 var repo=$('usedbar').dataset.repo,body=issueBody(l);if(body.length>6500){l=l.slice(-25);body=issueBody(l)+'\n(truncated to the latest 25)'}
 var u='https://github.com/'+repo+'/issues/new?labels='+encodeURIComponent('used-on-show')+'&title='+encodeURIComponent('Used on show '+today())+'&body='+encodeURIComponent(body);
 var w=window.open(u,'_blank','noopener,noreferrer');if(!w){location.href=u}};
$('ucopy').onclick=function(){var l=lines(false);if(!l.length){toast('Nothing to copy');return}copy(issueBody(l),'Used list copied')};
$('uclear').onclick=function(){if(!Object.keys(used).length)return;if(window.confirm('Clear all used marks on this device?')){used={};save();paint()}};
document.addEventListener('click',function(e){
 var u=e.target.closest('.use');if(u){var k=u.dataset.key;if(used[k])delete used[k];else used[k]={t:new Date().toISOString(),title:u.dataset.title,url:u.dataset.url,sec:u.dataset.sec};save();paint();return}
 var b=e.target.closest('.cp');if(b){e.preventDefault();copy(b.dataset.url);return}
 var ob=e.target.closest('#obmore');if(ob){var pv=document.getElementById('obprev'),sh=pv.hidden;pv.hidden=!sh;ob.setAttribute('aria-expanded',sh?'true':'false');ob.textContent=sh?ob.dataset.less:ob.dataset.more;e.preventDefault();return}
 var c=e.target.closest('[data-jump]');if(c){var d=document.getElementById(c.dataset.jump);if(d){var p=d.closest('details.sec');if(p)p.open=true;if(d.tagName==='DETAILS')d.open=true;d.scrollIntoView({behavior:'smooth',block:'start'})}e.preventDefault()}});
paint();
})();
"""
SEARCH_JS = r"""
(function(){
var qel=document.getElementById('q'), clr=document.getElementById('q-x'), cnt=document.getElementById('q-n');
if(!qel)return;
var list=[], secs=[], savedOpen=null, tmr=0, pending='', raf=0, hlraf=0;
function isParkedSec(d){return d&&(d.id==='aired'||d.id==='expired')}
function cardsNow(){return document.querySelectorAll('.item, .ob, .brkrow')}
function indexOne(el){
  var sec=el.closest('details.sec, #brk');
  var st='';
  if(sec){
    var sum=sec.querySelector(':scope > summary');
    var tn=sum&&sum.querySelector('.tn, .brkh b');
    var sm=sum&&sum.querySelector('.tt small');
    st=((tn&&tn.textContent)||'')+' '+((sm&&sm.textContent)||'');
  }
  el._qhay=((el.getAttribute('data-q')||'')+' '+st).toLowerCase();
  if(!el._qhay.trim()){
    el._qhay=(el.getAttribute('data-q')||'').toLowerCase();
  }
  return {el:el, hay:el._qhay, sec:sec, box:el.querySelector('.tx, .obn, .obm')||el};
}
function indexAll(){
  list=[];
  cardsNow().forEach(function(el){list.push(indexOne(el));});
  secs=[].slice.call(document.querySelectorAll('details.sec, #brk'));
}
function unmark(root){
  root.querySelectorAll('mark.qhit').forEach(function(m){
    var p=m.parentNode; if(!p)return;
    while(m.firstChild)p.insertBefore(m.firstChild,m);
    p.removeChild(m); p.normalize();
  });
}
function mark(root,q){
  if(!q)return;
  var rx; try{rx=new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'ig');}catch(e){return;}
  var tw=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null,false), nodes=[], n;
  while((n=tw.nextNode())){
    if(n.parentNode&&n.parentNode.closest&&n.parentNode.closest('mark.qhit,.acts,button,script,style,input'))continue;
    rx.lastIndex=0; if(n.nodeValue&&rx.test(n.nodeValue))nodes.push(n);
  }
  nodes.forEach(function(n){
    var t=n.nodeValue, frag=document.createDocumentFragment(), last=0, m;
    rx.lastIndex=0;
    while((m=rx.exec(t))){
      if(m.index>last)frag.appendChild(document.createTextNode(t.slice(last,m.index)));
      var mk=document.createElement('mark'); mk.className='qhit'; mk.textContent=m[0]; frag.appendChild(mk);
      last=m.index+m[0].length;
    }
    if(last<t.length)frag.appendChild(document.createTextNode(t.slice(last)));
    n.parentNode.replaceChild(frag,n);
  });
}
function snapshotOpen(){
  if(savedOpen)return;
  savedOpen={};
  secs.forEach(function(d){if(d.id)savedOpen[d.id]=!!d.open;});
}
function restoreOpen(){
  if(!savedOpen)return;
  window.ditmSearchOpening=true;
  secs.forEach(function(d){if(d.id&&Object.prototype.hasOwnProperty.call(savedOpen,d.id)&&d.open!==savedOpen[d.id])d.open=savedOpen[d.id];});
  window.ditmSearchOpening=false;
  savedOpen=null;
}
function applySearch(qraw){
  var raw=(qraw!==undefined?qraw:(qel.value||'')).trim(), q=raw.toLowerCase();
  if(clr)clr.hidden=!raw;
  if(!list.length)indexAll();
  if(!q){
    list.forEach(function(c){
      unmark(c.el);
      if(c.el.classList.contains('rm-hide'))c.el.hidden=true;
      else c.el.hidden=false;
    });
    secs.forEach(function(d){
      d.classList.remove('q-empty');
      var nav=d.id&&document.querySelector('nav a[href="#'+d.id+'"]');
      if(nav)nav.classList.remove('q-empty');
    });
    restoreOpen();
    if(cnt)cnt.textContent='';
    return;
  }
  snapshotOpen();
  var hit=0;
  list.forEach(function(c){
    unmark(c.el);
    if(c.el.classList.contains('rm-hide')){c.el.hidden=true;c._ok=false;return;}
    var parked=isParkedSec(c.sec);
    if(parked&&c.sec&&!c.sec.open){c.el.hidden=true;c._ok=false;return;}
    var hay=c.hay||c.el._qhay||(c.el.getAttribute('data-q')||'').toLowerCase();
    var ok=hay.indexOf(q)!==-1;
    c.el.hidden=!ok;
    c._ok=ok;
    if(ok)hit++;
  });
  window.ditmSearchOpening=true;
  secs.forEach(function(d){
    var n=0;
    list.forEach(function(c){if(c.sec===d&&c._ok)n++;});
    var empty=n===0;
    d.classList.toggle('q-empty',empty);
    if(n&&!isParkedSec(d)&&!d.open)d.open=true;
    var nav=d.id&&document.querySelector('nav a[href="#'+d.id+'"]');
    if(nav)nav.classList.toggle('q-empty',empty);
  });
  window.ditmSearchOpening=false;
  if(cnt)cnt.textContent=hit?(hit+' match'+(hit===1?'':'es')):'No matches';
  if(hlraf)cancelAnimationFrame(hlraf);
  hlraf=requestAnimationFrame(function(){
    hlraf=0;
    list.forEach(function(c){if(c._ok&&!c.el.hidden)mark(c.box||c.el,raw);});
  });
}
function schedule(){
  pending=qel.value||'';
  if(tmr)clearTimeout(tmr);
  if(!pending.trim()){if(raf)cancelAnimationFrame(raf);applySearch('');return;}
  tmr=setTimeout(function(){
    tmr=0;
    if(raf)cancelAnimationFrame(raf);
    raf=requestAnimationFrame(function(){raf=0;applySearch(pending);});
  },120);
}
indexAll();
qel.addEventListener('input',schedule);
qel.addEventListener('search',schedule);
if(clr)clr.addEventListener('click',function(){qel.value='';applySearch('');qel.focus();});
document.addEventListener('keydown',function(e){
  if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!e.altKey){
    var t=e.target; if(t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.isContentEditable||(t.closest&&t.closest('dialog'))))return;
    e.preventDefault(); qel.focus(); qel.select(); return;
  }
  if(e.key==='Escape'&&(document.activeElement===qel||(qel.value||'').trim())){
    if((qel.value||'').trim()){e.preventDefault(); qel.value=''; applySearch(''); qel.focus();}
    else {qel.blur();}
  }
});
if(window.MutationObserver){
  var brk=document.getElementById('brklist'), busy=false;
  if(brk){
    var obs=new MutationObserver(function(){
      if(busy)return;
      busy=true;
      requestAnimationFrame(function(){
        indexAll();
        if((qel.value||'').trim())applySearch();
        busy=false;
      });
    });
    obs.observe(brk,{childList:true,subtree:false});
  }
}
window.ditmSearch=function(){applySearch();};
window.ditmSearchIndex=indexAll;
})();
"""
STUDIO_CSS2 = """
.sec>summary{min-height:48px}
.sec>summary .st{display:flex;align-items:center;gap:8px;min-width:0;flex:1 1 300px}
.sec>summary .tt{display:block;min-width:0}.sec>summary .tt small{display:block;margin-top:1px}
.bl2{display:inline-flex;align-items:center;justify-content:center;min-width:2rem;height:2rem;padding:0 6px;border-radius:8px;background:rgba(0,0,0,.28);color:#fff;font-weight:900;font-size:1.05rem;letter-spacing:0;flex:none}
.sm{display:flex;gap:6px;align-items:center;justify-content:flex-end;flex-wrap:wrap;margin-left:auto;text-transform:none;letter-spacing:0}
.sm .cnt,.rbd .cnt{background:rgba(255,255,255,.24);border-radius:99px;padding:0 9px;font-size:.74rem;font-weight:800;white-space:nowrap;line-height:1.55}
.rbd{display:flex;gap:5px;flex-wrap:wrap;margin-top:3px}
.sb{display:inline-block;font-size:.66rem;font-weight:900;letter-spacing:.04em;line-height:1.55;padding:0 6px;border-radius:5px;color:#fff;text-transform:uppercase;white-space:nowrap;vertical-align:1px;margin-left:4px}
.sb.h{background:#c1121f}.sb.t{background:#e4572e}.sb.a{background:#6b7785}.sb.u{background:#6f42c1}
summary .sb,summary .cf{border:1px solid rgba(255,255,255,.75)}
.sortbox{display:block}
#brk{margin:8px max(16px,var(--sr)) 0 max(16px,var(--sl));border:2px solid var(--line);border-radius:12px;background:var(--card);padding:6px 12px}
.brkh{display:flex;align-items:center;gap:8px 12px;flex-wrap:wrap;min-height:44px}.brkh b{font-weight:900}
#brkcount{background:var(--chip);min-width:2em;text-align:center;font-size:.8rem}#brkcount.new{background:#c1121f;color:#fff;border-color:#c1121f}#brkcount.warn{background:#f2a900;color:#1b2430;border-color:#b87c00}
#brkmeta{flex:1 1 160px;font-size:.8rem;font-weight:600}
.brkrow{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;padding:6px 0;border-top:1px dashed var(--line)}.brkrow a{font-weight:700;flex:1 1 220px;min-width:0}
.brkrow .src{white-space:nowrap}.brkrow.old{opacity:.78}.brkrow .chysend{margin-left:auto;flex:none}
.brkrow .nw{background:#c1121f;color:#fff;font-size:.66rem;font-weight:900;border-radius:4px;padding:0 5px}
#brkbadge b{display:inline-block;min-width:1.6em;text-align:center;background:var(--ok);color:#fff;border-radius:99px;padding:0 6px;margin-left:6px}#brkbadge.hot b{background:#c1121f}
.brkmore{margin:4px 0}
.coact{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 0}
.cotext{font-size:clamp(1.2rem,1.5vw + .9rem,1.85rem);line-height:1.5;font-weight:600;margin:0 0 8px}
.jingle{background:var(--chip);border-left:6px solid #f2b705;border-radius:8px;padding:8px 12px;margin:8px 0;font-weight:800;font-size:1.05rem}
.jingle small{display:block;font-weight:600;color:var(--mut);font-size:.8rem;margin-top:3px}
.pill{display:inline-block;background:var(--chip);border:1px solid var(--line);border-radius:99px;padding:0 8px;font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
.pill.drew{background:#e4572e;color:#fff;border-color:#e4572e}.pill.jess{background:#8e6bbf;color:#fff;border-color:#8e6bbf}
.noev{background:var(--chip);border:2px dashed var(--mut);border-radius:10px;padding:8px 12px;font-weight:800}
.trn .tx>b{font-size:1.02em}.trn p{margin:3px 0}
.trn .ang{color:var(--fg)}.trn .ang b{color:var(--acc)}
.ss{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:4px 0 0}
.ss button{min-height:44px;min-width:44px;white-space:nowrap}
#chy{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0}.chlink[hidden],#mb-hold[hidden]{display:none}
#chy .chl{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}#chy button,.chlink{min-height:44px;min-width:44px;white-space:nowrap}
#chst{font-size:.8rem;font-weight:700;color:var(--mut);white-space:nowrap}.chlink{margin-top:4px;font-size:.8rem}
#ssbtn{background:var(--ok);color:#fff;border-color:var(--ok);padding:4px 16px;font-weight:900}
#ssreset:disabled{opacity:.45;cursor:default}
#ssind{display:inline-block;min-width:11.2em;font-weight:800;font-variant-numeric:tabular-nums;white-space:nowrap}
#sslive{display:block;width:100%;min-height:1.3em;font-weight:800;font-size:.85rem;color:var(--ok);font-variant-numeric:tabular-nums}
.rd>summary{display:grid;grid-template-columns:minmax(0,1fr) var(--trw,7.6rem) 1.2rem;align-items:center;gap:4px 10px}
.rd>summary:after{margin:0;padding:0;text-align:right}
.rd>summary .rt{min-width:0}
.rd .tt{display:block;min-width:0}.rd .tt small{display:block;margin-top:1px}
.tr{display:block;text-align:right;font-variant-numeric:tabular-nums;font-weight:900;white-space:nowrap;text-transform:none;letter-spacing:0;font-size:1.02rem;line-height:1.15}
.tr small{display:block;min-height:1.1em;font-size:.7rem;font-weight:700;opacity:.95;text-transform:none}
.rd.live,.sec.live{box-shadow:0 0 0 4px var(--ok);position:relative}
.rd.live>summary .tl,.sec.live>summary .tl{display:inline-block;background:#fff;color:#1f9d55;font-size:.68rem;font-weight:900;border-radius:4px;padding:0 5px;margin-left:6px}
.tl{display:none}
.cwn{display:flex;gap:6px;justify-content:flex-end;align-items:center;margin-top:4px;padding:2px 8px;border-radius:99px;min-height:1.9em;font-size:clamp(.78rem,.6vw + .52rem,.95rem);font-weight:800;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;border:2px solid transparent}
.cwn #cwn-l{color:var(--mut)}.cwn #cwn-c{color:#fff;font-style:normal;font-weight:900;border-radius:6px;padding:0 7px;min-width:1.6em;text-align:center}
.cwn #cwn-n{min-width:0;overflow:hidden;text-overflow:ellipsis}.cwn #cwn-t{font-weight:900}
.cwn.amber{background:#f2a900;color:#1b2430;border-color:#b87c00}.cwn.amber #cwn-l{color:#1b2430}
.cwn.red{background:#c1121f;color:#fff;border-color:#7d0b14}.cwn.red #cwn-l{color:#fff}
@media (max-width:820px){.cwn{justify-content:flex-start}}
.weave{background:var(--chip);border-radius:8px;padding:4px 8px;font-weight:700;font-size:.9rem}
@media (max-width:560px){.rd>summary{--trw:6.6rem}.tr{font-size:.95rem}}

/* ---- layout v6: uniform collapsed tiles, full-width multi-column expanded sections, native phone scrolling ---- */
#pin{position:sticky;top:0;z-index:20;background:#0b1017;border-bottom:1px solid #2a3340;padding-bottom:0;color:#f4f6f8}
#mc{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;padding:max(4px,var(--st)) max(8px,var(--sr)) 6px max(10px,var(--sl));background:#0b1017;color:#f4f6f8}
#find{display:flex;align-items:center;gap:6px;padding:0 max(10px,var(--sr)) 6px max(10px,var(--sl));background:#0b1017;color:#f4f6f8}
#find label.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
#q{flex:1 1 auto;min-width:0;min-height:44px;height:44px;padding:0 12px;border:1px solid #3a4554;border-radius:8px;background:#151c26;color:#f4f6f8;font:inherit;font-size:16px;-webkit-appearance:none;appearance:none}
#q::placeholder{color:#8b97a6}
#q:focus{outline:2px solid #3d8bfd;outline-offset:1px;border-color:#3d8bfd}
#q-x{min-height:44px;min-width:44px;padding:0 14px;border-radius:10px;border:1px solid #3a4554;background:#1c2430;color:#f4f6f8;font-weight:800;cursor:pointer;font:inherit}
#q-x[hidden]{display:none}
#q-n{flex:none;color:#9aa6b5;font-size:.85rem;font-weight:700;white-space:nowrap}
mark.qhit{background:#ffe08a;color:#1b2430;padding:0 .12em;border-radius:2px}
.sec.q-empty,#brk.q-empty{display:none}
nav a.q-empty{display:none}
.item[hidden],.ob[hidden],.brkrow[hidden]{display:none!important}
.mc-id{display:flex;align-items:center;gap:8px;flex:0 0 auto;min-width:0}
.mc-id img{height:36px;width:auto;max-width:28vw;background:#fff;border-radius:8px;padding:2px 6px;flex:none}
.mc-brand{display:flex;flex-direction:column;line-height:1.15;min-width:0}
.mc-brand b{font-size:.68rem;letter-spacing:.14em;font-weight:900}
.mc-brand span{font-size:.72rem;color:#9fb0c2;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:28vw}
.mc-status{display:flex;align-items:center;gap:8px 10px;flex:1 1 220px;min-width:0;flex-wrap:wrap;font-variant-numeric:tabular-nums;font-weight:800}
#minibar b#mb-time{font-size:1.15rem;white-space:nowrap;color:#fff}
#minibar span{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.8rem;color:#9fb0c2;font-weight:700}
#sslive{display:inline;width:auto;min-height:0;color:#7CFFB2;font-size:.8rem}
#ssind{display:inline;min-width:0;color:#9fb0c2;font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#chst{color:#c5d0da;font-size:.78rem;font-weight:700}
.mcp{display:inline-flex;align-items:center;justify-content:center;min-height:28px;padding:0 10px;border-radius:99px;font-size:.68rem;font-weight:900;letter-spacing:.1em;border:1px solid transparent}
.mcp.stand{background:#1a222d;color:#c5d0da;border-color:#3a4656}
.mcp.live{background:#c1121f;color:#fff}
.mcp.onair{background:#0b5cad;color:#fff}
.mcp.held{background:#f2a900;color:#1b2430}
#minibar.amber #mb-next,#minibar.amber #sslive{color:#f2a900}
#minibar.red #mb-next,#minibar.red #sslive{color:#ff6b6b}
#chy.mc-ops,#chy{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0;flex:1 1 auto}
.mc-ops button,.mc-ops .chlink,details#mc-more>summary{appearance:none;-webkit-appearance:none;flex:none;display:inline-flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;padding:0 11px;border-radius:8px;font-size:.72rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;border:1px solid #3a4656;background:#1a222d;color:#f4f6f8}
.mc-ops button:hover,details#mc-more>summary:hover{background:#2a3340;color:#fff;border-color:#5a6b7d}
#ssbtn{background:#1f9d55;color:#fff;border-color:#1f9d55;font-weight:900;padding:0 14px}
#ssstop,#stop-go{background:#b42318;color:#fff;border-color:#b42318;font-weight:900;padding:0 14px}
#ssstop:hover,#stop-go:hover{background:#9b1c1c;border-color:#9b1c1c;color:#fff}
#chhold.held{background:#f2a900;color:#1b2430;border-color:#f2a900}
#stop-go,#stop-no{min-height:44px;min-width:44px;padding:0 14px;border-radius:8px;font:inherit;font-weight:800;letter-spacing:.04em;text-transform:uppercase;cursor:pointer}
#stop-no{background:#1a222d;color:#f4f6f8;border:1px solid #3a4656}
#mc-guest{background:#0b5cad;border-color:#0b5cad;color:#fff}
#mc-caller{background:#c8102e;border-color:#c8102e;color:#fff}
#mc-logo{background:#2a3340;color:#fff}
details#mc-more{position:relative;flex:none;z-index:40;overflow:visible;background:transparent;border:none;min-width:0}
details#mc-more>summary{list-style:none;cursor:pointer;min-width:44px}
details#mc-more>summary::-webkit-details-marker{display:none}
.mc-more-p{position:absolute;right:0;top:calc(100% + 6px);z-index:30;min-width:min(340px,92vw);max-width:92vw;background:#141b24;border:1px solid #3a4656;border-radius:12px;padding:10px;box-shadow:0 12px 40px rgba(0,0,0,.45);display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.mc-more-p button,.mc-more-p .btnlike,.mc-more-p a{min-height:44px;min-width:44px}
#clockw{margin:6px 0 0;text-align:left;background:#0b1017;border:1px solid #3a4656;color:#f4f6f8;width:100%;min-width:0;max-width:100%}
#clockw #cw-time{font-size:1.4rem;color:#fff}
header.ident{background:var(--bg);border-bottom:1px solid var(--line);padding:6px max(16px,var(--sr)) 6px max(16px,var(--sl));display:block}
header.ident .k{font-size:.7rem;letter-spacing:.12em;font-weight:800;color:#b5651d;text-transform:uppercase}
header.ident .t{font-size:.85rem;color:var(--mut);font-weight:600}
.toolbar{display:none}
dialog.dlg{border:0;border-radius:16px;padding:0;width:min(520px,calc(100vw - 24px));max-height:calc(100vh - 24px);background:var(--card);color:var(--fg);box-shadow:0 20px 60px rgba(0,0,0,.4)}
dialog.dlg::backdrop{background:rgba(8,10,16,.65)}
.dlg-h{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:14px 16px 8px;font-weight:900}
.dlg-h h3{margin:0;font-size:1.05rem;letter-spacing:.04em;text-transform:uppercase}
.dlg-b{padding:8px 16px 16px;display:flex;flex-direction:column;gap:10px}
.dlg-b label{display:flex;flex-direction:column;gap:4px;font-weight:700;font-size:.8rem}
.dlg-b input[type=text],.dlg-b input[type=url]{min-height:44px;border:2px solid var(--line);border-radius:10px;padding:0 10px;font:inherit;background:var(--bg);color:var(--fg);width:100%;box-sizing:border-box}
.dlg-a{display:flex;flex-wrap:wrap;gap:8px}
.dlg-x{border:0;background:transparent;color:var(--mut);font-size:1.4rem;min-width:44px}
#c-prev{max-width:120px;max-height:120px;border-radius:8px;object-fit:cover}
.gp{display:contents}
#link-dlg p{margin:0 0 8px;line-height:1.45}
#link-dlg code{font-weight:800}
@media (max-width:900px){.mc-brand span,#ssind,#chst{max-width:100%}}
#mb-hold.held,#chhold.held{background:#f2a900;color:#1b2430;border-color:#f2a900}
.toolbar{display:flex;gap:6px 14px;align-items:center;flex-wrap:wrap;padding:6px max(16px,var(--sr)) 0 max(16px,var(--sl))}
.toolbar .t{font-size:.82rem;color:var(--mut);font-weight:600;flex:1 1 260px;min-width:0}
.toolbar .tools{margin:0;flex:0 1 auto}
.ht .d{font-size:clamp(1.25rem,1.8vw + .6rem,1.9rem)}
.ht{flex:1 1 280px}
@media (min-width:1000px){
 header{flex-wrap:nowrap}
 #clockw{flex:0 0 auto}
 .ss{margin:2px 0 0}
}
@media (max-width:999px){
 #clockw{margin-left:0;width:100%;min-width:0;text-align:left;display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:12px;align-items:center}
 #cw-time{grid-row:1/3;font-size:clamp(1.5rem,6vw,2rem)}.cwd{text-align:right}.cwx{justify-content:flex-end;margin-top:0}.cwn{grid-column:1/-1}
 .ss{flex-wrap:wrap}
}
@media (max-width:560px){
 header{padding-top:8px;gap:8px}
 header>img{height:40px}
 .ht{flex:1 1 150px}.ht .k{letter-spacing:.08em}
 #ssind{min-width:0;white-space:normal;flex:1 1 140px;font-size:.85rem}
 .toolbar{padding-top:4px}.toolbar .t{display:none}
 .toolbar .tools{width:100%;flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;overscroll-behavior-x:contain}.toolbar .tools::-webkit-scrollbar{display:none}.toolbar .tools>*{flex:none}
 #ustatus{display:none}#usedbar{padding-top:4px;padding-bottom:4px}
 #brkmeta{flex:1 1 0;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}#brk{padding:2px 12px}
 nav{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;overscroll-behavior-x:contain}
 nav::-webkit-scrollbar{display:none}
 nav a{flex:none}
 #usedbar .ubb{margin-left:0;width:100%}#usedbar .ubb>*{flex:1 1 auto}
 #brk .brkh button{flex:none}
 #toast{max-width:calc(100vw - 24px)}
}
/* A-L show timeline: pinned, always fits the width (no swiping), playhead + covered blocks darken */
.clock a{flex:0 0 auto;min-width:0;overflow:hidden;transition:filter .8s}
.clock a.done{filter:brightness(.6) saturate(.85)}
.clock a.live{outline:3px solid #fff;outline-offset:-3px;filter:none}
#phw{position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:2}
#ph{position:absolute;top:0;bottom:0;left:0;width:0;pointer-events:none;z-index:2;transition:left 1s linear,opacity .4s}
#ph:before{content:'';position:absolute;top:0;bottom:0;left:-1px;width:3px;background:#fff;box-shadow:0 0 0 1px #1b2430,0 0 6px rgba(0,0,0,.5)}
#ph:after{content:'';position:absolute;top:0;left:-8px;border-left:8px solid transparent;border-right:8px solid transparent;border-top:11px solid #fff;filter:drop-shadow(0 0 1px #1b2430) drop-shadow(0 0 1px #1b2430)}
.clock.pre #ph{opacity:.55}
@media (max-width:700px){.clock a small{display:none}.clock{height:28px}.clock a{font-size:.72rem}#minibar b{font-size:1.1rem}#minibar span{font-size:.78rem}#minibar a{display:none}}
/* uniform collapsed tiles: same box for every section, whatever its content */
details.sec{align-self:stretch}
details.sec[open]{grid-column:1/-1}
.sec>summary{position:relative;display:grid;grid-template-columns:auto minmax(0,1fr) auto;grid-template-rows:auto auto;align-items:center;gap:0;height:var(--sumh,3.4rem);min-height:var(--sumh,3.4rem);padding:4px 10px;overflow:hidden;flex-wrap:nowrap;letter-spacing:.03em}
.sec>summary .st,.sec>summary .tt{display:contents}
.sec>summary .bl2{grid-column:1;grid-row:1/3;margin:0;min-width:2.2rem;height:2.2rem}
.sec>summary .tn{grid-column:2/4;grid-row:1;margin-left:10px;padding-right:1.6rem;font-size:clamp(.9rem,.5vw + .78rem,1.08rem);line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;align-self:end}
.sec>summary .tt small{grid-column:2;grid-row:2;margin:0 0 0 10px;display:block;font-size:.76rem;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;align-self:start}
.sec>summary:after{position:absolute;right:12px;top:7px;margin:0;padding:0;line-height:1}
.sec>summary .sm{grid-column:3;grid-row:2;margin:0 0 0 10px;flex-wrap:nowrap;white-space:nowrap;max-width:15rem;overflow:hidden;align-self:start;gap:4px;justify-content:flex-start}
.sec>summary .sm .sb,.sec>summary .sm .cf,.sec>summary .sm .cnt{margin:0;white-space:nowrap;flex:none}
.sec>summary .sm .cnt{flex:none}
/* wide screens: every section is one full-width bar; title, subtitle and badges all fit on the bar, nothing truncates */
@media (min-width:700px){
 .sec>summary{grid-template-columns:auto minmax(0,1fr) auto 1.6rem;padding:4px 12px}
 .sec>summary .tn{grid-column:2;padding-right:14px;overflow:visible;text-overflow:clip}
 .sec>summary .tt small{grid-column:2;overflow:visible;text-overflow:clip;font-size:.84rem;padding-right:14px}
 .sec>summary .sm{grid-column:3;grid-row:1/3;align-self:center;max-width:none;overflow:visible;margin:0 8px 0 0;gap:6px}
 .sec>summary:after{position:static;grid-column:4;grid-row:1/3;align-self:center;text-align:right;font-size:1.3em}
 .sec>summary .tn,.sec>summary .tt small{white-space:normal}
}
@media (max-width:560px){.sec>summary .tn{font-size:.84rem;letter-spacing:0}.sec>summary .sm{max-width:8.5rem}.sec>summary .sm .sb:nth-child(n+3){display:none}}
.sec>.body{padding:8px clamp(8px,1.2vw,12px) 10px}
/* expanded sections fill the row; even-height story cards in a responsive grid */
.sec .sortbox{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,320px),1fr));gap:8px;align-items:stretch}
.sec .sortbox>.item{border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--bg);display:flex;flex-direction:column;align-items:stretch;gap:5px;min-width:0;min-height:100%;overflow:hidden;box-sizing:border-box;content-visibility:auto;contain-intrinsic-size:auto 240px}
.sec .sortbox>.item[data-rmid]{position:relative;padding-top:8px;padding-right:48px}
.rmx{position:absolute;top:2px;right:2px;min-width:44px;min-height:44px;padding:0;border:0;border-radius:8px;background:transparent;color:#c8102e;font-size:22px;font-weight:900;line-height:1;cursor:pointer;z-index:2;font-family:inherit}
.rmx:hover,.rmx:focus-visible{background:#c8102e;color:#fff;outline:none}
.item.rm-hide{display:none!important}
body.show-rm .item.rm-gone{opacity:.6;outline:1px dashed var(--line)}
.dtg{display:inline-block;font-size:.72rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase;color:var(--mut);border:1px solid var(--line);border-radius:999px;padding:0 7px;line-height:1.7;white-space:nowrap}
#toast.rmtoast{pointer-events:auto}
#toast .undobtn{margin-left:8px;min-height:44px;min-width:44px;padding:0 12px;border:0;border-radius:999px;background:#fff;color:#1b2430;font:inherit;font-weight:800;cursor:pointer}
.sec .sortbox>.item>.tx{min-width:0;overflow:hidden;display:flex;flex-direction:column;gap:4px;flex:1 1 auto}
.sec .sortbox>.item>.acts{margin-top:auto;justify-content:flex-end;flex-wrap:wrap;gap:6px;flex:none}
.sec .sortbox>.item>.acts button{flex:none;max-width:100%}
.sec .sortbox>.item:last-child{border:1px solid var(--line)}
.sec .sortbox>.item.used{background:rgba(31,157,85,.14)}
.sec .sortbox>.item.aired,.sec .sortbox>.item.expired{opacity:.78}
.apill,.xpill{display:none;font-size:.68rem;font-weight:900;border-radius:4px;padding:0 5px;margin-left:4px;color:#fff;letter-spacing:.04em}
.item.aired .apill,.aired>.tx .apill{display:inline-block;background:#1f9d55}
.item.expired .xpill,.expired>.tx .xpill{display:inline-block;background:#5c6b7a}
.ob{content-visibility:auto;contain-intrinsic-size:auto 88px}
.sec .sortbox>.noev{grid-column:1/-1}
/* nested story rows (National Desk): full-width rows like the rundown blocks, never side-by-side tiles */
.sec .sortbox>details.rd{margin:0}
.sec .sortbox>details.rd>summary{display:flex;flex-wrap:wrap;align-items:center;gap:4px 12px;min-height:60px;padding:8px 12px}
.sec .sortbox>details.rd>summary .rt{flex:1 1 16rem;min-width:0}
.sec .sortbox>details.rd>summary .tt{display:block;font-size:.98rem;line-height:1.25;letter-spacing:.02em}
.sec .sortbox>details.rd>summary .sm{margin:0 0 0 auto;justify-content:flex-end;flex:0 0 auto}
.sec .sortbox>details.rd>summary .src{color:rgba(255,255,255,.88)}
.sec .sortbox>details.rd>summary:after{margin:0}
/* no mid-word breaks in titles, badges or bars; badges never wrap */
summary,summary *,.rtn,.tn,.tt,h3,h4{overflow-wrap:normal;word-break:normal;hyphens:none}
.cf,.sb,.cnt,.pill,.tag,.upill,.ub,.cwn,.tr,.tr *,.bl,.bl2{white-space:nowrap}
.rd>summary .rtn{display:block}
.rd .rmeta .cnt,.rd .rmeta .cf{font-size:.68rem;padding-left:7px;padding-right:7px}.rd .rmeta{font-size:.85rem}
@media (max-width:1100px){.rdgrid>details.rd>summary{--trw:6.4rem}}
.sec .sortbox>details.rd:not([open])>summary .rtn{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;white-space:normal}
.rd .rmeta{display:flex;align-items:center;flex-wrap:wrap;gap:3px 8px;margin-top:2px}.rd .rmeta small{display:inline;margin:0}.rd .rmeta .rbd{margin:0}
.rd>summary .tl{margin-left:8px}
.rdgrid>details.rd{width:100%;display:block}
@media (min-width:700px){.rd>summary .rtn{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.rdgrid>details.rd>summary{min-height:60px}}
@media (max-width:560px){
 .rdgrid>details.rd>summary{grid-template-columns:minmax(0,1fr) 1.2rem;gap:2px 8px}
 .rdgrid>details.rd>summary .tr{grid-column:1/-1;grid-row:2;display:flex;gap:10px;align-items:baseline;text-align:left;font-size:.9rem}
 .rdgrid>details.rd>summary .tr small{display:inline;min-height:0}
 .rd .bl{width:2.1rem;height:2.1rem;font-size:1.3rem;margin-right:8px}
}
.thumbrow{display:flex;gap:12px;align-items:center;margin:0 0 10px}.thumbrow img{width:140px;max-width:35%;border-radius:8px;flex:none}
.lvgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:4px 18px;align-items:start}
.obl{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:0 22px}
.rd[open] .body{columns:2 340px;column-gap:26px}
.rd h4{break-after:avoid;break-inside:avoid}.rd .body>.item,.rd .body>.chy{break-inside:avoid}
.cotext,#uptotext{max-width:75ch}
/* ---- v3: every section opens into Trending-model cards; block bars; compact obituaries; chisme ---- */
.sec>summary .sm .tr{flex:none;min-width:6.4rem;margin:0 0 0 4px;color:#fff;font-size:.95rem}
.sec>summary .sm .tr small{min-height:0;font-size:.68rem;white-space:nowrap}
.sec .sortbox>.item.trn{gap:4px}
.sec .sortbox .ang{margin:0;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;line-height:1.25;max-width:100%}
.sec .sortbox .tldr{margin:0;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:12;overflow:hidden;line-height:1.35;max-width:100%;overflow-wrap:anywhere}
.sec .sortbox .item.tldr-open .tldr{display:block;-webkit-line-clamp:unset;overflow:visible}
.tldr-exp{align-self:flex-start;margin:0;min-height:44px;min-width:44px;padding:0 10px;border:0;border-radius:8px;background:transparent;color:var(--acc,#2a7de1);font:inherit;font-size:.82rem;font-weight:800;cursor:pointer}
.tldr-exp:hover,.tldr-exp:focus-visible{text-decoration:underline;outline:none}
#showdone{background:#1f9d55;color:#fff;border-color:#167a40}
#aired,#expired{scroll-margin-top:16rem}
body.show-post #pin,body.show-post header.ident,body.show-post #usedbar,body.show-post #brk,body.show-post nav,body.show-post main,body.show-post footer,body.show-post #toast{display:none!important}
#post-show{display:none;max-width:52rem;margin:0 auto;padding:16px max(16px,var(--sl)) 48px;background:var(--bg);color:var(--fg)}
body.show-post #post-show{display:block}
#post-show .ps-top{display:block;border:0;background:transparent;padding:0;position:static}
#post-show .ps-k{margin:0 0 .2rem;font-size:.75rem;letter-spacing:.12em;font-weight:800;color:#b5651d;text-transform:uppercase}
#post-show .ps-top h1{margin:.15rem 0 .2rem;font-size:clamp(1.6rem,3vw + 1rem,2.2rem);line-height:1.15;letter-spacing:-.02em}
#post-show .ps-date{font-weight:800;font-size:1.15rem;margin:0 0 .6rem}
#post-show .ps-top .mut{max-width:42rem}
.ps-acts{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 20px}
.ps-acts button{min-height:44px;padding:0 14px;border-radius:8px;font:inherit;font-weight:800;cursor:pointer}
.ps-story{border:1.5px solid var(--line);border-radius:10px;padding:10px 12px;margin:0 0 12px;background:var(--card)}
.ps-story h3{margin:0 0 4px;font-size:1.05rem}.ps-meta{margin:0 0 6px;color:var(--mut)}
.ps-syn{margin:0 0 8px;line-height:1.4}.ps-d{margin:0 0 10px}.ps-d pre{white-space:pre-wrap;margin:6px 0 0;padding:8px;border-radius:8px;background:var(--bg);border:1px solid var(--line);font:inherit}
.ps-dl{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.ps-copy{min-height:44px;min-width:44px;padding:0 12px;font:inherit;font-weight:800;cursor:pointer}
.item:not(.aired):not(.expired) .sd-restore{display:none}.item.aired .sd-restore,.item.expired .sd-restore{display:inline-flex}.sd-restore{min-height:44px;min-width:44px;padding:0 10px;font:inherit;font-weight:800;cursor:pointer}
@media print{body.show-post #pin,body.show-post nav{display:none!important}#post-show{display:block!important;max-width:none} .ps-acts,.ps-copy,.sd-restore{display:none!important}}

.sec .sortbox .tc .wico{margin-top:4px;flex:none}
.sec .sortbox>.noev{grid-column:1/-1;margin:2px 0}
.sec .item.trn .pill{margin-right:4px}
.sec .item.trn .tx{min-width:0}
.sec .item.trn .tx>b.hd,.sec .item.trn .tx>b.hd a{display:block;overflow:visible;overflow-wrap:anywhere;word-break:break-word;white-space:normal;font-size:1em;line-height:1.28;margin:0}
.sec .item.trn .tx .meta{display:flex;flex-wrap:wrap;align-items:center;gap:2px 6px;min-width:0;color:var(--mut);font-size:.82rem;font-weight:600}
.sec .item.trn .tx .meta .src{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}
.sec .item.trn .tx .ang ul,.sec .item.trn .tx .ang ol{margin:2px 0 0;padding-left:18px}
.obgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,15rem),1fr));gap:6px;margin:4px 0 8px;align-items:stretch}
.ob{border:1px solid var(--line);border-radius:8px;background:var(--bg);padding:6px 8px;display:flex;flex-direction:column;gap:2px;min-width:0;overflow:hidden;box-sizing:border-box}
.ob a{font-weight:800;overflow-wrap:anywhere;word-break:break-word}.ob .obn{min-width:0;display:block}.ob .obm{color:var(--mut);font-size:.82rem}.ob .acts{margin-top:auto;justify-content:flex-end}
.subh{margin:12px 0 6px;font-size:.8rem;letter-spacing:.04em;text-transform:uppercase;font-weight:800;color:var(--mut)}.subsec + .subh,.sortbox + .subh,.obgrid + .subh,.mut + .subh{margin-top:14px}
.obmore{display:block;width:100%;min-height:48px;margin:6px 0 10px;padding:10px 14px;border:2px dashed var(--line);border-radius:10px;background:var(--card);color:var(--fg);font-weight:800;font-size:.95rem;font-family:inherit;cursor:pointer}
.obmore:hover,.obmore:focus-visible{border-color:var(--acc);outline:none}
.obprev[hidden]{display:none}
.obh{margin:10px 0 2px;font-size:.95rem}
.tc.chisme{border-left:4px solid #b5179e}
.tc .cf{white-space:nowrap}
@media (max-width:560px){.sec>summary .sm:has(.cf) .cnt{display:none}.sec>summary .sm{max-width:11rem}.sec>summary .sm .sb{display:none}#obits>summary .sm{max-width:13.5rem}.sec>summary .sm .tr{min-width:0;font-size:.8rem;margin:0}.sec>summary .sm .tr small{display:none}}
"""

SHOWDONE_JS = r"""
(function(){
var AK='ditm-aired-v1', EK='ditm-expired-v1', $=function(i){return document.getElementById(i)}, mem={};
var store={get:function(k){try{var v=localStorage.getItem(k);return v===null?(mem[k]===undefined?null:mem[k]):v}catch(e){return mem[k]===undefined?null:mem[k]}},
 set:function(k,v){mem[k]=v;try{localStorage.setItem(k,v)}catch(e){}}};
var aired={}, expired={};
try{aired=JSON.parse(store.get(AK)||'{}')||{}}catch(e){aired={}}
try{expired=JSON.parse(store.get(EK)||'{}')||{}}catch(e){expired={}}
function save(){store.set(AK,JSON.stringify(aired));store.set(EK,JSON.stringify(expired))}
function sendCmd(cmd,id){if(window.ditmChy&&window.ditmChy.send)window.ditmChy.send(cmd,undefined,id)}
function newsCards(){return [].slice.call(document.querySelectorAll('.item[data-rmid]'))}
function rememberHome(el){
  if(el._home)return;
  el._home={parent:el.parentNode, next:el.nextSibling};
}
function unpark(el){
  var h=el._home; if(!h||!h.parent)return;
  if(h.next&&h.next.parentNode===h.parent)h.parent.insertBefore(el,h.next);
  else h.parent.appendChild(el);
}
function toastUndo(html){
  var e=$('toast'); if(!e)return;
  e.innerHTML=html; e.className='on rmtoast';
  clearTimeout(toastUndo.t);
  toastUndo.t=setTimeout(function(){if(e.className.indexOf('rmtoast')!==-1){e.className='';e.textContent='';}},8000);
}
function setUsePressed(el,on){
  var b=el.querySelector('.use');
  if(b){b.setAttribute('aria-pressed',on?'true':'false');}
}
function paint(){
  var ab=$('aired-box'), xb=$('expired-box');
  newsCards().forEach(function(el){
    rememberHome(el);
    var id=el.getAttribute('data-rmid');
    var isA=!!aired[id], isX=!!expired[id]&&!isA;
    el.classList.toggle('aired',isA);
    el.classList.toggle('expired',isX);
    el.classList.toggle('used',isA||el.classList.contains('used')&&!isX);
    if(isA)el.classList.add('used');
    if(isX)el.classList.remove('used');
    setUsePressed(el,isA);
    if(isA&&ab)ab.appendChild(el);
    else if(isX&&xb)xb.appendChild(el);
    else unpark(el);
  });
  var na=ab?ab.querySelectorAll('.item[data-rmid]').length:0;
  var nx=xb?xb.querySelectorAll('.item[data-rmid]').length:0;
  var ca=$('cnt-aired'), cx=$('cnt-expired');
  if(ca)ca.textContent=na?(na+' aired'):'None yet';
  if(cx)cx.textContent=nx?(nx+' expired'):'None yet';
  var sb=$('showdone');
  if(sb)sb.setAttribute('data-n', String(newsCards().filter(function(el){var id=el.getAttribute('data-rmid');return !aired[id]&&!expired[id];}).length));
  if(window.ditmSearchIndex)window.ditmSearchIndex();
  if(window.ditmSearch)window.ditmSearch();
}
function markAired(id,sync){
  if(!id)return;
  delete expired[id];
  aired[id]=Date.now();
  save();
  if(sync!==false)sendCmd('aired',id);
}
function markUnaired(id,sync){
  if(!id)return;
  delete aired[id];
  save();
  if(sync!==false)sendCmd('unaired',id);
}
function markExpired(id,sync){
  if(!id)return;
  if(aired[id])return;
  expired[id]=Date.now();
  save();
  if(sync!==false)sendCmd('expire',id);
}
function markUnexpired(id,sync){
  if(!id)return;
  delete expired[id];
  save();
  if(sync!==false)sendCmd('unexpire',id);
}
function restoreOne(id,sync){
  var wasA=!!aired[id], wasX=!!expired[id];
  delete aired[id]; delete expired[id];
  save();
  if(sync!==false){
    if(wasA)sendCmd('unaired',id);
    if(wasX)sendCmd('unexpire',id);
  }
  paint();
}
function listedFresh(){
  return newsCards().filter(function(el){
    var id=el.getAttribute('data-rmid');
    return id&&!aired[id]&&!expired[id]&&!el.classList.contains('rm-hide');
  });
}
function showDone(){
  var snap={aired:JSON.parse(JSON.stringify(aired)), expired:JSON.parse(JSON.stringify(expired))};
  var fresh=listedFresh();
  var ticks=[], rest=[];
  fresh.forEach(function(el){
    var id=el.getAttribute('data-rmid');
    var on=el.querySelector('.use')&&el.querySelector('.use').getAttribute('aria-pressed')==='true';
    if(on||aired[id])ticks.push(id); else rest.push(id);
  });
  // already-ticked earlier in the show (in aired) stay aired; this pass also airs ticks still in fresh (pressed)
  ticks.forEach(function(id){aired[id]=aired[id]||Date.now(); delete expired[id];});
  rest.forEach(function(id){if(!aired[id])expired[id]=Date.now();});
  save();
  ticks.forEach(function(id){sendCmd('aired',id);});
  if(rest.length)sendCmd('expire','*');
  paint();
  var na=Object.keys(aired).length, nx=Object.keys(expired).length;
  var msg='Show\'s done \u00B7 '+na+' aired, '+nx+' expired \u00B7 <button type="button" id="sd-undo" class="undobtn">Undo</button> <button type="button" id="sd-recap" class="undobtn">Post-show recap</button>';
  toastUndo(msg);
  var undone=false;
  if($('sd-undo'))$('sd-undo').onclick=function(){
    if(undone)return; undone=true;
    aired=snap.aired; expired=snap.expired; save();
    ticks.forEach(function(id){sendCmd('unaired',id);});
    rest.forEach(function(id){sendCmd('unexpire',id);});
    paint();
    var e=$('toast'); if(e){e.className='';e.textContent='Undone'; setTimeout(function(){e.textContent='';},1600);}
  };
  if($('sd-recap'))$('sd-recap').onclick=function(){if(window.ditmPostShow)window.ditmPostShow.open();};
  if(window.ditmPostShow)window.ditmPostShow.open();
}
function openDlg(){var d=$('done-dlg');if(!d)return;if(d.showModal){try{d.showModal()}catch(e){d.setAttribute('open','')}}else d.setAttribute('open','')}
function closeDlg(){var d=$('done-dlg');if(!d)return;if(d.close){try{d.close()}catch(e){d.removeAttribute('open')}}else d.removeAttribute('open')}
if($('showdone'))$('showdone').onclick=function(){openDlg()};
if($('done-go'))$('done-go').onclick=function(){closeDlg();showDone();};
if($('done-no'))$('done-no').onclick=function(){closeDlg()};
if($('done-x'))$('done-x').onclick=function(){closeDlg()};
if($('done-dlg'))$('done-dlg').addEventListener('cancel',function(e){e.preventDefault();closeDlg();});
document.addEventListener('click',function(e){
  var u=e.target&&e.target.closest&&e.target.closest('.use');
  if(u){
    var el=u.closest('.item'), id=el&&el.getAttribute('data-rmid');
    if(!id)return;
    setTimeout(function(){
      var on=u.getAttribute('aria-pressed')==='true';
      if(on){markAired(id); if(expired[id]){delete expired[id]; save(); sendCmd('unexpire',id);} }
      else {markUnaired(id);}
      paint();
    },0);
    return;
  }
  var rst=e.target&&e.target.closest&&e.target.closest('.sd-restore');
  if(rst){
    e.preventDefault();e.stopPropagation();
    var el=rst.closest('.item'), id=el&&el.getAttribute('data-rmid');
    if(id)restoreOne(id);
  }
}, false);
window.ditmShowDone={
  apply:function(c){
    if(!c||!c.cmd)return;
    var id=c.id||'';
    if(c.cmd==='expire'&&id==='*'){
      listedFresh().forEach(function(el){
        var i=el.getAttribute('data-rmid');
        var on=el.querySelector('.use')&&el.querySelector('.use').getAttribute('aria-pressed')==='true';
        if(i&&!on&&!aired[i])expired[i]=c.at||Date.now();
      });
      save();paint();return;
    }
    if(c.cmd==='unexpire'&&id==='*'){expired={};save();paint();return;}
    if(!/^r-[0-9a-f]{8,32}$/.test(id))return;
    if(c.cmd==='aired'){aired[id]=c.at||Date.now();delete expired[id];save();paint();}
    if(c.cmd==='unaired'){delete aired[id];save();paint();}
    if(c.cmd==='expire'){if(!aired[id]){expired[id]=c.at||Date.now();save();paint();}}
    if(c.cmd==='unexpire'){delete expired[id];save();paint();}
  },
  paint:paint,
  aired:function(){return Object.keys(aired);},
  expired:function(){return Object.keys(expired);}
};
newsCards().forEach(rememberHome);
paint();
})();
"""

POSTSHOW_JS = r"""
(function(){
var $=function(i){return document.getElementById(i)};
function readJSON(k, fb){try{var v=JSON.parse(localStorage.getItem(k)||'');return v&&typeof v==='object'?v:(fb||{})}catch(e){return fb||{}}}
function stories(){
  if(window.DITM_STORIES&&window.DITM_STORIES.length)return window.DITM_STORIES;
  var el=$('ditm-stories');
  if(!el)return [];
  try{return JSON.parse(el.textContent||'[]')||[]}catch(e){return []}
}
function byId(){var m={}; stories().forEach(function(s){if(s&&s.id)m[s.id]=s;}); return m;}
function showDate(){
  var d=(window.DITM_SHOW&&window.DITM_SHOW.date)||document.body.getAttribute('data-showdate')||($('ssbtn')&&$('ssbtn').getAttribute('data-showdate'))||'';
  return d;
}
function showLabel(){
  var d=showDate();
  if(!d)return '';
  try{var x=new Date(d+'T12:00:00-06:00');
    return x.toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric',timeZone:'America/Chicago'});
  }catch(e){return d;}
}
function skipSocial(s){
  if(!s)return true;
  if(s.rumor||s.chisme||(s.badge&&/rumor/i.test(s.badge)))return true;
  if(s.kids||(s.desk&&/family/i.test(s.desk)))return true;
  return false;
}
function trimAt(s,n){
  s=String(s||'').replace(/\s+/g,' ').trim();
  if(s.length<=n)return s;
  var c=s.slice(0,n-1).replace(/\s+\S*$/,'').replace(/[ ,;:\-–—]+$/,'');
  return (c||s.slice(0,n-1))+'…';
}
function confirmTag(s){return s&&s.confirm?' (CONFIRM BEFORE AIR)':'';}
function draftX(s){
  var src=s.source?(' — '+s.source):'';
  var core='"'+s.title+'"'+src+confirmTag(s);
  if(s.url&&core.length+1+s.url.length<=280)return core+' '+s.url;
  return trimAt(core,280);
}
function draftCaption(s){
  var parts=[s.title];
  if(s.synopsis)parts.push(s.synopsis);
  if(s.source)parts.push('Source: '+s.source);
  if(s.url)parts.push(s.url);
  if(s.confirm)parts.push('CONFIRM BEFORE AIR.');
  parts.push('From Drew in the Morning in McAllen.');
  return parts.join(' ');
}
function draftLinkedIn(s){
  var line=s.title+(s.synopsis?(' — '+s.synopsis):'')+(s.source?(' ('+s.source+')'):'')+confirmTag(s);
  return trimAt(line,400);
}
function recapX(items, dateLabel){
  var lines=['Drew in the Morning'+(dateLabel?(' · '+dateLabel):'')+':'];
  items.forEach(function(s){if(lines.join('\n').length>220)return; lines.push('• '+s.title);});
  var t=lines.join('\n');
  return trimAt(t,280);
}
function recapCaption(items, dateLabel){
  var parts=['Highlights from Drew in the Morning'+(dateLabel?(' on '+dateLabel):'')+'.'];
  items.forEach(function(s){parts.push('• '+s.title+(s.source?(' ('+s.source+')'):''));});
  parts.push('Draft only — nothing has been posted.');
  return parts.join('\n');
}
function recapLinkedIn(items, dateLabel){
  var parts=['What we talked about on Drew in the Morning'+(dateLabel?(' ('+dateLabel+')'):'')+'.'];
  items.forEach(function(s){parts.push(s.title+'.');});
  return parts.join(' ');
}
function guests(){
  var fm=readJSON('ditm-gp-form-v1',{});
  var out=[];
  if(fm['g-name'])out.push({kind:'guest',name:fm['g-name'],title:fm['g-title']||'',blurb:fm['g-blurb']||''});
  if(fm['c-name'])out.push({kind:'caller',name:fm['c-name'],title:fm['c-title']||''});
  return out;
}
function copy(text, btn){
  function done(){if(btn){var o=btn.textContent;btn.textContent='Copied';setTimeout(function(){btn.textContent=o;},1200);}}
  function fb(){var a=document.createElement('textarea');a.value=text;a.setAttribute('readonly','');a.style.cssText='position:fixed;opacity:0';document.body.appendChild(a);a.select();try{document.execCommand('copy');done()}catch(e){}a.remove();}
  if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(text).then(done,fb);else fb();
}
function row(s, drafts){
  var h='<article class="ps-story'+(s.confirm?' confirm':'')+(s.rumor?' rumor':'')+'">';
  h+='<h3>'+(s.url?('<a href="'+s.url.replace(/"/g,'&quot;')+'" target="_blank" rel="noopener noreferrer">'):'')+esc(s.title)+(s.url?'</a>':'')+'</h3>';
  h+='<p class="ps-meta">'+esc([s.desk,s.source,s.date].filter(Boolean).join(' · '));
  if(s.confirm)h+=' <span class="cf">CONFIRM BEFORE AIR</span>';
  if(s.rumor)h+=' <span class="cf">RUMOR · CONFIRM BEFORE AIR</span>';
  h+='</p>';
  if(s.synopsis)h+='<p class="ps-syn">'+esc(s.synopsis)+'</p>';
  if(drafts&&!skipSocial(s)){
    h+='<div class="ps-drafts"><h4>Social drafts (not posted)</h4>';
    [['X',draftX(s)],['Instagram / Facebook',draftCaption(s)],['LinkedIn',draftLinkedIn(s)]].forEach(function(pair){
      h+='<div class="ps-d"><div class="ps-dl"><b>'+pair[0]+'</b> <span>'+pair[1].length+(pair[0]==='X'?'/280':'')+'</span> <button type="button" class="ps-copy" data-copy="'+encodeURIComponent(pair[1])+'">Copy</button></div><pre>'+esc(pair[1])+'</pre></div>';
    });
    h+='</div>';
  }else if(drafts){
    h+='<p class="mut">No social draft: '+(s.rumor||s.chisme?'chisme / rumor':'story involves kids or the Family &amp; Kids desk')+'.</p>';
  }
  h+='</article>';
  return h;
}
function esc(t){return String(t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function render(root){
  if(!root)return;
  var map=byId(), aired=readJSON('ditm-aired-v1',{}), expired=readJSON('ditm-expired-v1',{});
  var airedIds=Object.keys(aired).sort(function(a,b){return (aired[b]||0)-(aired[a]||0);});
  var items=airedIds.map(function(id){return map[id];}).filter(Boolean);
  var missing=airedIds.filter(function(id){return !map[id];}).length;
  var social=items.filter(function(s){return !skipSocial(s);});
  var dateLabel=showLabel();
  var peeps=guests();
  var desks={};
  items.forEach(function(s){if(s.desk)desks[s.desk]=(desks[s.desk]||0)+1;});
  var segs=Object.keys(desks);
  var html='<header class="ps-top"><p class="ps-k">Post-show recap</p><h1>Drew in the Morning</h1><p class="ps-date">'+esc(dateLabel||'Show day')+'</p>';
  html+='<p class="mut">Built on this device from the stories you marked Aired. Drafts only — nothing is posted. Facts come from the packet; nothing is invented.</p>';
  html+='<p class="ps-acts"><button type="button" id="ps-print">Print / Save PDF</button> <button type="button" id="ps-json">Download aired.json</button>';
  if($('post-show')&&document.body.classList.contains('show-post'))html+=' <button type="button" id="ps-back">Back to the board</button>';
  html+='</p></header>';
  html+='<section class="ps-hl"><h2>Highlights</h2>';
  if(!items.length)html+='<p>No stories are marked Aired yet. Tick stories on the board, then press Show\'s done.</p>';
  else{
    html+='<p>'+items.length+' stor'+(items.length===1?'y':'ies')+' aired';
    if(segs.length)html+=', across '+esc(segs.join(', '));
    html+='. '+Object.keys(expired).length+' expired (on the board but not ticked).';
    if(missing)html+=' '+missing+' aired id'+(missing===1?' is':'s are')+' not in this packet\'s story list.';
    html+='</p><ul>'+items.map(function(s){return '<li>'+esc(s.title)+(s.desk?' <span class="mut">('+esc(s.desk)+')</span>':'')+'</li>';}).join('')+'</ul>';
  }
  html+='</section>';
  if(peeps.length){
    html+='<section><h2>Guests and callers</h2><ul>';
    peeps.forEach(function(p){html+='<li><b>'+esc(p.kind)+':</b> '+esc(p.name)+(p.title?(' — '+esc(p.title)):'')+(p.blurb?(' · '+esc(p.blurb)):'')+'</li>';});
    html+='</ul></section>';
  }
  if(segs.length){
    html+='<section><h2>Segments with aired stories</h2><ul>';
    segs.forEach(function(d){html+='<li>'+esc(d)+' — '+desks[d]+'</li>';});
    html+='</ul></section>';
  }
  html+='<section><h2>Aired stories</h2>'+(items.map(function(s){return row(s,true);}).join('')||'<p>None.</p>')+'</section>';
  if(social.length){
    html+='<section class="ps-all"><h2>One overall show recap (draft only)</h2>';
    [['X',recapX(social,dateLabel)],['Instagram / Facebook',recapCaption(social,dateLabel)],['LinkedIn',recapLinkedIn(social,dateLabel)]].forEach(function(pair){
      html+='<div class="ps-d"><div class="ps-dl"><b>'+pair[0]+'</b> <span>'+pair[1].length+(pair[0]==='X'?'/280':'')+'</span> <button type="button" class="ps-copy" data-copy="'+encodeURIComponent(pair[1])+'">Copy</button></div><pre>'+esc(pair[1])+'</pre></div>';
    });
    html+='</section>';
  }
  html+='<p class="mut">A later post-show routine can pick this up from a downloaded aired.json (or a used-on-show issue attachment). That file is written only on this device unless you save or send it — this page does not upload it or post anything.</p>';
  root.innerHTML=html;
  root.onclick=function(e){
    var b=e.target.closest('.ps-copy');
    if(b){e.preventDefault();copy(decodeURIComponent(b.getAttribute('data-copy')||''),b);return;}
    if(e.target.id==='ps-print'){e.preventDefault();window.print();return;}
    if(e.target.id==='ps-back'){e.preventDefault();close();return;}
    if(e.target.id==='ps-json'){e.preventDefault();download();return;}
  };
}
function payload(){
  var map=byId(), aired=readJSON('ditm-aired-v1',{}), expired=readJSON('ditm-expired-v1',{});
  function pack(ids){return Object.keys(ids).map(function(id){var s=map[id]||{id:id}; return Object.assign({airedAt:ids[id]},s);});}
  return {v:1, showDate:showDate(), generatedAt:new Date().toISOString(), timezone:'America/Chicago',
    aired:pack(aired), expired:pack(expired), guests:guests()};
}
function download(){
  var blob=new Blob([JSON.stringify(payload(),null,2)],{type:'application/json'});
  var a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  a.download='ditm-aired-'+(showDate()||'show')+'.json';
  document.body.appendChild(a); a.click(); a.remove();
}
function open(){
  var panel=$('post-show');
  if(panel){
    document.body.classList.add('show-post');
    panel.hidden=false;
    render($('ps-root')||panel);
    try{panel.scrollIntoView({block:'start'});}catch(e){}
    return;
  }
  // standalone page
  var root=$('ps-root'); if(root)render(root);
}
function close(){
  document.body.classList.remove('show-post');
  var panel=$('post-show'); if(panel)panel.hidden=true;
}
window.ditmPostShow={open:open,close:close,render:render,payload:payload};
if($('ps-root')&&!$('pin'))open(); // standalone post-show page
if($('ps-open'))$('ps-open').onclick=function(){open();};
document.addEventListener('click',function(e){
  var a=e.target&&e.target.closest&&e.target.closest('a[href="#post-show"]');
  if(!a)return; e.preventDefault(); open();
});
})();
"""

TLDR_JS = r"""
(function(){
function needs(el){return el && el.scrollHeight>el.clientHeight+2}
function enhance(p){
  if(!p||p.dataset.expInit)return;
  p.dataset.expInit='1';
  if(!needs(p))return;
  var b=document.createElement('button');
  b.type='button';b.className='tldr-exp';b.setAttribute('aria-expanded','false');b.setAttribute('aria-label','Show full synopsis');
  b.textContent='More';
  b.addEventListener('click',function(e){
    e.preventDefault();e.stopPropagation();
    var item=p.closest('.item'); if(!item)return;
    var open=item.classList.toggle('tldr-open');
    b.setAttribute('aria-expanded',open?'true':'false');
    b.setAttribute('aria-label',open?'Hide extra synopsis':'Show full synopsis');
    b.textContent=open?'Less':'More';
  });
  p.insertAdjacentElement('afterend',b);
}
function paint(){
  document.querySelectorAll('.item.trn .tldr').forEach(function(p){
    if(p.dataset.expInit)return;
    var r=p.getBoundingClientRect();
    if(r.bottom< -20||r.top>(window.innerHeight||0)+80)return;
    enhance(p);
  });
}
if(window.IntersectionObserver){
  var io=new IntersectionObserver(function(ents){
    ents.forEach(function(en){
      if(!en.isIntersecting)return;
      enhance(en.target);
      io.unobserve(en.target);
    });
  },{root:null,rootMargin:'80px',threshold:0});
  function watch(){document.querySelectorAll('.item.trn .tldr').forEach(function(p){if(!p.dataset.expInit)io.observe(p);});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){requestAnimationFrame(watch);});
  else requestAnimationFrame(watch);
  window.ditmTldr={paint:function(){requestAnimationFrame(function(){watch();});},enhance:enhance};
}else{
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){requestAnimationFrame(paint);});
  else requestAnimationFrame(paint);
  window.ditmTldr={paint:function(){requestAnimationFrame(paint);}};
}
})();
"""

CHY_JS = r"""
(function(){var api=window.ditmRos;if(!api)return;var $=function(i){return document.getElementById(i)};
var LK='ditm-chyron-topic-v1',RX=/^[A-Za-z0-9_-]{6,64}$/,mem=null,CMDS={start:1,stop:1,hold:1,resume:1,toggle:1,logo:1,item:1,guest:1,guest_hide:1,caller:1,caller_show:1,caller_hide:1,next:1,prev:1,goto:1,clear:1,show:1,remove:1,restore:1,aired:1,unaired:1,expire:1,unexpire:1},IDRX=/^i-[0-9a-f]{10}$/,RMID=/^r-[0-9a-f]{8,32}$/;
function cap(v,n){return(typeof v==='string')?v.replace(/[\u0000-\u001f\u007f-\u009f]+/g,' ').replace(/\s+/g,' ').trim().slice(0,n):''}
function httpsOnly(u){try{var x=new URL(u);return(x.protocol==='https:'&&x.hostname&&!x.username)?x.href:''}catch(e){return ''}}
function gget(){try{return localStorage.getItem(LK)}catch(e){return mem}}function gset(v){mem=v;try{localStorage.setItem(LK,v)}catch(e){}}
var nq=/[?&]ntfy=(https:\/\/ntfy\.sh|http:\/\/127\.0\.0\.1:\d+)(?:&|$)/.exec((function(){try{return decodeURIComponent(location.search)}catch(e){return''}})()),BASE=nq?nq[1]:'https://ntfy.sh';
var q=/[?&#]ctl=([A-Za-z0-9_-]{6,64})/.exec(location.search+location.hash);
if(q){gset(q[1]);try{history.replaceState(null,'',location.pathname)}catch(e){}}
var topic=gget();if(!RX.test(topic||''))topic=null;
var last=null,vis=true,ADRX=/^a-[0-9a-f]{10}$/;
function send(cmd,idx,id,x){if(!topic||!Object.prototype.hasOwnProperty.call(CMDS,cmd))return;var m={k:'cmd',cmd:cmd,at:Date.now(),v:1};if(typeof idx==='number')m.idx=idx;if(cmd==='item'){if(IDRX.test(id||''))m.id=id;else{var h=cap(x&&x.headline,100);if(!h)return;m.headline=h;m.line=cap(x.line,118);m.kicker=cap(x.kicker,44);if(ADRX.test(id||''))m.id=id}}
 if((cmd==='remove'||cmd==='restore'||cmd==='aired'||cmd==='unaired'||cmd==='expire'||cmd==='unexpire')&&id){if(!(RMID.test(id)||id==='*'))return;m.id=id}
 if(cmd==='guest'&&x){m.name=cap(x.name,60);m.title=cap(x.title,80);m.blurb=cap(x.blurb,140);if(!m.name)return}
 if(cmd==='caller'&&x){m.name=cap(x.name,60);m.title=cap(x.title,80);m.photo=(x.photo&&httpsOnly(x.photo))||'';if(!m.name)return}
 try{fetch(BASE+'/'+topic,{method:'POST',body:JSON.stringify(m)}).catch(function(){})}catch(e){}}
function ago(ms){var s=Math.max(0,Math.round(ms/1000));return s<60?s+'s':s<3600?Math.floor(s/60)+'m':Math.floor(s/3600)+'h'}
var sentId=null,sentAt=0;
function card(id){return id?document.querySelector('[data-chyid="'+id+'"]'):null}
function isChyId(id){return IDRX.test(id||'')||ADRX.test(id||'')}
function airId(){if(last&&isChyId(last.item)&&last.rx>sentAt+200)return last.item;if(sentId&&Date.now()-sentAt<4000&&!(last&&last.rx>sentAt+200))return sentId;return(last&&isChyId(last.item))?last.item:null}
function ui(){var on=!!topic;document.body.classList.toggle('chy-on',on);
 var pill=$('mc-pill');if(pill){var stopped=api.idle&&api.idle(),live=!stopped&&last&&last.running,held=!stopped&&((api.held&&api.held())||(last&&last.held)),air=!stopped&&last&&(last.visible||last.logo||last.guest||last.caller);pill.textContent=held?'HELD':(live?'LIVE':(air?'ON AIR':'STANDBY'));pill.className='mcp '+(held?'held':live?'live':air?'onair':'stand')}
 var aid=airId();[].forEach.call(document.querySelectorAll('.onair'),function(e){if(!aid||e.getAttribute('data-chyid')!==aid)e.classList.remove('onair')});
 [].forEach.call(document.querySelectorAll('.chysend'),function(b){var is=!!aid&&b.getAttribute('data-chyid')===aid;b.setAttribute('aria-pressed',is?'true':'false');b.querySelector('.ct').textContent=is?'On air':'Chyron'});
 var ac=card(aid);if(ac)ac.classList.add('onair');if($('chlink'))$('chlink').hidden=on;if($('mb-hold'))$('mb-hold').hidden=!on;
 var h=api.held();['chhold','mb-hold'].forEach(function(i){var b=$(i);if(!b)return;b.textContent=h?'\u25B6 Resume':'\u23F8 Hold';b.classList.toggle('held',h);b.setAttribute('aria-pressed',h?'true':'false')});
 var c=$('chclr');if(c)c.textContent=(last&&last.visible===false)?'Show':'Clear';
 var st=$('chst');if(st){if(!last)st.textContent='waiting for the chyron\u2026';else{var age=Date.now()-last.rx,live=last.running;
  var au=aid&&last.item?(card(aid)?card(aid).getAttribute('data-chyh'):'item'):null;
  st.textContent=(au?'audible: '+au:(last.letter||'?'))+' \u00B7 '+(live?(last.held?'HELD':'AUTO'):'MANUAL')+(last.logo?' \u00B7 logo only':(last.visible===false?' \u00B7 off air':''))+(last.guest?' \u00B7 guest: '+last.guest:'')+(last.caller?' \u00B7 on the phone: '+last.caller:'')+' \u00B7 '+(age>600000?'last heard '+ago(age)+' ago':'synced');st.dataset.state=live?(last.held?'held':'auto'):'manual'}}}
api.onChange=ui;api.onStart=function(){send('start')};api.onStop=function(){send('stop');send('clear')};
function openDlg(id){var d=$(id);if(!d)return;if(d.showModal){try{d.showModal()}catch(e){d.setAttribute('open','')}}else d.setAttribute('open','')}
function closeDlg(id){var d=$(id);if(!d)return;if(d.close){try{d.close()}catch(e){d.removeAttribute('open')}}else d.removeAttribute('open')}
function needLink(){if(topic)return false;openDlg('link-dlg');return true}
function hold(){if(needLink())return;if(api.held()){api.resume();send('resume')}else{api.hold();send('hold')}}
['chhold','mb-hold'].forEach(function(i){var b=$(i);if(b)b.onclick=hold});
if($('chprev'))$('chprev').onclick=function(){if(needLink())return;send('prev')};
/* ---- guest + phone caller panels (free text goes out only with the guest / caller commands, length-capped) ---- */
var FK='ditm-gp-form-v1',FM={};try{FM=JSON.parse(localStorage.getItem(FK)||'{}')||{}}catch(e){}
['g-name','g-title','g-blurb','c-name','c-title','c-photo'].forEach(function(i){var e=$(i);if(!e)return;if(typeof FM[i]==='string')e.value=FM[i].slice(0,1000);e.addEventListener('input',function(){FM[i]=e.value;try{localStorage.setItem(FK,JSON.stringify(FM))}catch(x){}})});
function gv(i,n){return cap($(i)?$(i).value:'',n)}function gmsg(t){['gp-msg','c-msg'].forEach(function(i){if($(i))$(i).textContent=t||''})}
if($('g-show'))$('g-show').onclick=function(){var n=gv('g-name',60);if(!n){gmsg('Type the guest\u2019s name first.');return}gmsg('');send('guest',undefined,undefined,{name:n,title:gv('g-title',80),blurb:gv('g-blurb',140)})};
if($('g-hide'))$('g-hide').onclick=function(){gmsg('');send('guest_hide')};
if($('c-go'))$('c-go').onclick=function(){var n=gv('c-name',60);if(!n){gmsg('Type the caller\u2019s name first.');return}var ph=($('c-photo').value||'').trim();if(ph&&!httpsOnly(ph)){gmsg('The photo link must start with https://');return}gmsg('');send('caller',undefined,undefined,{name:n,title:gv('c-title',80),photo:ph?httpsOnly(ph):''})};
if($('c-show'))$('c-show').onclick=function(){send('caller_show')};if($('c-hide'))$('c-hide').onclick=function(){send('caller_hide')};
/* upload: shrink to <=400px JPEG in the browser, then PUT it to the private topic as an ntfy attachment; ntfy answers with the https link of the file */
if($('c-file'))$('c-file').onchange=function(){var f=this.files&&this.files[0],up=$('c-up');this.value='';if(!f)return;if(!topic){up.textContent='Link the chyron first.';return}if(!/^image\//.test(f.type||'')){up.textContent='That file is not an image.';return}
 up.textContent='Preparing the photo\u2026';var r=new FileReader();r.onerror=function(){up.textContent='Could not read that file.'};
 r.onload=function(){var im=new Image();im.onerror=function(){up.textContent='Could not open that image.'};
  im.onload=function(){var k=Math.min(1,400/Math.max(im.width,im.height)),w=Math.max(1,Math.round(im.width*k)),h=Math.max(1,Math.round(im.height*k)),cv=document.createElement('canvas');cv.width=w;cv.height=h;var cx=cv.getContext('2d');cx.fillStyle='#fff';cx.fillRect(0,0,w,h);cx.drawImage(im,0,0,w,h);
   var prev=cv.toDataURL('image/jpeg',.85);cv.toBlob(function(bl){if(!bl){up.textContent='Could not shrink that image.';return}up.textContent='Uploading\u2026';
    fetch(BASE+'/'+topic+'?filename=caller.jpg',{method:'PUT',body:bl,headers:{'Content-Type':'image/jpeg'}}).then(function(x){return x.ok?x.json():Promise.reject(new Error('HTTP '+x.status))}).then(function(j){var u=j&&j.attachment&&j.attachment.url,ok=u&&(httpsOnly(u)||(BASE.indexOf('http://127.0.0.1:')===0&&u.indexOf(BASE+'/')===0));
     if(!ok){up.textContent='The upload did not return a link.';return}$('c-photo').value=u;FM['c-photo']=u;try{localStorage.setItem(FK,JSON.stringify(FM))}catch(e){}
     var pv=$('c-prev');pv.src=prev;pv.hidden=false;up.textContent='Photo ready (ntfy keeps it about 3 hours). Tap Bring caller on.'}).catch(function(e){up.textContent='Upload failed ('+(e&&e.message||'network')+'). Paste an https link instead.'})},'image/jpeg',.85)};
  im.src=r.result};r.readAsDataURL(f)};
document.addEventListener('click',function(e){var b=e.target&&e.target.closest?e.target.closest('.chysend'):null;if(!b)return;e.preventDefault();if(needLink())return;var id=b.getAttribute('data-chyid');if(IDRX.test(id||'')){sentId=id;sentAt=Date.now();send('item',undefined,id);ui();return}var h=cap(b.getAttribute('data-chyh'),100);if(!h)return;sentId=ADRX.test(id||'')?id:'';sentAt=Date.now();send('item',undefined,id,{headline:h,line:cap(b.getAttribute('data-chyl'),118),kicker:cap(b.getAttribute('data-chyk'),44)});ui()});if($('chnext'))$('chnext').onclick=function(){if(needLink())return;send('next')};
if($('chclr'))$('chclr').onclick=function(){if(needLink())return;send(last&&last.visible===false?'show':'clear')};
function applyLink(v){v=(v||'').trim().replace(/^.*ctl=/,'');if(!RX.test(v))return false;gset(v);topic=v;connect();ui();closeDlg('link-dlg');return true}
if($('chlink'))$('chlink').onclick=function(){openDlg('link-dlg')};
if($('link-go'))$('link-go').onclick=function(){if(!applyLink($('link-code')&&$('link-code').value)){var e=$('link-code');if(e)e.placeholder='That code was not recognized'};};
['link-x','g-x','c-x','stop-x'].forEach(function(i){if($(i))$(i).onclick=function(){closeDlg({ 'link-x':'link-dlg','g-x':'g-dlg','c-x':'c-dlg','stop-x':'stop-dlg'}[i])}});
if($('mc-guest'))$('mc-guest').onclick=function(){if(needLink())return;openDlg('g-dlg')};
if($('mc-caller'))$('mc-caller').onclick=function(){if(needLink())return;openDlg('c-dlg')};
if($('mc-logo'))$('mc-logo').onclick=function(){if(needLink())return;send('logo')};
function ctDate(ms){return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms))}
function ctMin(ms){var o={};new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',hourCycle:'h23',hour:'2-digit',minute:'2-digit'}).formatToParts(new Date(ms)).forEach(function(p){if(p.type!=='literal')o[p.type]=parseInt(p.value,10)});return (o.hour%24)*60+o.minute}
/* the chyron owns the truth: mirror its state (running, held, which block) and follow it when it is running */
function onState(st){var rx=Date.now();st.rx=rx;if(last&&(last.at||0)>(st.at||0))return;last=st;
 var fresh=rx-(st.at||0)<240000;
 if(fresh&&st.running&&st.startAt){var sm=ctMin(st.startAt),a=api.snap(),hs=Math.round((st.holdMs||0)/1000),hd=st.held?st.heldAt:null;
  if(a.start!==sm||a.holdS!==hs||(a.heldAt===null)!==(hd===null))api.adopt({startMin:sm,holdS:hs,heldAt:hd})}
 ui()}
var es=null;function connect(){if(es){try{es.close()}catch(e){}es=null}if(!topic||!window.EventSource)return;
 es=new EventSource(BASE+'/'+topic+'/sse?since=6h');
 es.onmessage=function(ev){var m;try{m=JSON.parse(ev.data)}catch(e){return}if(!m||m.event!=='message'||!m.message)return;var c;try{c=JSON.parse(m.message)}catch(e){return}
  if(c&&c.k==='state'&&typeof c.at==='number')onState(c);
  if(c&&c.k==='cmd'&&(c.cmd==='remove'||c.cmd==='restore')&&window.ditmRemove)window.ditmRemove.apply(c);
  if(c&&c.k==='cmd'&&(c.cmd==='aired'||c.cmd==='unaired'||c.cmd==='expire'||c.cmd==='unexpire')&&window.ditmShowDone)window.ditmShowDone.apply(c)};
 es.onerror=function(){var st=$('chst');if(st&&!last)st.textContent='connecting\u2026'}}
connect();ui();setInterval(ui,5000);
window.ditmChy={send:send,linked:function(){return !!topic},state:function(){return last}};
})();
"""
REMOVE_JS = r"""
(function(){
var RK='ditm-removed-v1',$=function(i){return document.getElementById(i)},mem={};
var store={get:function(k){try{var v=localStorage.getItem(k);return v===null?(mem[k]===undefined?null:mem[k]):v}catch(e){return mem[k]===undefined?null:mem[k]}},
 set:function(k,v){mem[k]=v;try{localStorage.setItem(k,v)}catch(e){}}};
var removed={};try{removed=JSON.parse(store.get(RK)||'{}')||{}}catch(e){removed={}}
function ids(){return Object.keys(removed)}
function save(){store.set(RK,JSON.stringify(removed))}
function sendCmd(cmd,id){if(window.ditmChy&&window.ditmChy.send)window.ditmChy.send(cmd,undefined,id)}
function showUndo(id){var e=$('toast');if(!e)return;e.innerHTML='Removed \u00B7 <button type="button" id="rm-undo" class="undobtn">Undo</button>';e.className='on rmtoast';
 clearTimeout(showUndo.t);var undone=false;var b=$('rm-undo');if(b)b.onclick=function(){undone=true;restore(id,false);e.className='';e.textContent=''};
 showUndo.t=setTimeout(function(){if(!undone){e.className='';e.textContent=''}},6000)}
function recount(){document.querySelectorAll('details.sec').forEach(function(sec){var all=sec.querySelectorAll('.item[data-rmid]');if(!all.length)return;
 var n=sec.querySelectorAll('.item[data-rmid]:not(.rm-hide)').length;var cnt=sec.querySelector('summary .cnt');
 if(cnt&&/stor(y|ies)/i.test(cnt.textContent||''))cnt.textContent=n?(n+' stor'+(n===1?'y':'ies')):'No stories today'})}
function paintMore(){var n=ids().length,b=$('rm-show'),r=$('rm-restore');
 if(b)b.textContent=(document.body.classList.contains('show-rm')?'Hide removed':'Show removed')+' ('+n+')';
 if(r)r.disabled=!n}
function applyAll(){var show=document.body.classList.contains('show-rm');
 document.querySelectorAll('.item[data-rmid]').forEach(function(el){var id=el.getAttribute('data-rmid'),gone=!!removed[id];
  el.classList.toggle('rm-hide',gone&&!show);el.classList.toggle('rm-gone',gone);
  var b=el.querySelector('.rmx');if(b){b.setAttribute('aria-label',gone?'Restore story':'Remove story');b.setAttribute('title',gone?'Restore story':'Remove story')}});
 recount();paintMore();if(window.ditmSearch)window.ditmSearch()}
function hide(id,undo){removed[id]=Date.now();save();applyAll();if(undo)showUndo(id);sendCmd('remove',id)}
function restore(id,sync){delete removed[id];save();applyAll();if(sync!==false)sendCmd('restore',id)}
function restoreAll(){if(!ids().length)return;removed={};save();applyAll();sendCmd('restore','*')}
document.addEventListener('click',function(e){var b=e.target&&e.target.closest&&e.target.closest('.rmx');if(!b)return;
 e.preventDefault();e.stopPropagation();var el=b.closest('.item'),id=el&&el.getAttribute('data-rmid');if(!id)return;
 if(removed[id])restore(id);else hide(id,true)},true);
if($('rm-show'))$('rm-show').onclick=function(){document.body.classList.toggle('show-rm');applyAll()};
if($('rm-restore'))$('rm-restore').onclick=function(){restoreAll()};
window.ditmRemove={apply:function(c){if(!c||!c.cmd)return;var id=c.id||'';
  if(c.cmd==='restore'&&id==='*'){removed={};save();applyAll();return}
  if(!/^r-[0-9a-f]{8,32}$/.test(id))return;
  if(c.cmd==='remove'){removed[id]=c.at||Date.now();save();applyAll()}
  if(c.cmd==='restore'){delete removed[id];save();applyAll()}}};
applyAll();
})();
"""

SHOW_JS = r"""
(function(){var b=document.getElementById('ssbtn');if(!b)return;
var SD=b.dataset.showdate,KEY='ditm-showstart-v1:'+SD,PLAN=480,mem={},$=function(i){return document.getElementById(i)};
var store={get:function(k){try{var v=localStorage.getItem(k);return v===null?(mem[k]===undefined?null:mem[k]):v}catch(e){return mem[k]===undefined?null:mem[k]}},
 set:function(k,v){mem[k]=v;try{localStorage.setItem(k,v)}catch(e){}},del:function(k){delete mem[k];try{localStorage.removeItem(k)}catch(e){}}};
var parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',hourCycle:'h23',hour:'2-digit',minute:'2-digit',second:'2-digit'}),
 ctd=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'});
function ct(){var o={};parts.formatToParts(new Date()).forEach(function(p){if(p.type!=='literal')o[p.type]=parseInt(p.value,10)});return{h:o.hour%24,m:o.minute,s:o.second}}
function fmt(m){m=Math.floor(m+1e-6);var h=Math.floor(m/60)%24,mm=m%60;return(h%12||12)+':'+(mm<10?'0':'')+mm}
function fmtp(m){return fmt(m)+' '+(Math.floor(m/60)%24<12?'AM':'PM')}
var rows=[].slice.call(document.querySelectorAll('.tr[data-off]')),start=null,holdS=0,heldAt=null,idle=false,fq=/[?&]t=(-?\d+(?:\.\d+)?)/.exec(location.search),FORCE=fq?parseFloat(fq[1])*60:null,segs=[].slice.call(document.querySelectorAll('#tl a[data-off]')),TL=$('tl'),PH=$('ph');
try{var o=JSON.parse(store.get(KEY)||'null');if(o){if(typeof o.startMin==='number')start=o.startMin;if(typeof o.holdS==='number')holdS=o.holdS;if(typeof o.heldAt==='number')heldAt=o.heldAt;if(o.idle)idle=true}}catch(e){}
function persist(){if(start===null&&heldAt===null&&!holdS&&!idle)store.del(KEY);else store.set(KEY,JSON.stringify({startMin:start,setAt:new Date().toISOString(),holdS:holdS,heldAt:heldAt,idle:!!idle}))}
/* hold = freeze the current topic and the show clock; resume pushes every later block back by the time held. window.ditmRos lets the chyron link (CHY_JS) drive and mirror it */
var api=window.ditmRos={held:function(){return heldAt!==null},idle:function(){return !!idle},hold:function(at){if(heldAt===null){heldAt=at||Date.now();persist();paint()}},
 resume:function(at){if(heldAt!==null){holdS+=Math.round(((at||Date.now())-heldAt)/1000);heldAt=null;persist();paint()}},
 adopt:function(a){start=a.startMin;holdS=Math.round(a.holdS||0);heldAt=a.heldAt||null;if(a.idle)idle=true;else if(a.startMin!=null)idle=false;persist();paint()},snap:function(){return{start:start,holdS:holdS,heldAt:heldAt,idle:!!idle}},onStart:null,onStop:null,onChange:null};
function base(){return (start===null?PLAN:start)+holdS/60}
function paint(){var st=base();
 rows.forEach(function(r){var off=+r.dataset.off,dur=+r.dataset.dur,s=st+off,e=s+dur,sm=r.querySelector('small');
  r.querySelector('b').textContent=fmt(s)+'\u2013'+fmt(e);r.dataset.range=fmt(s)+'\u2013'+fmt(e);
  r.dataset.flexTxt=r.dataset.stretch?('stretch to '+fmt(s+(+r.dataset.stretch))):'';if(!r.classList.contains('islive'))sm.textContent=r.dataset.flexTxt});
 $('ssind').textContent=(idle?'Stopped \u00B7 0:00':(start===null?'Planned start 8:00 AM':'Started '+fmtp(start)))+(heldAt!==null&&!idle?' \u00B7 HELD':'');
 b.setAttribute('aria-label',start===null||idle?'Set show start to now':'Show started '+fmtp(start)+'. Tap to set start to now again');
 live();if(api.onChange)api.onChange()}
function live(){var st=base(),n=ct(),nowS=n.h*3600+n.m*60+n.s,onDay=ctd.format(new Date())===SD,active=!idle&&(start!==null||onDay),hit=null,left=0,over=false;
 var el=nowS-st*60;if(heldAt!==null)el-=Math.floor((Date.now()-heldAt)/1000);if(FORCE!==null&&!idle){active=true;el=FORCE}if(idle){el=0;active=false}if(active){rows.forEach(function(r){var off=+r.dataset.off*60,dur=+r.dataset.dur*60;if(el>=off&&el<off+dur){hit=r;left=off+dur-el}});over=el>=3600}
 rows.forEach(function(r){var d=r.closest('details.sec,details.rd'),L=r===hit;r.classList.toggle('islive',L);if(d)d.classList.toggle('live',L);var tl=d&&d.querySelector('.tl');
  if(L){r.querySelector('small').textContent=(heldAt!==null?'HELD \u00B7 ':'LIVE \u00B7 ')+Math.floor(left/60)+':'+('0'+left%60).slice(-2)+' left'}else{r.querySelector('small').textContent=r.dataset.flexTxt||''}});
 [].forEach.call(document.querySelectorAll('.clock a'),function(a){a.classList.toggle('live',!!hit&&a.dataset.jump==='blk-'+hit.dataset.letter)});
 countdown(active,el,hit);playhead(active,el);
 $('sslive').textContent=hit?((heldAt!==null?'HELD: ':'LIVE: ')+hit.dataset.letter+' \u00B7 '+hit.dataset.name+' \u00B7 '+Math.floor(left/60)+':'+('0'+left%60).slice(-2)+' left'):(active&&over?'Show time is up (60 min).':'')}
function playhead(active,el){if(!TL||!segs.length)return;var T=0;segs.forEach(function(a){T+=+a.dataset.dur});T*=60;
 var e=active?el:0,p=Math.min(1,Math.max(0,e/T)),st=!active||e<0?'pre':e>=T?'post':'run';
 var cum=0,left=0,w=0;segs.forEach(function(a){var o=+a.dataset.off*60,d=+a.dataset.dur*60;a.classList.toggle('done',active&&e>=o+d)});
 TL.classList.toggle('pre',st==='pre');TL.dataset.state=st;TL.dataset.p=p.toFixed(4);TL.dataset.el=Math.round(e);
 var pc=p*100;PH.style.left=pc+'%';PH.dataset.pct=pc.toFixed(2);
 TL.setAttribute('aria-label','60 minute show timeline. '+(st==='run'?Math.floor(e/60)+' minutes in':st==='post'?'Show is over':'Show has not started'))}
var cn=$('cwnext');
function fmtt(t){t=Math.max(0,t);var h=Math.floor(t/3600),m=Math.floor(t%3600/60),s=t%60;return h?h+':'+('0'+m).slice(-2)+':'+('0'+s).slice(-2):m+':'+('0'+s).slice(-2)}
function countdown(active,el,hit){if(!cn)return;var T=rows.length?(+rows[rows.length-1].dataset.off+ +rows[rows.length-1].dataset.dur)*60:3600,lab='',chip='',nm='',col='',t=null,msg='';
 if(idle){msg='Stopped \u00B7 0:00'}
 else if(!active){msg=(SD>ctd.format(new Date()))?'Show: '+b.dataset.showlabel+' \u00B7 8:00 AM':'Show\u2019s over'}
 else if(el<0){lab='Show starts in';t=-el}
 else if(el>=T){msg='Show\u2019s over'}
 else{var i=rows.indexOf(hit);if(i>=0&&i<rows.length-1){var nx=rows[i+1];lab='Next:';chip=nx.dataset.letter;nm=nx.dataset.name;col=nx.dataset.color;t=+nx.dataset.off*60-el}else{lab='Show ends in';t=T-el}}
 var cls='cwn'+(t!==null&&t<15?' red':t!==null&&t<60?' amber':'');cn.className=cls;
 $('cwn-l').textContent=msg||lab;var c=$('cwn-c');c.textContent=chip;c.style.display=chip?'inline-block':'none';c.style.background=col||'';
 $('cwn-n').textContent=nm;$('cwn-t').textContent=t===null?'':(chip?'in ':'')+fmtt(t);
 cn.setAttribute('aria-label',(msg||lab)+' '+nm+' '+(t===null?'':fmtt(t)))}
b.onclick=function(){var n=ct();start=n.h*60+n.m;holdS=0;heldAt=null;idle=false;persist();paint();if(api.onStart)api.onStart();
 var t=document.getElementById('toast');if(t){t.textContent='Show start set to '+fmtp(start);t.className='on';setTimeout(function(){t.className=''},1800)}};
function openStop(){var d=$('stop-dlg');if(!d)return;if(d.showModal){try{d.showModal()}catch(e){d.setAttribute('open','')}}else d.setAttribute('open','')}
function closeStop(){var d=$('stop-dlg');if(!d)return;if(d.close){try{d.close()}catch(e){d.removeAttribute('open')}}else d.removeAttribute('open')}
function stopReset(){idle=true;start=null;holdS=0;heldAt=null;store.del(KEY);persist();
 rows.forEach(function(r){r.classList.remove('islive');var d=r.closest('details.sec,details.rd');if(d)d.classList.remove('live')});
 [].forEach.call(document.querySelectorAll('.clock a.live'),function(a){a.classList.remove('live')});
 var pill=$('mc-pill');if(pill){pill.textContent='STANDBY';pill.className='mcp stand'}
 paint();if(api.onStop)api.onStop();
 var t=document.getElementById('toast');if(t){t.textContent='Show stopped \u00B7 reset to 0:00';t.className='on';setTimeout(function(){t.className=''},1800)}}
if($('ssstop'))$('ssstop').onclick=openStop;
if($('ssreset'))$('ssreset').onclick=openStop;
if($('stop-go'))$('stop-go').onclick=function(){closeStop();stopReset()};
if($('stop-no'))$('stop-no').onclick=closeStop;
if($('stop-dlg'))$('stop-dlg').addEventListener('cancel',function(e){e.preventDefault();closeStop()});
paint();setInterval(live,1000);
})();
"""

BRK_JS = r"""
(function(){var s=document.getElementById('brk');if(!s)return;
var built=Date.parse(s.dataset.built)||0,POLL=(+s.dataset.poll||120)*1000,$=function(i){return document.getElementById(i)},
 list=$('brklist'),cnt=$('brkcount'),meta=$('brkmeta'),bdg=$('brkbadge'),bb=$('brkb'),showAll=false,more=false,data=null;
function feedUrl(){var p=location.pathname,i=p.indexOf('/packets/');return(i>=0?p.slice(0,i+1):p.replace(/[^\/]*$/,''))+'breaking.json'}
function ago(ms){var m=Math.round((Date.now()-ms)/60000);if(m<1)return'just now';if(m<60)return m+'m ago';return Math.floor(m/60)+'h '+(m%60)+'m ago'}
function safe(u){return/^https?:\/\//i.test(u||'')?u:''}
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
function capBrk(v,n){return String(v||'').replace(/[\u0000-\u001f\u007f-\u009f]+/g,' ').replace(/\s+/g,' ').trim().slice(0,n)}
function adhocId(title,url){var s=String(title||'')+'|'+String(url||''),h=2166136261;for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return 'a-'+('0000000000'+(h>>>0).toString(16)).slice(-10)}
function row(i,isNew){var r=el('div','brkrow'+(isNew?'':' old'));
 if(isNew)r.appendChild(el('span','nw','NEW'));
 var lab=el('span','sb '+(i.label==='Hot'?'h':i.label==='Trending'?'t':'a'),(i.level==='alert'?'ALERT ':'')+String(i.label||'').toUpperCase()+' '+i.score);r.appendChild(lab);
 if(i.uncovered){r.appendChild(el('span','sb u','UNCOVERED \u00B7 CONFIRM BEFORE AIR'))}
 var u=safe(i.url),a;if(u){a=el('a','',i.title);a.href=u;a.target='_blank';a.rel='noopener noreferrer'}else a=el('span','',i.title);r.appendChild(a);
 var n=(i.sources||[]).length;r.appendChild(el('span','src',(i.source||'')+(n>1?' +'+(n-1)+' more':'')+' \u00B7 '+ago(Date.parse(i.firstSeen)||0)));
 if(i.matches&&i.matches.length)r.appendChild(el('span','src','['+i.matches.slice(0,4).join(', ')+']'));
 var src=String(i.source||''),ttl=String(i.title||''),un=true; var hid=adhocId(ttl,i.url||''); var btn=el('button','chysend');btn.type='button';btn.setAttribute('data-chyid',hid); btn.setAttribute('data-chyh',capBrk(ttl,100));btn.setAttribute('data-chyl',(un?'UNCONFIRMED \u00B7 ':'')+capBrk(src,104));btn.setAttribute('data-chyk','BREAKING'); btn.setAttribute('aria-label','Send to chyron: '+ttl);btn.appendChild(el('span','ci','\u25B6'));btn.appendChild(el('span','ct','Chyron'));r.appendChild(btn);
 return r}
function render(){if(!data)return;var items=(data.items||[]),fresh=[],old=[];
 items.forEach(function(i){((Date.parse(i.firstSeen)||0)>built?fresh:old).push(i)});
 var anyAlert=fresh.some(function(i){return i.level==='alert'});
 cnt.textContent=fresh.length;cnt.className='pill'+(anyAlert?' new':fresh.length?' warn':'');
 bb.textContent=fresh.length;bdg.className='btnlike'+(anyAlert?' hot':'');
 var gen=Date.parse(data.generatedAt)||0;
 meta.textContent='checked '+ago(gen)+' \u00B7 '+(data.feeds?data.feeds.ok+'/'+data.feeds.total+' feeds':'')+(data.bootstrap?' \u00B7 warming up':'')+' \u00B7 page built '+ago(built)+' \u00B7 leads only, CONFIRM BEFORE AIR';
 list.textContent='';
 if(!fresh.length)list.appendChild(el('div','mut','Nothing new since this page was built.'));
 fresh.slice(0,showAll?fresh.length:5).forEach(function(i){list.appendChild(row(i,true))});
 if(fresh.length>5&&!showAll){var b=el('button','brkmore','Show all '+fresh.length+' new');b.type='button';b.onclick=function(){showAll=true;render()};list.appendChild(b)}
 if(old.length){if(!more){var b2=el('button','brkmore','Show earlier in the last 24h ('+old.length+')');b2.type='button';b2.onclick=function(){more=true;render()};list.appendChild(b2)}
  else old.slice(0,15).forEach(function(i){list.appendChild(row(i,false))})}}
function load(){if(location.protocol==='file:'){meta.textContent='Breaking feed needs the live site (this copy was opened from a file).';bb.textContent='\u2013';return}var c=window.AbortController?new AbortController():null,t=setTimeout(function(){c&&c.abort()},9000);
 fetch(feedUrl()+'?t='+Date.now(),{cache:'no-store',signal:c?c.signal:undefined}).then(function(r){clearTimeout(t);if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})
 .then(function(j){data=j;render()},function(e){clearTimeout(t);if(!data){meta.textContent='Breaking feed not reachable from here (offline, or this file is not on the live site).';bb.textContent='\u2013'}else meta.textContent='Could not refresh ('+(e&&e.message||'offline')+'); showing the last check '+ago(Date.parse(data.generatedAt)||0)})}
$('brkref').onclick=load;load();setInterval(load,POLL);setInterval(function(){if(data)render()},60000);window.ditmBrk={refresh:load,render:render};
})();
"""

import hashlib
UPTO_SEC = "What I've Been Up To"
# ---- "send to chyron": the dashboard sends only an id; the words live in docs/chyron-items.json (built here, with the packet)
CHY_ITEMS = {}
CHY_UNCONF = "UNCONFIRMED"
def chy_id(sec, title, url=""):
    return "i-" + hashlib.sha1(f"chy|{sec}|{title}|{url}".encode()).hexdigest()[:10]
def chy_trim(t, n):
    t = re.sub(r"https?://\S+", " ", str(t or ""))
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()
    if len(t) <= n:
        return t
    cut = t[:n - 1].rsplit(" ", 1)[0].rstrip(" ,;:-–—.")
    return (cut or t[:n - 1]) + "…"
def chy_line(tldr, fallback, unconf=False, n=118):
    first = re.split(r"(?<=[.!?])\s", re.sub(r"\s+", " ", str(tldr or "")).strip(), 1)[0]
    body = chy_trim(first or fallback, n - (len(CHY_UNCONF) + 3 if unconf else 0))
    return (CHY_UNCONF + (" · " + body if body else "")) if unconf else body
def chy_register(sec, title, url, tldr, fallback, unconf=False, kicker=""):
    hl = chy_trim(title, 100) or chy_trim(fallback, 100) or chy_trim(kicker or sec, 44) or "Item"
    cid = chy_id(sec, title or hl, url)
    CHY_ITEMS[cid] = {"headline": hl, "line": chy_line(tldr, fallback, unconf), "kicker": chy_trim((kicker or sec).replace(": ", " · ").upper(), 44)}
    return cid
def chy_btn(cid, title, on=""):
    return (f'<button class="chysend" type="button" data-chyid="{cid}" aria-pressed="false" aria-label="Send to chyron: {esc(title)}" title="Send to the on-air chyron (audible)">'
            f'<span class="ci">▶</span><span class="ct">Chyron</span></button>')

def use_btn(sec, title, url="", rmid=""):
    key = hashlib.sha1(f"{sec}|{url or title}".encode()).hexdigest()[:10]
    rm = f' data-rmid="{esc(rmid)}"' if rmid else ""
    label = "Mark as aired" if rmid else "Mark used on show"
    return (f'<button class="use" type="button" data-key="{key}" data-title="{esc(title)}" data-url="{esc(url)}" data-sec="{esc(sec)}"{rm} aria-pressed="false" '
            f'aria-label="{label}: {esc(title)}" title="{label}"><span class="ck"></span></button>')

def _by_score(lst):
    return sorted(lst, key=lambda it: (-(it.get("score") or 0), it.get("ord", 0)))



STORY_CATALOG = []

def catalog_entry(it, desk):
    """Facts already on the story. Never invents a synopsis or label."""
    if not isinstance(it, dict):
        return None
    title = it.get("title") or it.get("headline") or ""
    if not title:
        return None
    desk = desk or it.get("_desk") or ""
    rumor = bool((it.get("badge") and "RUMOR" in str(it.get("badge"))) or desk.lower() == "chisme" or it.get("_desk") == "chisme")
    kids = (isinstance(desk, str) and "family" in desk.lower()) or bool(is_family_kids_story(it))
    return {
        "id": it.get("_rmid") or story_remove_id(it),
        "title": title,
        "synopsis": story_synopsis(it),
        "url": it.get("url") or it.get("source_url") or _story_url(it) or "",
        "source": it.get("source") or "",
        "desk": desk,
        "date": it.get("_date_tag") or story_date_tag(it, it.get("_packet_date")),
        "confirm": bool(it.get("confirm") or it.get("isConfirm")),
        "rumor": rumor,
        "chisme": rumor or desk.lower() == "chisme",
        "kids": bool(kids),
    }

def build_story_catalog(week, seg):
    rows, seen = [], set()
    def add(it, desk):
        e = catalog_entry(it, desk)
        if not e or not e.get("id") or e["id"] in seen:
            return
        seen.add(e["id"]); rows.append(e)
    names = {"C": "Local News", "D": "Local Politics", "E": "School Boards", "F": "City Hall",
             "G": "Economic Development", "H": "Family & Kids", "I": "Statewide", "J": "The National Desk"}
    for letter, name in names.items():
        for it in (seg or {}).get(letter) or []:
            add(it, name)
    for it in (seg or {}).get("LIFE") or []:
        add(it, "Lifestyle")
    for it in (week or {}).get("chisme") or []:
        add(it, "Chisme")
    for key, label in (("national", "National"), ("trending", "Trending"), ("tech", "Tech"),
                       ("rgv", "Local News"), ("texas", "Statewide")):
        for it in (week or {}).get(key) or []:
            add(it, label)
    return rows

def post_show_html(data, catalog, standalone=True):
    """Self-contained recap page. Reads aired ids from localStorage; does not invent facts or post."""
    m = (data or {}).get("meta") or {}
    date = m.get("date") or m.get("showDate") or ""
    logo = ""
    try:
        logo = b64(asset("assets/DITM_SunLogo.png"), "image/png")
    except Exception:
        logo = ""
    cat = json.dumps(catalog or [], ensure_ascii=False).replace("<", "\\u003c")
    css = (
        "body{margin:0;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;"
        "background:#f6f1e8;color:#1b2430;line-height:1.4}"
        " .ps-wrap{max-width:52rem;margin:0 auto;padding:16px 16px 48px}"
        " .ps-brand{display:flex;gap:12px;align-items:center;margin:0 0 16px}"
        " .ps-brand img{width:72px;height:auto}"
        " h1{margin:.2rem 0 0} .ps-date{font-weight:800}"
        " .ps-acts{display:flex;flex-wrap:wrap;gap:8px} .ps-acts button,.ps-copy{min-height:44px;padding:0 14px;border-radius:8px;font:inherit;font-weight:800;cursor:pointer;border:1.5px solid #1b2430;background:#fff}"
        " .ps-story{border:1.5px solid #1b2430;border-radius:10px;padding:10px 12px;margin:0 0 12px;background:#fff}"
        " .ps-syn{line-height:1.4} .ps-d pre{white-space:pre-wrap;margin:6px 0 0;padding:8px;border-radius:8px;background:#f6f1e8;border:1px solid #1b2430;font:inherit}"
        " .cf{background:#c1121f;color:#fff;font-size:.75rem;font-weight:800;border-radius:4px;padding:0 5px;margin-left:4px}"
        " .mut{color:#5c6b7a} a{color:#0b5cad} @media print{.ps-acts,.ps-copy{display:none!important}}"
    )
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data: https:; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; connect-src \'none\'">'
        f'<title>Post-show recap · Drew in the Morning</title><style>{css}</style></head>'
        f'<body data-showdate="{esc(date)}"><div class="ps-wrap"><div class="ps-brand">'
        f'{("<img src=\""+logo+"\" alt=\"Drew in the Morning\">") if logo else ""}'
        f'<div><p class="ps-k">Post-show recap</p></div></div><div id="ps-root"></div></div>'
        f'<script type="application/json" id="ditm-stories">{cat}</script>'
        f'<script>window.DITM_SHOW={{date:{json.dumps(date)}}};</script>'
        f'<script>{POSTSHOW_JS}</script></body></html>'
    )

def studio_html(data, archive_href=None):
    CHY_ITEMS.clear()
    data = dict(data)
    if data.get("scoring"):   # the dashboard shows the highest-scoring stories first (a button flips to editorial order)
        data["headlines"] = dict(data["headlines"], rgv=_by_score(data["headlines"]["rgv"]), texas=_by_score(data["headlines"]["texas"]))
        data["nationalDesk"] = _by_score(data["nationalDesk"]); data["trending"] = _by_score(data.get("trending") or [])
    m, w = data["meta"], data["weather"]
    logo = b64(asset("assets/DITM_SunLogo.png"), "image/png")
    A = lambda url, text, extra="": f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer" {extra}>{esc(text)}</a>'
    CP = lambda url, label="Copy link": f'<button class="cp" type="button" data-url="{esc(url)}" title="{label}" aria-label="{label}">{label}</button>'
    def item(it, text=None, sec="", use=True):
        conf = f' <span class="cf">CONFIRM BEFORE AIR</span> <span class="src">{esc(conf_text(it))}</span>' if it.get("confirm") else ""
        url = it.get("url") or ""
        title = text or it["title"]
        main = A(url, title) if url else esc(title)
        cid = chy_register(sec or "Show", title, url, "", it.get("source", ""), unconf=bool(it.get("confirm")))
        acts = (CP(url) if url else "") + chy_btn(cid, title) + (use_btn(sec, it["title"], url) if use and sec else "")
        hay = " ".join(x for x in (title, it.get("source",""), sec) if x)
        return (f'<div class="item" data-ord="{it.get("ord", 0)}" data-sc="{it.get("score", 0)}" data-chyid="{cid}" data-chyh="{esc(chy_trim(title, 100))}" data-q="{esc(hay)}"><div class="tx">{main} <span class="src">{esc(it.get("source",""))}</span>{sc_studio(it)}<span class="upill">USED</span>{conf}</div><div class="acts">{acts}</div></div>')
    def linkrow(l):
        cid = chy_register("Links", l["label"], l["url"], "", l["label"])
        return f'<div class="item" data-chyid="{cid}" data-chyh="{esc(chy_trim(l["label"], 100))}" data-q="{esc(l["label"])}"><div class="tx">{A(l["url"], l["label"])}</div><div class="acts">{CP(l["url"])}{chy_btn(cid, l["label"])}</div></div>'
    def sec(id_, color, title, sub, body, wide=False, open_=False, fg="", count="", badges="", chip="", tr="", blk=False):
        # every section starts collapsed (open_ is kept only so old calls still work); STUDIO_JS restores the session's state
        chip_h = f'<span class="bl2">{chip}</span>' if chip else ""
        cnt_h = f'<span class="cnt" id="cnt-{id_}">{esc(count)}</span>' if count != "" else ""
        ptitle = html.unescape(re.sub(r"<[^>]+>", "", title)).replace("LIVE", "").strip()
        return (f'<details class="sec{" blk" if blk else ""}" id="{id_}"><summary style="background:{color};{fg}" title="{esc(ptitle)}"><span class="st">{chip_h}<span class="tt"><span class="tn">{title}</span><small>{sub}</small></span></span>'
                f'<span class="sm">{cnt_h}{badges}{tr}</span></summary><div class="body">{body}</div></details>')
    clock = data.get("showClock", [])
    _off = [sum(x["minutes"] for x in clock[:i]) for i in range(len(clock))]
    clockbar = "".join(f'<a href="#blk-{c["letter"]}" data-jump="blk-{c["letter"]}" data-off="{_off[i]}" data-dur="{c["minutes"]}" data-letter="{c["letter"]}" style="width:{c["minutes"]/60*100:.3f}%;background:{c["color"]}" title="{esc(c["title"])} · {c["timeRange"]}">{c["letter"]}{"★" if c["signature"] else ""}<small>{c["minutes"]}m</small></a>' for i, c in enumerate(clock))
    thumb = data["headlines"].get("image")
    thumbhtml = f'<div class="thumbrow"><img src="{b64(asset(thumb["file"]), "image/jpeg")}" alt="Starship file photo" loading="lazy" decoding="async"><div class="src">{esc(thumb["caption"])} · {A(thumb["credit_url"], "source")}</div></div>' if thumb else ""
    # ================= v3 body: every section is a full-width bar that opens into Trending-model cards =================
    TZC = datetime.timezone(datetime.timedelta(hours=-6))
    def tcard(title, url="", pills=(), meta="", tldr="", riff="", riff_label="Riff", score="", conf="", extra="", sec_="", ord_=None, sc=0, copy_text="", use=True, uid="", cls="", badges="", chy_unconf=False, chy_fallback=None, rmid="", when=0, date_tag=""):
        """THE card (Trending News model): headline, meta line (source / date / score / badges), TL;DR, Riff, then link + copy + used.
        Any field that has no data is left out cleanly; nothing is invented to fill a slot."""
        head = A(url, title) if url else esc(title)
        pl = "".join(f'<span class="pill"{(" style=background:" + c) if c else ""}>{esc(p)}</span>' for p, c in ((x if isinstance(x, tuple) else (x, "")) for x in pills if x))
        cf = ' <span class="cf">CONFIRM BEFORE AIR</span>' if conf else ""
        tag = f'<span class="dtg">{esc(date_tag)}</span>' if date_tag else ""
        mt = f'<span class="src">{esc(meta)}</span>' if meta else ""
        summary = tldr or ""
        td = f'<p class="tldr">{esc(summary)}</p>' if summary else ""
        riff_txt = re.sub(r"<[^>]+>", " ", riff) if riff.startswith("<") else riff
        rf = f'<p class="ang"><b>{esc(riff_label)}:</b> {esc(riff_txt)}</p>' if riff_txt.strip() else ""
        ct = copy_text or url or (title + (" " + tldr if tldr else ""))
        fb = chy_fallback if chy_fallback is not None else meta
        cid = chy_register(sec_ or "Show", title, url, tldr, fb, unconf=bool(conf) or chy_unconf)
        hl = CHY_ITEMS[cid]["headline"]
        acts = CP(ct, "Copy link" if url and not copy_text else "Copy") + chy_btn(cid, hl) + (use_btn(sec_, title, url, rmid) if (use and sec_) else "")
        pills_txt = " ".join((x[0] if isinstance(x, tuple) else x) for x in pills if x)
        hay = " ".join(x for x in (title, meta, tldr, riff_txt, conf, sec_, pills_txt) if x)
        attrs = (f' data-ord="{ord_}" data-sc="{sc}"' if ord_ is not None else "") + (f' id="{uid}"' if uid else "") + (f' data-rmid="{esc(rmid)}"' if rmid else "") + (f' data-when="{int(when)}"' if when else "") + f' data-chyid="{cid}" data-chyh="{esc(hl)}" data-q="{esc(hay)}"'
        rmx = (f'<button type="button" class="rmx" data-rmid="{esc(rmid)}" aria-label="Remove story" title="Remove story">×</button>' if rmid else "")
        return (f'<div class="item trn tc{(" " + cls) if cls else ""}"{attrs}>{rmx}<div class="tx"><b class="hd">{head}</b><div class="meta">{pl}{tag}{mt}{score}{badges}<span class="upill">USED</span><span class="apill">AIRED</span><span class="xpill">EXPIRED</span> <button type="button" class="sd-restore">Restore</button>{cf}</div>{td}{rf}{extra}</div><div class="acts">{acts}</div></div>')
    def grid(cards, empty=""):
        return '<div class="sortbox">' + ("".join(cards) or f'<p class="mut noev">{esc(empty)}</p>') + "</div>"
    def lks_of(links):
        return "".join(linkrow(l) for l in links or [] if str(l.get("url", "")).startswith("http"))
    def dtl(iso):
        try:
            return datetime.datetime.fromisoformat(iso).astimezone(TZC).strftime("%b %-d, %-I:%M %p CT")
        except Exception:
            return ""

    # ---- top headlines (RGV first, then Texas)
    def news_bits(i):
        pkt_day = i.get("_packet_date") or ((data.get("meta") or {}).get("date"))
        when = i.get("_when") or 0
        if not when:
            dt = story_when(i, pkt_day)
            when = int(dt.timestamp()) if dt else 0
        return dict(rmid=i.get("_rmid") or story_remove_id(i), when=when, date_tag=i.get("_date_tag") or story_date_tag(i, pkt_day))
    def hcard(i, sec_):
        pubs = ""
        return tcard(i["title"], i.get("url", "") or _story_url(i), pills=(("VALLEY", "#2a7de1"),) if i.get("valley") else (), meta=i.get("source", "") + ((" · " + dtl(i["published"])) if i.get("published") else ""), tldr=story_synopsis(i),
                     score=sc_studio(i), conf=conf_text(i) if i.get("confirm") else "", sec_=sec_, ord_=i.get("ord", 0), sc=i.get("score", 0), **news_bits(i))

    # ---- rolling 7-day news window (today + prior packets on disk; email/print still use today's data only)
    week = merge_week_news(data, os.path.join(HERE, ".."), data["meta"]["date"])
    data["_week"] = {"found": [d.isoformat() for d in week["found"]], "missing": [d.isoformat() for d in week["missing"]],
                     "window": [week["window"][0].isoformat(), week["window"][1].isoformat()],
                     "counts": {k: len(week[k]) for k in ("rgv", "texas", "national", "trending", "tech", "chisme")}}
    if OPTS.get("enrich_synopses"):
        enrich_synopses([it for k in ("rgv", "texas", "national", "trending", "tech", "chisme") for it in (week.get(k) or [])])

    # ---- chisme
    ch = data.get("chisme") or {}
    chi = week["chisme"]
    def chcard(c, k):
        mt = c.get("metrics") or {}
        eng = c.get("engagement")
        score = (f'<span class="sb a" title="{esc(" · ".join(f"{a} {b}" for a, b in mt.items()))}">{"▲ " + format(eng, ",") if eng is not None else "no counts"}</span>')
        cb = c.get("confirmedBy")
        badge = (f'<span class="sb t" title="{esc(cb["url"])}">CONFIRMED · {esc(cb["outlet"])}</span>' if cb else f'<span class="cf">{esc(c.get("badge") or CHISME_BADGE)}</span>')
        when = dtl(c.get("published", ""))
        return tcard(c["title"], c.get("url") or _story_url(c), pills=(c.get("platform", ""), c.get("source", "")), meta=when, tldr=story_synopsis(c), riff=c.get("riff", ""), score=score, badges=badge,
                     sec_="Chisme", ord_=k, sc=eng or 0, cls="chisme", chy_unconf=not c.get("confirmedBy"), chy_fallback=" · ".join(x for x in (c.get("platform", ""), when) if x), **news_bits(c))
    src_status = ch.get("sources") or {}
    ok_src = [f'{k.split(":")[0]} {v["items"]}' for k, v in src_status.items() if v.get("ok")]
    bad_src = sorted({k.split(":")[0].split("/")[0].replace("r", "reddit", 1) if k.startswith("r/") else k.split(":")[0] for k, v in src_status.items() if not v.get("ok")})
    chnote = ('<p class="mut"><span class="cf">' + esc(CHISME_BADGE) + '</span> Local social buzz from the last 72 hours (Reddit, Facebook, Instagram and similar). It is all rumor until a news outlet confirms it: '
              'tease it as "people are talking about…" and never state it as fact. No private people named in anything negative, nothing about kids, no addresses or personal details. '
              f'Read today: {esc(", ".join(ok_src) or "nothing")}.' + (f' Not available: {esc(", ".join(bad_src))} (login-walled or blocked; skipped, never faked).' if bad_src else "") + '</p>')
    chisme_h = chnote + grid([chcard(c, k) for k, c in enumerate(chi)], "No chisme loaded today: no Valley social post passed the safety filter in the last 72 hours, or the sources could not be read. Nothing is made up to fill this section.")

    # ---- pull Family & Kids / Lifestyle items out of every desk (one story, one home)
    _meme_flat = []
    for lv in (data.get("memes") or {}).get("levels") or []:
        for it in lv.get("items") or []:
            _meme_flat.append(_normalize_story(it, "meme", {"source": "Meme of the Week · " + (lv.get("level") or ""), "short": it.get("what") or it.get("title") or ""}))
    seg = assign_segment_stories(week["rgv"], week["texas"],
                                 national=week["national"], trending=week["trending"],
                                 tech=week["tech"], memes=_meme_flat)
    global STORY_CATALOG
    STORY_CATALOG = build_story_catalog(week, seg)
    data["_story_catalog"] = STORY_CATALOG
    _moved = {_story_key(i) for i in (seg.get("H") or []) + (seg.get("LIFE") or [])
              if i.get("_desk") in ("national", "trending", "tech", "meme")}

    # ---- national desk
    def ncard(n, k_):
        valley = f'<p class="ang"><b>Valley angle:</b> {esc(n["valley"])}</p>' if n.get("valley") else ""
        u = n["links"][0]["url"] if n.get("links") else ""
        return tcard(n["title"], u, meta="National Desk", tldr=story_synopsis(n), riff=n.get("angle", ""), score=sc_studio(n), conf=conf_text(n) if n.get("confirm") else "",
                     extra=valley, sec_="National Desk", ord_=n.get("ord", k_), sc=n.get("score", 0), uid=f"nat-{k_}", **news_bits(n))
    _nat_keep = [n for n in week["national"] if _story_key(n) not in _moved]
    nat = grid([ncard(n, k_) for k_, n in enumerate(_nat_keep)], "No National Desk stories loaded.")
    # ---- trending news
    def trcard(t, k_):
        c = trend_item_conf(t)
        media = f'<div class="src">Video: {A(t["video_url"], "watch")}{(" · credit: " + esc(t["image_credit"])) if t.get("image_credit") else ""}</div>' if t.get("video_url") else ""
        when = ((" · " + dtl(t["published"])) if t.get("published") else "")
        return tcard(t["title"], t.get("source_url", "") or _story_url(t), pills=(t.get("category", ""),), meta=(t.get("source", "") + when), tldr=story_synopsis(t), score=sc_studio(t), conf=c or "",
                     extra=media, sec_="Trending", ord_=t.get("ord", 0), sc=t.get("score", 0), **news_bits(t))
    _tr_keep = [t for t in week["trending"] if _story_key(t) not in _moved]
    trn = '<p class="mut">What\'s trending around the nation. Separate from the National Desk (no duplicates). Source order: X trends/news, AP/Reuters, Google Trends, YouTube trending.</p>' + grid([trcard(t, k_) for k_, t in enumerate(_tr_keep)], "No trending items loaded.")
    # ---- tech
    tk = data["tech"]
    def tkcard(t, k_):
        return tcard(t["title"], t.get("source_url", "") or _story_url(t), pills=("TECH",), meta=" · ".join(x for x in (t.get("source", ""), t.get("published", "")) if x), tldr=story_synopsis(t),
                     badges=f'<span class="sb {"a" if tk["origin"] == "wires" else "t"}" title="{esc(tk["originLabel"])}">{esc(t.get("basis") or tk.get("badge") or "")}</span>', conf=t["confirm"] if t.get("confirm") else "",
                     sec_="Tech", ord_=k_, sc=0, **news_bits(t))
    _tech_keep = [t for t in week["tech"] if _story_key(t) not in _moved]
    tech_h = (f'<p class="mut"><b>{esc(tk["badge"])}</b> · {esc(tk["originLabel"])}</p>' + (f'<p class="mut">{esc(tk["note"])}</p>' if tk.get("note") else "")
              + grid([tkcard(t, k_) for k_, t in enumerate(_tech_keep)], "No tech items loaded today."))

    # ---- obituaries: compact cards, the newest 7 days up front, the week before behind one button
    ob = data["obituaries"]
    grps = ob["groups"]
    def ocard(r):
        bits = [x for x in ((f'{r["age"]}' if r.get("age") else ""), r.get("city") or "", fmt_day(r["published"])) if x]
        cid = chy_register("Remembering Our Neighbors", f'Remembering {r["name"]}', r["url"], "", " · ".join(bits), kicker="Remembering our neighbors")   # name, age, town, date only; never a cause of death
        hay = " ".join(x for x in ("Remembering", r["name"], *bits, "obituaries", "neighbors") if x)
        return (f'<div class="ob" data-chyid="{cid}" data-chyh="{esc(chy_trim("Remembering " + r["name"], 100))}" data-q="{esc(hay)}"><div class="obn"><a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">{esc(r["name"])}</a></div><span class="obm">{esc(" · ".join(bits))}</span><div class="acts">{chy_btn(cid, "Remembering " + r["name"])}</div></div>')
    n_week = len(grps[0]["items"]) if grps else 0
    n_prev = sum(len(g["items"]) for g in grps[1:])
    if ob["count"]:
        obit_h = (f'<p class="mut">Obituaries The Monitor ran on Legacy.com, {esc(ob["windowLabel"])}. Names, ages and towns only.</p>')
        if grps:
            obit_h += f'<h3 class="obh">This week · {esc(grps[0]["label"])} <span class="mut">({n_week})</span></h3><div class="obgrid" id="obnew">{"".join(ocard(r) for r in grps[0]["items"])}</div>'
        if n_prev:
            lab = " · ".join(g["label"] for g in grps[1:])
            obit_h += (f'<button class="obmore" id="obmore" type="button" aria-expanded="false" aria-controls="obprev" data-more="Show the previous week ({n_prev})" data-less="Hide the previous week ({n_prev})">Show the previous week ({n_prev})</button>'
                       f'<div id="obprev" class="obprev" hidden><h3 class="obh">The week before · {esc(lab)} <span class="mut">({n_prev})</span></h3><div class="obgrid">{"".join(ocard(r) for g in grps[1:] for r in g["items"])}</div></div>')
    else:
        obit_h = '<p class="mut">No obituaries loaded today.</p>'
    ob_count = (f'{n_week} this week · {ob["count"]} in 2 weeks' if n_prev else f'{ob["count"]} this week') if ob["count"] else "0 obituaries"

    # ---- weather
    upd = datetime.datetime.fromisoformat(w["updated"].replace("Z", "+00:00")).astimezone(TZC)
    alerts = "No active NWS alerts." if w.get("alerts") == [] else ("Alerts: " + ", ".join(w["alerts"]) if w.get("alerts") else "")
    wcards = []
    for d in w["days"][:7]:
        wcards.append(tcard(f'{d["label"]} {d["dateLabel"]}', "", pills=(("MONDAY SHOW", "#e4572e"),) if d["date"] == w["monday"] else (), meta=f'{d["hi"]}° / {d["lo"] if d["lo"] is not None else "–"}° · {d["pop"]}% rain',
                            tldr=d["short"], extra=f'<div class="wico">{icon(d["icon"], 40)}</div>', use=False, copy_text=f'{d["label"]} {d["dateLabel"]}: {d["hi"]}°, {d["short"]}', cls="wx"))
    weather = (f'<p class="mut">{esc(alerts)} Updated {upd.strftime("%b %-d %-I:%M %p")} CT. Source: {esc(w["source"])}.</p>' + grid(wcards))
    # ---- sports
    hs = data["sports"]["highSchool"]
    sl, nl, nores, nonext = hs_texts(hs)
    def scard(i, sec_, pill):
        return tcard(i["title"], i.get("url", ""), pills=(pill,), meta=i.get("source", ""), tldr=i.get("tldr") or "", riff=i.get("riff") or "", sec_=sec_, conf=conf_text(i) if i.get("confirm") else "")
    hs_cards = [scard(r, "HS football", "FINAL") for r in hs["results"]] + [scard(r, "HS football", "NEXT") for r in hs["next"]] + [scard(hs["college"], "HS football", "COLLEGE")]
    hsb = f'<p class="mut">{esc(hs["sourceNote"])} · {esc(sl.capitalize())}; {esc(nl)}.</p>' + grid(hs_cards, nores)
    def scorebox(g, pill):
        s = data["sports"][g]
        sc = [tcard(b, "", pills=("FINAL",), meta=a, use=False, copy_text=f"{b} ({a})") for a, b in s["scores"]]
        if g == "nba": sc += [tcard(b, "", pills=("TEXAS",), meta=a, use=False, copy_text=f"{b} ({a})") for a, b in s["texas"]]
        sc += [scard(n, g.upper(), "NOTABLE") for n in s["notable"]]
        return grid(sc, f"No {g.upper()} games in this window.")
    mlb = data["sports"]["mlb"]
    sports_nfl = scorebox("nfl", "NFL"); sports_nba = scorebox("nba", "NBA")
    sports_mlb = f'<p class="mut"><i>{esc(mlb["note"])}</i></p>' + grid([scard(n, "MLB", "HOT STOVE") for n in mlb["notable"]], "No MLB items.")
    # ---- meme of the week
    colors = {"Elementary": "#2a9d8f", "Middle School": "#8e6bbf", "High School": "#e76f51"}
    mcards = []
    for lv in data["memes"]["levels"]:
        for it in lv["items"]:
            if _story_key(it) in _moved:
                continue
            is_motw = it["id"] == data["memes"].get("memeOfTheWeek")
            mcards.append(tcard(it["title"], (it["links"][0]["url"] if it["links"] else ""), pills=((lv["level"], colors.get(lv["level"], "#888")),) + ((("MEME OF THE WEEK", "#c1121f"),) if is_motw else ()), meta=lv["icon"] + " for parents",
                                tldr=(it["what"] + " " + it["means"]).strip(), conf=conf_text(it) if it.get("confirm") else "",
                                sec_="Meme of the Week: " + lv["level"], cls="meme"))
    mem = f'<p class="mut"><b>{esc(data["memes"]["tagline"])}</b> {esc(data["memes"]["intro"])}</p>' + grid(mcards, "No memes loaded.")

    # ---- run-of-show blocks A..L: one section per letter; story grids live on the same bar as the timer
    SUBS = {"A": "jingle · cold open · the hour's promise", "B": "family calendar · look-ahead", "C": "top Valley stories · headlines · chisme", "D": "races, candidates and runoffs",
            "E": "trustees, budgets and board votes", "F": "mayors, councils and city managers", "G": "jobs, projects and deals", "H": "stories for kids, teens (6–18) and parents",
            "I": "Texas and Texas politics", "J": "national desk · trending · tech", "K": "call-ins and topic submissions", "L": "meme of the week · close"}
    byL = {r["letter"]: r for r in data.get("rundown") or []}
    b_cards = []
    for e in data["up_to"] + [dict(x, coming=True) for x in data["up_to_coming"]]:
        dd = datetime.date.fromisoformat(e["date"]).strftime("%a %b %-d")
        b_cards.append(tcard(e["label"], "", pills=(e["category"],) + (("COMING UP", "#2a7de1"),) if e.get("coming") else (e["category"],),
                             meta=dd + (f' · {upto_when(e)}' if e["count"] > 1 else ""), sec_=UPTO_SEC, cls="ev" + (" ahead" if e.get("coming") else "")))
    def blk(L, body, count="", badges=""):
        r = byL[L]
        stretch = f' data-stretch="{r["stretchTo"]}"' if r["flex"] and r.get("stretchTo") else ""
        tr = (f'<span class="tr" data-off="{r["offset"]}" data-dur="{r["minutes"]}"{stretch} data-letter="{L}" data-name="{esc(r["short"])}" data-color="{r["color"]}"><b>{r["timeRange"]}</b><small></small></span>')
        title = esc(r["title"]) + (" ★" if r["signature"] else "") + '<span class="tl">LIVE</span>'
        sub = esc(r.get("subject") or SUBS.get(L, ""))
        return sec(f"blk-{L}", r["color"], title, sub, body, count=count, chip=L, tr=tr, blk=True,
                   badges=plus_confirm(badges, len(r.get("confirm") or [])))
    def stories_of(L, sec_name, empty="No stories today."):
        items = seg.get(L) or []
        n, bdg = sc_agg(items)
        return grid([hcard(i, sec_name) for i in items], empty), (f"{n} stories" if n else "No stories today"), bdg, n
    nav = "".join(f'<a href="#{i}" data-jump="{i}">{t}</a>' for i, t in (("brk", "Breaking"), ("blk-A", "Cold open"), ("blk-B", "Up To"), ("blk-C", "Local News"), ("chisme", "Chisme"),
                                                                       ("blk-D", "Local Politics"), ("blk-E", "School Boards"), ("blk-F", "City Hall"), ("blk-G", "Econ Dev"), ("blk-H", "Family & Kids"), ("blk-I", "Statewide"),
                                                                       ("blk-J", "National"), ("trending", "Trending"), ("tech", "Tech"), ("lifestyle", "Lifestyle"), ("obits", "Neighbors"), ("memes", "Meme of the Week"),
                                                                       ("weather", "Weather"), ("hs", "HS Football"), ("nfl", "NFL"), ("nba", "NBA"), ("mlb", "MLB"), ("used", "Used list"), ("aired", "Aired"), ("expired", "Expired"), ("post-show", "Post-show")))
    mon = m["mode"] == "monday"
    used_body = ('<ul id="usedul"></ul><p class="mut">Tap the box next to any item when it is used on the show. Marks stay on this device until cleared, so nothing gets repeated. '
                 '"Log to repo" opens a pre-filled GitHub issue (label used-on-show) for the post-show job: it cuts clips from the recording and drafts social teasers for approval. Nothing posts by itself.</p>')
    nh, bh = sc_agg(data["headlines"]["rgv"] + data["headlines"]["texas"])
    nt_, bt_ = sc_agg(_tr_keep)
    nn_, bn_ = sc_agg(_nat_keep)
    nm_ = len(mcards)
    cfm = sum(1 for lv in data["memes"]["levels"] for it in lv["items"] if it.get("confirm") and _story_key(it) not in _moved)
    n_nfl = len(data["sports"]["nfl"]["scores"]) + len(data["sports"]["nfl"]["notable"])
    n_nba = len(data["sports"]["nba"]["scores"]) + len(data["sports"]["nba"]["notable"])
    n_hs = len(hs["results"]) + len(hs["next"])
    wal = w.get("alerts")
    wb = ('<span class="cf">' + str(len(wal)) + ' ALERT' + ('S' if len(wal) != 1 else '') + '</span>') if wal else ""
    n_rumor = sum(1 for c in chi if not c.get("confirmedBy"))
    # C uses leftover local headlines (stories that belong in D–I have been moved) plus Chisme
    c_rgv = [i for i in seg["C"] if i.get("_desk") == "rgv"]
    c_tx = [i for i in seg["C"] if i.get("_desk") == "texas"]
    heads = (thumbhtml
             + (('<div class="src" style="font-weight:800">RGV</div>' + grid([hcard(i, "Headlines: RGV") for i in c_rgv], "No RGV headlines loaded.")) if c_rgv or not c_tx else "")
             + (('<div class="src" style="margin-top:10px;font-weight:800">TEXAS</div>' + grid([hcard(i, "Headlines: Texas") for i in c_tx], "No Texas headlines loaded.")) if c_tx else ""))
    c_body = f'<div class="subsec" id="headlines">{heads}</div><h3 class="subh" id="chisme">Chisme</h3>{chisme_h}'
    c_count = f"{len(seg['C']) + len(chi)} stories"
    c_badges = plus_confirm(sc_agg(seg["C"])[1], 0) + (f'<span class="cf">{n_rumor} RUMOR</span>' if n_rumor else "")
    d_grid, d_cnt, d_bdg, _ = stories_of("D", "Local Politics")
    e_grid, e_cnt, e_bdg, _ = stories_of("E", "School Boards")
    f_grid, f_cnt, f_bdg, _ = stories_of("F", "City Hall")
    g_grid, g_cnt, g_bdg, _ = stories_of("G", "Economic Development")
    h_grid, h_cnt, h_bdg, _ = stories_of("H", "Family & Kids")
    i_grid, i_cnt, i_bdg, _ = stories_of("I", "Statewide")
    n_tech_cf = sum(1 for x in _tech_keep if x.get("isConfirm"))
    j_body = (f'<div class="subsec" id="national">{nat}</div>'
              f'<h3 class="subh" id="trending">Trending News</h3>{trn}'
              '<h3 class="subh" id="tech">What\'s Happening in Tech</h3>' + tech_h)
    j_count = f"{nn_ + nt_ + len(_tech_keep)} stories"
    j_badges = bn_ + bt_ + (f'<span class="sb {"a" if tk["origin"] == "wires" else "t"}">{esc(tk["badge"])}</span>' if tk.get("badge") else "") + (f'<span class="cf">{n_tech_cf} CONFIRM</span>' if n_tech_cf else "")
    life_items = seg.get("LIFE") or []
    life_extra = (('<h3 class="subh" id="life-honors">Weddings, births &amp; honors</h3>' + grid([hcard(i, "Lifestyle") for i in life_items], "No honors today."))
                  if life_items else '<p class="mut">No marriages, births, or student honors in today\'s sources.</p>')
    life_body = f'{life_extra}<div class="subsec" id="obits">{obit_h}</div>'
    life_count = (f"{len(life_items)} honors · {ob_count}" if life_items else ob_count)
    l_body = f'<div class="subsec" id="memes">{mem}</div>'
    l_count = (f"{nm_} memes" if nm_ else "No memes today")
    l_badges = (f'<span class="cf">{cfm} CONFIRM</span>' if cfm else "")
    def maybe(L, *a, **k):
        return blk(L, *a, **k) if L in byL else ""
    body = "".join([
        maybe("A", "", count=""),
        maybe("B", grid(b_cards, "No look-ahead items today."), count=(f"{len(b_cards)} events" if b_cards else "No events")),
        maybe("C", c_body, count=c_count, badges=c_badges),
        maybe("D", d_grid, count=d_cnt, badges=d_bdg),
        maybe("E", e_grid, count=e_cnt, badges=e_bdg),
        maybe("F", f_grid, count=f_cnt, badges=f_bdg),
        maybe("G", g_grid, count=g_cnt, badges=g_bdg),
        maybe("H", h_grid, count=h_cnt, badges=h_bdg),
        maybe("I", i_grid, count=i_cnt, badges=i_bdg),
        maybe("J", j_body, count=j_count, badges=j_badges),
        maybe("K", "", count=""),
        sec("lifestyle", "#5c6b7a", "Lifestyle", "marriages · births · neighbors · student honors", life_body, count=life_count),
        maybe("L", l_body, count=l_count, badges=l_badges),
        sec("weather", "#2a7de1", "McAllen / RGV Weather", w["source"], weather, count="7 days", badges=wb),
        sec("hs", "#2a9d8f", "RGV High School Football", hs["round"], hsb, count=f"{n_hs} games"),
        sec("nfl", "#264653", esc(sport_title(data["sports"]["nfl"], False).replace("NFL ", "NFL · ", 1)), "scores + notable", sports_nfl, count=f"{n_nfl} items"),
        sec("nba", "#c1121f", "NBA", esc((data["sports"]["nba"].get("window", "") + " + Texas teams").strip(" +")), sports_nba, count=f"{n_nba} items"),
        sec("mlb", "#003f88", "MLB · Offseason", "no scores · hot stove", sports_mlb, count=f'{len(mlb["notable"])} items'),
        sec("used", "#1f9d55", "Used on Show", "running list · no repeats", used_body, count="0 used"),
        sec("aired", "#1f9d55", "Aired", "ticked off during the show — individually restorable", '<div class="sortbox" id="aired-box"></div>', count="None yet"),
        sec("expired", "#5c6b7a", "Expired", "on the board but not ticked, after Show's done — individually restorable", '<div class="sortbox" id="expired-box"></div>', count="None yet")])
    segs = "".join(f"<li>{esc(s)}</li>" for s in data.get("segues", []))
    nowc = w.get("now") or {}
    bt = nowc.get("tempF"); bsrc = nowc.get("source", "forecast")
    if bt is None and w.get("days"):
        td = next((x for x in w["days"] if x["date"] == m["date"]), w["days"][0]); bt, nowc, bsrc = td["hi"], {"cond": td["short"], "at": w["updated"]}, "forecast high"
    bat = ""
    if nowc.get("at"):
        bat = datetime.datetime.fromisoformat(nowc["at"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=-6))).strftime("%-I:%M %p") + " CT"
    clockw = (f'<div id="clockw" aria-label="Current time in McAllen, Texas" data-obs="https://api.weather.gov/stations/KMFE/observations/latest" data-hourly="{esc(w["apiUrl"])}/hourly" '
              f'data-build-temp="{"" if bt is None else bt}" data-build-cond="{esc(nowc.get("cond", ""))}" data-build-at="{esc(bat)}" data-build-src="{esc(bsrc)}" data-state="build">'
              f'<div id="cw-time">--:--:-- --</div><div class="cwd"><span id="cw-dow"></span> · <span id="cw-date"></span></div>'
              f'<div class="cwx"><span id="cw-ico" aria-hidden="true"></span><b id="cw-temp">--°F</b><span id="cw-cond"></span><small id="cw-note">as of build</small></div>'
              f'<div id="cwnext" class="cwn" aria-live="off"><span id="cwn-l">Planned 8:00 AM start</span><i id="cwn-c" style="display:none"></i><span id="cwn-n"></span><b id="cwn-t"></b></div></div>')
    showdate = datetime.date.fromisoformat(m["showDate"]).strftime("%a %b %-d")
    showstart = ""  # controls live in the sticky master-control strip
    dialogs = (
        f'<div id="gp">'
        f'<dialog id="g-dlg" class="dlg" aria-labelledby="g-ttl"><div class="dlg-h"><h3 id="g-ttl">Guest on the chyron</h3><button id="g-x" class="dlg-x" type="button" aria-label="Close">×</button></div><div class="dlg-b">'
        f'<label>Name<input id="g-name" type="text" maxlength="60" autocomplete="off" placeholder="Guest name"></label>'
        f'<label>Title<input id="g-title" type="text" maxlength="80" autocomplete="off" placeholder="Title or role"></label>'
        f'<label>Blurb<input id="g-blurb" type="text" maxlength="140" autocomplete="off" placeholder="One line about them"></label>'
        f'<div class="dlg-a"><button id="g-show" type="button">Show guest on chyron</button><button id="g-hide" type="button">Hide</button></div>'
        f'<p id="gp-msg" class="gpm" aria-live="polite"></p></div></dialog>'
        f'<dialog id="c-dlg" class="dlg" aria-labelledby="c-ttl"><div class="dlg-h"><h3 id="c-ttl">On the phone</h3><button id="c-x" class="dlg-x" type="button" aria-label="Close">×</button></div><div class="dlg-b">'
        f'<label>Name<input id="c-name" type="text" maxlength="60" autocomplete="off" placeholder="Caller name"></label>'
        f'<label>Title<input id="c-title" type="text" maxlength="80" autocomplete="off" placeholder="Title or where they are"></label>'
        f'<label>Photo link<input id="c-photo" type="url" maxlength="1000" autocomplete="off" placeholder="https://…"></label>'
        f'<div class="dlg-a"><label class="upl">Upload photo<input id="c-file" type="file" accept="image/*"></label><img id="c-prev" alt="" hidden><span id="c-up" class="gpm"></span></div>'
        f'<div class="dlg-a"><button id="c-go" type="button">Bring caller on</button><button id="c-show" type="button">Show</button><button id="c-hide" type="button">Hide caller</button></div>'
        f'<p id="c-msg" class="gpm" aria-live="polite"></p></div></dialog>'
        f'<dialog id="link-dlg" class="dlg" aria-labelledby="link-ttl"><div class="dlg-h"><h3 id="link-ttl">Link this device</h3><button id="link-x" class="dlg-x" type="button" aria-label="Close">×</button></div><div class="dlg-b">'
        f'<p>This iPad isn\u2019t linked to the studio chyron yet. Open the dashboard once from the control link (the address with <code>?ctl=</code> in it) and this device will remember it. You can also paste the link code here.</p>'
        f'<label>Link code<input id="link-code" type="text" autocomplete="off" spellcheck="false" placeholder="Paste the link code"></label>'
        f'<div class="dlg-a"><button id="link-go" type="button">Link</button></div></div></dialog>'
        f'<dialog id="stop-dlg" class="dlg" aria-labelledby="stop-ttl" aria-describedby="stop-msg"><div class="dlg-h"><h3 id="stop-ttl">Stop the show?</h3><button id="stop-x" class="dlg-x" type="button" aria-label="Cancel">×</button></div><div class="dlg-b">'
        f'<p id="stop-msg">Stop the show and reset to 0:00?</p>'
        f'<div class="dlg-a"><button id="stop-go" type="button">Stop &amp; reset</button><button id="stop-no" type="button">Cancel</button></div></div></dialog>'
        f'<dialog id="done-dlg" class="dlg" aria-labelledby="done-ttl" aria-describedby="done-msg"><div class="dlg-h"><h3 id="done-ttl">Show\'s done?</h3><button id="done-x" class="dlg-x" type="button" aria-label="Cancel">×</button></div><div class="dlg-b">'
        f'<p id="done-msg">Mark ticked stories as Aired and every other story still on the board as Expired? You can undo.</p>'
        f'<div class="dlg-a"><button id="done-go" type="button">Show\'s done</button><button id="done-no" type="button">Cancel</button></div></div></dialog></div>'
    )
    mcbar = (
        f'<div id="mc">'
        f'<div class="mc-id"><img src="{logo}" alt="Drew in the Morning"><div class="mc-brand"><b>DREW IN THE MORNING</b><span id="mc-sub">{esc(m["dateLabel"])}</span></div></div>'
        f'<div id="minibar" class="mc-status"><span id="mc-pill" class="mcp stand">STANDBY</span><b id="mb-time">--:--</b>'
        f'<span id="sslive" aria-live="off"></span><span id="ssind" aria-live="polite">Planned start 8:00 AM</span><span id="chst" aria-live="polite"></span><span id="mb-next"></span></div>'
        f'<div id="chy" class="mc-ops">'
        f'<button id="ssbtn" type="button" data-showdate="{m["showDate"]}" data-showlabel="{showdate}" aria-label="Set show start to now">Start</button>'
        f'<button id="chhold" type="button" aria-pressed="false" title="Hold freezes the current topic and the show clock; Resume carries on and pushes the later topics back">Hold</button>'
        f'<button id="ssstop" type="button" title="Stop the show and reset to 0:00" aria-label="Stop the show and reset to 0:00" aria-haspopup="dialog" aria-controls="stop-dlg">Stop</button>'
        f'<button id="chprev" type="button">Prev</button><button id="chnext" type="button">Next</button><button id="chclr" type="button">Clear</button>'
        f'<button id="mc-guest" type="button">Guest</button><button id="mc-caller" type="button">Caller</button><button id="mc-logo" type="button">Logo</button><button id="showdone" type="button" title="Mark ticked stories as Aired and the rest as Expired" aria-label="Show is done" aria-haspopup="dialog" aria-controls="done-dlg">Show\'s done</button>'
        f'<details id="mc-more"><summary aria-label="More controls">More</summary><div class="mc-more-p">'
        f'<button id="theme" type="button" title="Toggle dark/light">Dark / Light</button>'
        f'<button id="smaller" type="button">A−</button><button id="bigger" type="button">A+</button>'
        f'<button id="expand" type="button">Expand all</button><button id="collapse" type="button">Collapse all</button>'
        f'<button id="sortbtn" type="button" title="Order items by trend score or by the original editorial order">Sort: Score</button>'
        f'<button id="ssreset" type="button" title="Stop the show and reset to 0:00" aria-label="Stop the show and reset to 0:00" aria-haspopup="dialog" aria-controls="stop-dlg">Stop &amp; reset</button>'
        f'<button id="rm-show" type="button">Show removed (0)</button><button id="rm-restore" type="button">Restore all</button><button id="ps-open" type="button">Post-show recap</button>'
        f'<button id="chlink" type="button" class="chlink" title="Link this page to the OBS chyron (paste the link code once)">Link chyron</button>'
        f'<a id="brkbadge" class="btnlike" href="#brk" data-jump="brk" title="Breaking watch: new since this page was built">Breaking <b id="brkb">–</b></a>'
        f'<a href="#top" data-jump="top" aria-label="Back to top">Top ↑</a>'
        f'{clockw}'
        f'</div></details></div></div>'
    )
    usedbar = (f'<div id="usedbar" data-repo="{REPO}"><span class="ubl">Used today <b id="ucount">0</b></span><span id="ustatus"></span>'
               f'<span class="ubb"><button id="ulog" type="button">Log to repo</button><button id="ucopy" type="button">Copy list</button><button id="uclear" type="button">Clear</button></span></div>')
    brk = (f'<section id="brk" aria-label="Breaking watch" data-built="{esc(data.get("generatedAt", ""))}" data-poll="120"><div class="brkh"><b>Breaking / New since build</b>'
           f'<span id="brkcount" class="pill">0</span><span id="brkmeta" class="mut">checking the breaking feed…</span><button id="brkref" type="button">Refresh</button></div>'
           f'<div id="brklist" aria-live="polite"></div></section>')
    arch = f'<p><a href="{esc(archive_href)}">All past packets and briefings</a></p>' if archive_href else ""
    chk = data.get("linkCheck")
    html_out = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data: https:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self' https://api.weather.gov https://ntfy.sh http://127.0.0.1:*"><title>{esc(m["emailSubject"])} · Studio</title><style>{STUDIO_CSS}{STUDIO_CSS2}</style></head><body data-showdate="{esc(m["date"])}">
<div id="pin">{mcbar}
<div id="find"><label class="sr-only" for="q">Search stories and keywords</label><input id="q" type="search" placeholder="Search stories and keywords" autocomplete="off" autocorrect="off" spellcheck="false" enterkeyhint="search" inputmode="search"><button id="q-x" type="button" hidden aria-label="Clear search">Clear</button><span id="q-n" aria-live="polite"></span></div>
<div class="clock pre" id="tl" role="img" aria-label="60 minute show timeline, blocks A to L">{clockbar}<div id="phw"><div id="ph" aria-hidden="true"></div></div></div></div>
{dialogs}
<header id="top" class="ident"><div class="k">Studio page · {esc(m["kicker"])} {('<span class="sample">'+esc(m["sampleLabel"])+'</span>') if m.get("sample") else ''}</div><div class="t">{esc(m["recap"])} · {esc(m["tagline"])}</div></header>
{usedbar}
{brk}
<nav>{nav}</nav>
<main>{body}</main>
<footer>{arch}<b>Jump segues (menu):</b><ul>{segs}</ul>Every item links to its source and opens in a new tab; Copy link puts the URL on your clipboard for sharing on screen. CONFIRM BEFORE AIR = verify first. No trackers, no external scripts or fonts. The only network request is the header clock's weather lookup (api.weather.gov); the page works offline (the clock then shows the build-time temperature, and links need internet). Show Start times are computed in the page from each block's offset and length.{(" Links checked "+chk["date"]+": "+str(chk["ok"])+" ok, "+str(chk["blocked"])+" bot-blocked, "+str(chk["dead"])+" dead.") if chk else ""}</footer>
<div id="post-show" hidden><div id="ps-root"></div></div><!--DITM_STORIES--><div id="toast" role="status"></div><script>{STUDIO_JS}</script><script>{SEARCH_JS}</script><script>{SHOW_JS}</script><script>{CHY_JS}</script><script>{REMOVE_JS}</script><script>{SHOWDONE_JS}</script><script>{POSTSHOW_JS}</script><script>{TLDR_JS}</script><script>{CLOCK_JS}</script><script>{BRK_JS}</script></body></html>"""
    _cat = json.dumps(STORY_CATALOG or data.get("_story_catalog") or [], ensure_ascii=False).replace("<", "\\u003c")
    return html_out.replace("<!--DITM_STORIES-->", '<script type="application/json" id="ditm-stories">' + _cat + "</script>")


# ---------------------------------------------------------------- render

# ---------------------------------------------------------------- obs-data.json (cold open, jingle, up-to) + latest/docs publishing
def update_obs(path, data):
    if not path or not os.path.exists(path): return False
    o = json.load(open(path)); co = data["coldOpen"]; m = data["meta"]
    o["coldOpen"] = co["text"]
    o["coldOpenMeta"] = {"date": m["date"], "template": co["template"], "confirm": co["confirm"], "builtFrom": m["fileStem"], "sample": bool(m.get("sample"))}
    o["jingle"] = {"primary": co["jingle"], "alternates": co["alternates"]}
    o["upTo"] = {"banner": data["up_to_meta"]["banner"], "script": data["up_to_script"], "calendar": data["up_to_meta"].get("calendar", ""), "window": data["up_to_meta"].get("window", ""),
                 "comingWindow": data["up_to_meta"].get("comingWindow", ""), "source": "family calendar (tools/family_calendar.py), generic wording",
                 "events": [{"date": e["date"], "label": e["label"], "category": e["category"], "count": e["count"]} for e in data["up_to"]],
                 "coming": [{"date": e["date"], "label": e["label"], "category": e["category"], "count": e["count"]} for e in data["up_to_coming"]]}
    json.dump(o, open(path, "w"), indent=2, ensure_ascii=False)
    return True

def listing_html(docs):
    rows = []
    pk = os.path.join(docs, "packets")
    for d in sorted(os.listdir(pk), reverse=True):
        mp = os.path.join(pk, d, "meta.json")
        if os.path.exists(mp): rows.append((d, json.load(open(mp))))
    items = ""
    for d, mt in rows:
        files = " · ".join(f'<a href="{d}/{f}">{lab}</a>' for f, lab in ((mt["files"].get(k), lab) for k, lab in (("studio", "Studio"), ("pdf", "PDF"), ("txt", "Text"), ("email", "Email HTML"))) if f)
        items += f'<li><b>{html.escape(mt["label"])}</b> <span>{html.escape(mt["kind"])}{" · SAMPLE/TEST" if mt.get("sample") else ""}</span><br>{files}</li>'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>Drew in the Morning · past packets</title>'
            '<style>body{font:17px/1.5 -apple-system,BlinkMacSystemFont,Inter,Segoe UI,Arial,sans-serif;margin:0;padding:16px max(16px,env(safe-area-inset-left));max-width:900px;margin-inline:auto;overflow-wrap:anywhere}'
            'li{margin:0 0 14px;list-style:none;border:2px solid #1b2430;border-radius:12px;padding:8px 12px}ul{padding:0}a{color:#0b5cad;display:inline-block;min-height:44px;line-height:44px;margin-right:6px}span{color:#5a6b7d;font-weight:600}</style></head><body>'
            f'<h1>Drew in the Morning · all packets and briefings</h1><p><a href="../index.html">Latest studio page</a></p><ul>{items}</ul></body></html>')

def publish(out, stem, data, force=False):
    m = data["meta"]; name = os.path.basename(stem)
    docs = os.path.join(out, "docs"); pk = os.path.join(docs, "packets")
    folder = m["date"] + ("-SAMPLE" if m.get("sample") else "")
    pdir = os.path.join(pk, folder); os.makedirs(pdir, exist_ok=True)
    cp = lambda src, dst: shutil.copyfile(src, dst) if os.path.exists(src) else None
    studio_pkt = studio_html(data, archive_href="../index.html")
    open(os.path.join(pdir, "index.html"), "w").write(studio_pkt)
    for ext in (".pdf", ".txt", ".png", "-email-preview.html"): cp(stem + ext, os.path.join(pdir, name + ext))
    files = {"studio": "index.html", "pdf": name + ".pdf" if os.path.exists(stem + ".pdf") else "", "txt": name + ".txt", "email": name + "-email-preview.html"}
    json.dump({"date": m["date"], "mode": m["mode"], "sample": bool(m.get("sample")), "label": m["headline"].title().replace("Show Packet", "Show Packet") if False else m["dateLabel"] + (" · Monday Show Packet" if m["mode"] == "monday" else " · Daily Briefing"),
               "kind": "Monday show packet" if m["mode"] == "monday" else "Daily briefing", "files": files, "built": data["generatedAt"]}, open(os.path.join(pdir, "meta.json"), "w"), indent=2)
    open(os.path.join(pk, "index.html"), "w").write(listing_html(docs))
    try:   # the OBS chyron page (docs/chyron.html + chyron.json) is rebuilt with every packet from obs-data.json
        sys.path.insert(0, os.path.join(HERE, "..", "companion"))
        import chyron_build
        chyron_build.write(docs)
    except Exception as e:   # never block the packet on the chyron page
        print("chyron page not built:", e)
    # "latest": a real packet is never replaced by a sample/test build unless forced
    lp = os.path.join(pk, "latest.json")
    prev = json.load(open(lp)) if os.path.exists(lp) else None
    take = force or prev is None or not m.get("sample") or prev.get("sample")
    if take:
        json.dump({"date": m["date"], "sample": bool(m.get("sample")), "stem": name}, open(lp, "w"))
        open(os.path.join(docs, "index.html"), "w").write(studio_html(data, archive_href="packets/index.html"))
        open(os.path.join(out, "latest-studio.html"), "w").write(studio_html(data))
        _ps = os.path.join(docs, "post-show")
        os.makedirs(_ps, exist_ok=True)
        open(os.path.join(_ps, "index.html"), "w").write(post_show_html(data, data.get("_story_catalog") or STORY_CATALOG))
        # chyron-items.json: the ONLY words the on-air chyron will show for a "send to chyron" id (ids are what travels over ntfy)
        json.dump({"v": 1, "date": m["date"], "generated": data["generatedAt"], "items": dict(CHY_ITEMS)}, open(os.path.join(docs, "chyron-items.json"), "w"), ensure_ascii=False, indent=1)
        for ext, dst in ((".pdf", "latest.pdf"), (".txt", "latest.txt"), (".png", "latest.png")):
            cp(stem + ext, os.path.join(out, dst)); cp(stem + ext, os.path.join(docs, dst))
    return folder, take

def run(cmd, **k): return subprocess.run(cmd, capture_output=True, text=True, **k)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--obs-data", default=os.path.join(HERE, "..", "obs-data.json"))
    ap.add_argument("--refresh-weather", action="store_true"); ap.add_argument("--check-links", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="skip Chrome (PDF/PNG/screenshot)")
    ap.add_argument("--no-obs-update", action="store_true", help="do not write coldOpen/jingle/upTo into obs-data.json")
    ap.add_argument("--force-latest", action="store_true", help="let a SAMPLE/test build replace the latest-* copies and docs/index.html")
    ap.add_argument("--fetch-trends", action="store_true", help="fetch Google Trends (US-TX + US) for the trend score and cache it in data/trends-cache.json (else use the cache if < 36 h old)")
    ap.add_argument("--no-score", action="store_true", help="skip dedupe + trend score + badges + sorting")
    ap.add_argument("--enrich-synopses", action="store_true", help="re-fetch public og:description/meta description for stories whose synopsis is short (read-only; soft-fail)")
    a = ap.parse_args()
    OPTS["fetch_trends"] = a.fetch_trends; OPTS["score"] = not a.no_score; OPTS["enrich_synopses"] = a.enrich_synopses
    os.makedirs(a.out, exist_ok=True)
    data = prepare(json.load(open(a.data)), a.obs_data, a.refresh_weather)
    stem = os.path.join(a.out, data["meta"]["fileStem"])
    urls = all_urls(data)
    if a.check_links:
        # individual Legacy notices are not link-checked (dozens of requests to one site that rate-limits); the listing page is
        det = check_links(sorted({u["url"] for u in urls if u["url"].startswith("http") and u["section"] != "Remembering Our Neighbors" or u["url"] == OBIT_PAGE}))
        cnt = lambda r: sum(1 for v in det.values() if v["result"] == r)
        data["linkCheck"] = {"date": datetime.date.today().isoformat(), "ok": cnt("ok"), "blocked": cnt("blocked-by-site"), "dead": cnt("dead"), "unreachable": cnt("unreachable")}
        data["linkCheckDetail"] = det
        json.dump(det, open(stem + "-link-check.json", "w"), indent=2)
        print("link check:", data["linkCheck"])
        for u, v in det.items():
            if v["result"] in ("dead", "unreachable"): print("  !!", v["status"], u)
    data["generatedAt"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    data["sources"] = urls
    json.dump(data, open(stem + ".json", "w"), indent=2, ensure_ascii=False)
    open(stem + ".txt", "w").write(txt(data))
    open(stem + "-sources.txt", "w").write(sources_txt(data))
    open(stem + "-email.html", "w").write(email_html(data, False))
    open(stem + "-email-preview.html", "w").write(email_html(data, True))
    open(stem + "-studio.html", "w").write(studio_html(data))
    ph = stem + "-print.html"
    open(ph, "w").write(print_html(data))
    if not a.no_obs_update and update_obs(a.obs_data, data): print("obs-data.json: coldOpen, jingle, upTo updated")
    if a.no_render:
        print("docs:", publish(a.out, stem, data, a.force_latest)); return
    r = run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={stem}.pdf", "file://" + ph]); 
    pages = int(re.search(r"Pages:\s+(\d+)", run(["pdfinfo", stem + ".pdf"]).stdout).group(1))
    dom = run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=2000", "--dump-dom", "file://" + ph]).stdout
    ov = re.search(r'data-overflow="([^"]*)"', dom)
    overflow = ov.group(1) if ov else "?"
    run(["pdftoppm", "-r", "120", "-png", "-f", "1", "-l", "1", "-singlefile", stem + ".pdf", stem])
    run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--window-size=1500,1000", f"--screenshot={stem}-studio.png", "file://" + stem + "-studio.html"])
    os.remove(ph) if os.environ.get("DITM_KEEP_PRINT_HTML") is None else None
    print(f"PDF pages: {pages} (must be 1) · clipped cards: {overflow or 'none'}")
    if pages != 1 or overflow not in ("",):
        print("!! LAYOUT PROBLEM: trim items or tune PRINT_CSS"); sys.exit(2)
    print("docs:", publish(a.out, stem, data, a.force_latest))
    print("built:", stem + ".*")

if __name__ == "__main__":
    main()
