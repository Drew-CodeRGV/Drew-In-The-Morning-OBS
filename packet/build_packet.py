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
import argparse, base64, concurrent.futures, datetime, html, json, os, re, shutil, subprocess, sys, textwrap, urllib.request, urllib.error

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
OPTS = {"fetch_trends": False, "score": True}

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
    prep_up_to(data); prep_trending(data); prep_tech(data); prep_obituaries(data); score_stage(data); data["coldOpen"] = build_cold_open(data)
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
    ob = data["obituaries"]
    if ob["count"]:
        obit_b = f'<p style="margin:0 0 6px;font-size:12px;color:#66788c">{ob["count"]} obituaries The Monitor ran on Legacy.com, {esc(ob["windowLabel"])}. Names, ages, towns and funeral homes are only what each notice lists. Read near the close, block L.</p>'
        obit_b += f'<p style="margin:0 0 8px"><b>On-air read:</b> {esc(ob["script"])}</p>'
        for g in ob["groups"]:
            obit_b += f'<p style="margin:8px 0 2px"><b>{esc(g["label"])}</b> ({len(g["items"])})</p><ul style="margin:0;padding-left:18px">' + "".join(
                f'<li><a href="{esc(r["url"])}" style="color:#0b5cad">{esc(r["name"])}</a>' + esc(obit_line(r)[len(r["name"]):]) + '</li>' for r in g["items"]) + "</ul>"
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
        for g in ob["groups"]:
            W(f"  {g['label']} ({len(g['items'])})")
            for r in g["items"]:
                W("    - " + obit_line(r)); W("      " + r["url"])
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
--fs:clamp(17px,1.1vw + 9px,20px);--hh:118px;--sl:env(safe-area-inset-left,0px);--sr:env(safe-area-inset-right,0px);--st:env(safe-area-inset-top,0px);--sb:env(safe-area-inset-bottom,0px)}
[data-theme=dark]{--bg:#10151c;--fg:#eef2f6;--card:#1a222d;--line:#4c5d70;--mut:#9fb0c2;--link:#7cc0ff;--chip:#263140;--ok:#37c97a}
*{box-sizing:border-box;-webkit-tap-highlight-color:rgba(228,87,46,.28)}
html{font-size:var(--fs);-webkit-text-size-adjust:100%;text-size-adjust:100%;touch-action:manipulation;scroll-padding-top:calc(var(--hh) + 8px);color-scheme:light}
[data-theme=dark]{color-scheme:dark}
[id]{scroll-margin-top:calc(var(--hh) + 8px)}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Inter,-apple-system,BlinkMacSystemFont,'SF Pro Text','Segoe UI',Roboto,Arial,sans-serif;line-height:1.4;overflow-wrap:anywhere;touch-action:manipulation}
a,button,summary{touch-action:manipulation}
img,svg{max-width:100%;height:auto}
a{color:var(--link)}
header{position:relative;z-index:6;background:var(--bg);border-bottom:3px solid var(--line);padding:max(8px,var(--st)) max(16px,var(--sr)) 8px max(16px,var(--sl));display:flex;gap:clamp(8px,1.5vw,16px);align-items:center;flex-wrap:wrap}
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
#usedbar{background:var(--chip);border-bottom:2px solid var(--line);padding:6px max(16px,var(--sr)) 6px max(16px,var(--sl));display:flex;align-items:center;gap:8px 12px;flex-wrap:wrap}
#usedbar .ubl{font-weight:800}#usedbar .ubl b{display:inline-block;min-width:1.6em;text-align:center;background:var(--ok);color:#fff;border-radius:99px;padding:0 8px}
#ustatus{color:var(--mut);font-size:.8rem;font-weight:600;flex:1 1 160px}
#usedbar .ubb{display:flex;gap:8px;margin-left:auto;flex-wrap:wrap}
.btnlike{display:inline-flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;padding:4px 12px;border:2px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg);font-weight:700;text-decoration:none}
nav{display:flex;gap:6px;flex-wrap:wrap;padding:8px max(16px,var(--sr)) 8px max(16px,var(--sl))}
nav a{background:var(--chip);border-radius:99px;padding:8px 14px;min-height:44px;display:inline-flex;align-items:center;font-weight:700;font-size:.85rem;text-decoration:none;color:var(--fg);border:1px solid var(--line)}
.clock{display:flex;margin:6px max(16px,var(--sr)) 6px max(16px,var(--sl));height:52px;border-radius:10px;overflow:hidden;border:2px solid var(--line)}
.clock a{display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;font-weight:900;text-decoration:none;border-right:1px solid rgba(255,255,255,.6);font-size:clamp(.85rem,1vw + .4rem,1.15rem);line-height:1;min-width:0}.clock a small{font-size:clamp(.55rem,.5vw + .35rem,.7rem);font-weight:700;opacity:.95}
main{padding:6px max(16px,var(--sr)) calc(40px + var(--sb)) max(16px,var(--sl));display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,380px),1fr));gap:12px;align-items:stretch}
details{background:var(--card);border:2px solid var(--line);border-radius:12px;overflow:hidden;min-width:0}
summary{cursor:pointer;list-style:none;padding:8px 12px;min-height:48px;color:#fff;font-weight:900;letter-spacing:.05em;text-transform:uppercase;display:flex;justify-content:space-between;align-items:center;gap:4px 10px;flex-wrap:wrap;font-size:clamp(.92rem,.8vw + .65rem,1.15rem)}
summary::-webkit-details-marker{display:none}summary small{font-weight:600;text-transform:none;letter-spacing:0;opacity:.95;font-size:.78em}
summary:after{content:'\\25BE';margin-left:auto;font-size:1.2em;padding-left:6px}details:not([open])>summary:after{content:'\\25B8'}
.body{padding:10px clamp(10px,1.4vw,16px);min-width:0}
.item{display:flex;gap:8px;align-items:center;padding:6px 0;border-bottom:1px dashed var(--line)}.item:last-child{border:0}
.item .tx{flex:1 1 auto;min-width:0}.item .tx>a{font-weight:700}.src{color:var(--mut);font-size:.8rem;font-weight:600}
.acts{display:flex;gap:6px;flex:none;align-items:center}
.cp{font-size:.74rem;padding:2px 8px;flex:none}.cf{display:inline-block;background:#c1121f;color:#fff;font-size:.7rem;font-weight:900;border-radius:4px;padding:0 5px}
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
.rdgrid{display:grid;grid-template-columns:minmax(0,1fr);gap:8px;align-items:start}
@media (min-width:600px){.rdgrid{grid-template-columns:repeat(auto-fill,minmax(min(100%,330px),1fr))}.rdgrid>details[open]{grid-column:1/-1}}
.rd{border:2px solid var(--line);border-radius:10px;margin:6px 0;background:var(--card)}.rdgrid>.rd{margin:0}.rd>summary{border-radius:0;min-height:60px}
.rd .bl{display:inline-flex;align-items:center;justify-content:center;width:2.5rem;height:2.5rem;border-radius:10px;background:rgba(255,255,255,.25);font-size:1.6rem;font-weight:900;margin-right:8px;flex:none;letter-spacing:0}
.rd .rt{display:flex;align-items:center;min-width:0;flex:1 1 220px}
.rd h4{margin:8px 0 3px;font-size:.85rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}.rd ul{margin:0;padding-left:20px}
.chy{display:inline-block;background:#1b2430;color:#fff;border-radius:6px;padding:2px 8px;margin:2px;font-size:.85rem}.chy b{color:#ffd23f}
#usedul{margin:0;padding-left:20px}#usedul li{margin-bottom:4px}
#toast{position:fixed;bottom:calc(18px + var(--sb));left:50%;transform:translateX(-50%);background:#1b2430;color:#fff;padding:8px 16px;border-radius:99px;font-weight:700;opacity:0;transition:.25s;pointer-events:none;z-index:9;max-width:92vw}#toast.on{opacity:1}
.obl{list-style:none;margin:0 0 8px;padding:0}.obl li{padding:5px 0;border-bottom:1px dashed var(--line)}.obh{margin:10px 0 2px;font-size:1rem}
footer{padding:10px max(16px,var(--sr)) calc(30px + var(--sb)) max(16px,var(--sl));color:var(--mut);font-size:.8rem}
@media (pointer:coarse){.cp{min-height:44px;min-width:56px}}
@media print{#minibar{display:none}header,#usedbar{position:static}.cp,.use,#clockw,#usedbar,.tools{display:none}}
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
var hd=document.querySelector('header'),mb=$('minibar');
function hh2(){var h=getComputedStyle(hd).position==='sticky'?hd.offsetHeight:(mb&&getComputedStyle(mb).display!=='none'?mb.offsetHeight:0);document.documentElement.style.setProperty('--hh',h+'px')}hh2();addEventListener('resize',hh2);if(window.ResizeObserver)new ResizeObserver(hh2).observe(hd);
/* slim sticky mini clock on phones/tablets: mirrors the big clock so the header itself can scroll away */
function mini(){var t=$('cw-time'),n=$('cwnext');if(!mb||!t)return;$('mb-time').textContent=t.textContent.replace(/:\d\d(?= [AP]M)/,'');var x=n?(n.textContent||'').replace(/\s+/g,' ').trim():'';$('mb-next').textContent=x;mb.className=n&&/amber/.test(n.className)?'amber':n&&/red/.test(n.className)?'red':''}
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
var sfs=parseFloat(store.get('ditm-fs'));if(sfs)r.style.setProperty('--fs',sfs+'px');
function curfs(){return parseFloat(getComputedStyle(r).fontSize)||17}
$('theme').onclick=function(){t=t==='dark'?'light':'dark';r.setAttribute('data-theme',t);store.set('ditm-theme',t)};
$('bigger').onclick=function(){var n=Math.min(28,curfs()+2);r.style.setProperty('--fs',n+'px');store.set('ditm-fs',n)};
$('smaller').onclick=function(){var n=Math.max(17,curfs()-2);r.style.setProperty('--fs',n+'px');store.set('ditm-fs',n)};
/* ---- collapsed by default; this session's open/closed state lives in sessionStorage (a fresh tab starts collapsed) ---- */
var OK='ditm-open-v1',opn={},sm={get:function(k){try{return sessionStorage.getItem(k)}catch(e){return mem['s'+k]===undefined?null:mem['s'+k]}},set:function(k,v){mem['s'+k]=v;try{sessionStorage.setItem(k,v)}catch(e){}}};
try{opn=JSON.parse(sm.get(OK)||'{}')||{}}catch(e){opn={}}
var DET=[].slice.call(document.querySelectorAll('details[id]'));
DET.forEach(function(d){if(opn[d.id])d.open=true});
var lastTap=0;document.addEventListener('click',function(e){if(e.target.closest&&e.target.closest('summary'))lastTap=Date.now()},true);
DET.forEach(function(d){d.addEventListener('toggle',function(){if(d.open)opn[d.id]=1;else delete opn[d.id];sm.set(OK,JSON.stringify(opn));if(d.open&&Date.now()-lastTap<500&&d.classList.contains('sec')){lastTap=0;setTimeout(function(){d.scrollIntoView({behavior:'smooth',block:'start'})},30)}})});
function setAll(v){[].forEach.call(document.querySelectorAll('details'),function(d){d.open=v})}
$('expand').onclick=function(){setAll(true)};
$('collapse').onclick=function(){setAll(false)};
if(location.hash.length>1){var hh=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(hh){var hp=hh.closest('details.sec');if(hp)hp.open=true;if(hh.tagName==='DETAILS')hh.open=true}}
/* ---- order items by trend score (default) or editorial order ---- */
var SORT=sm.get('ditm-sort')||'score';
function sortAll(){[].forEach.call(document.querySelectorAll('.sortbox'),function(b){var k=[].slice.call(b.children).filter(function(c){return c.dataset.ord!==undefined});
 k.sort(function(a,c){return SORT==='ord'?(a.dataset.ord-c.dataset.ord):((c.dataset.sc-a.dataset.sc)||(a.dataset.ord-c.dataset.ord))});k.forEach(function(c){b.appendChild(c)})});
 $('sortbtn').textContent='Sort: '+(SORT==='ord'?'Editorial':'Score')}
$('sortbtn').onclick=function(){SORT=SORT==='ord'?'score':'ord';sm.set('ditm-sort',SORT);sortAll()};
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
 var c=e.target.closest('[data-jump]');if(c){var d=document.getElementById(c.dataset.jump);if(d){var p=d.closest('details.sec');if(p)p.open=true;if(d.tagName==='DETAILS')d.open=true;d.scrollIntoView({behavior:'smooth',block:'start'})}e.preventDefault()}});
paint();
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
.brkrow .src{white-space:nowrap}.brkrow.old{opacity:.78}
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
.rd.live{box-shadow:0 0 0 4px var(--ok);position:relative}
.rd.live>summary .tl{display:inline-block;background:#fff;color:#1f9d55;font-size:.68rem;font-weight:900;border-radius:4px;padding:0 5px;margin-left:6px}
.tl{display:none}
.clock a.live{outline:4px solid #fff;outline-offset:-4px;filter:brightness(1.15)}
.cwn{display:flex;gap:6px;justify-content:flex-end;align-items:center;margin-top:4px;padding:2px 8px;border-radius:99px;min-height:1.9em;font-size:clamp(.78rem,.6vw + .52rem,.95rem);font-weight:800;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;border:2px solid transparent}
.cwn #cwn-l{color:var(--mut)}.cwn #cwn-c{color:#fff;font-style:normal;font-weight:900;border-radius:6px;padding:0 7px;min-width:1.6em;text-align:center}
.cwn #cwn-n{min-width:0;overflow:hidden;text-overflow:ellipsis}.cwn #cwn-t{font-weight:900}
.cwn.amber{background:#f2a900;color:#1b2430;border-color:#b87c00}.cwn.amber #cwn-l{color:#1b2430}
.cwn.red{background:#c1121f;color:#fff;border-color:#7d0b14}.cwn.red #cwn-l{color:#fff}
@media (max-width:820px){.cwn{justify-content:flex-start}}
.weave{background:var(--chip);border-radius:8px;padding:4px 8px;font-weight:700;font-size:.9rem}
@media (max-width:560px){.rd>summary{--trw:6.6rem}.tr{font-size:.95rem}}

/* ---- layout v6: uniform collapsed tiles, full-width multi-column expanded sections, native phone scrolling ---- */
#minibar{display:none}
.toolbar{display:flex;gap:6px 14px;align-items:center;flex-wrap:wrap;padding:6px max(16px,var(--sr)) 0 max(16px,var(--sl))}
.toolbar .t{font-size:.82rem;color:var(--mut);font-weight:600;flex:1 1 260px;min-width:0}
.toolbar .tools{margin:0;flex:0 1 auto}
.ht .d{font-size:clamp(1.25rem,1.8vw + .6rem,1.9rem)}
.ht{flex:1 1 280px}
@media (min-width:1000px){
 header{position:sticky;top:0;flex-wrap:nowrap}
 #clockw{flex:0 0 auto}
 .ss{margin:2px 0 0}
}
@media (max-width:999px){
 #minibar{display:flex;position:sticky;top:0;z-index:8;align-items:center;gap:8px;min-height:44px;padding:4px max(12px,var(--sr)) 4px max(12px,var(--sl));padding-top:max(4px,var(--st));background:var(--bg);border-bottom:3px solid var(--line);font-weight:800;font-variant-numeric:tabular-nums}
 #minibar b{font-size:1.15rem;white-space:nowrap}
 #minibar span{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.8rem;color:var(--mut)}
 #minibar.amber{background:#f2a900;color:#1b2430}#minibar.amber span{color:#1b2430}
 #minibar.red{background:#c1121f;color:#fff}#minibar.red span{color:#fff}
 #minibar a{flex:none;display:inline-flex;align-items:center;min-height:44px;padding:0 10px;font-weight:800;font-size:.85rem;text-decoration:none;color:var(--link)}
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
 nav::-webkit-scrollbar,.clock::-webkit-scrollbar{display:none}
 nav a{flex:none}
 #usedbar .ubb{margin-left:0;width:100%}#usedbar .ubb>*{flex:1 1 auto}
 #brk .brkh button{flex:none}
 #toast{max-width:calc(100vw - 24px)}
}
.clock{overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;scrollbar-width:none;overscroll-behavior-x:contain}
.clock a{flex:0 0 auto;min-width:44px}
/* uniform collapsed tiles: same box for every section, whatever its content */
details.sec{align-self:stretch}
details.sec[open]{grid-column:1/-1}
.sec>summary{position:relative;display:grid;grid-template-columns:auto minmax(0,1fr) auto;grid-template-rows:auto auto;align-items:center;gap:1px 0;height:var(--sumh,4.1rem);min-height:var(--sumh,4.1rem);padding:6px 12px;overflow:hidden;flex-wrap:nowrap;letter-spacing:.03em}
.sec>summary .st,.sec>summary .tt{display:contents}
.sec>summary .bl2{grid-column:1;grid-row:1/3;margin:0;min-width:2.2rem;height:2.2rem}
.sec>summary .tn{grid-column:2/4;grid-row:1;margin-left:10px;padding-right:1.6rem;font-size:clamp(.9rem,.5vw + .78rem,1.08rem);line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;align-self:end}
.sec>summary .tt small{grid-column:2;grid-row:2;margin:0 0 0 10px;display:block;font-size:.76rem;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;align-self:start}
.sec>summary:after{position:absolute;right:12px;top:7px;margin:0;padding:0;line-height:1}
.sec>summary .sm{grid-column:3;grid-row:2;margin:0 0 0 10px;flex-wrap:nowrap;white-space:nowrap;max-width:15rem;overflow:hidden;align-self:start;gap:4px;justify-content:flex-start}
.sec>summary .sm .sb,.sec>summary .sm .cf,.sec>summary .sm .cnt{margin:0;white-space:nowrap;flex:none}
.sec>summary .sm .cnt{flex:none}
@media (max-width:560px){.sec>summary .sm{max-width:8.5rem}.sec>summary .sm .sb:nth-child(n+3){display:none}}
.sec>.body{padding:12px clamp(12px,1.6vw,20px) 16px}
/* expanded sections fill the row; their content flows in 2-4 columns instead of one tall list */
.sec .sortbox{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,320px),1fr));gap:10px;align-items:stretch}
.sec .sortbox>.item{border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:var(--bg);flex-direction:column;align-items:stretch;gap:6px}
.sec .sortbox>.item>.acts{margin-top:auto;justify-content:flex-end}
.sec .sortbox>.item:last-child{border:1px solid var(--line)}
.sec .sortbox>.item.used{background:rgba(31,157,85,.14)}
.sec .sortbox>.noev{grid-column:1/-1}
/* National Desk story cards (nested details) inside the multi-column grid */
.sec .sortbox>details.rd{margin:0;align-self:stretch}
.sec .sortbox>details.rd[open]{grid-column:1/-1}
.sec .sortbox>details.rd>summary{display:flex;flex-wrap:wrap;align-content:space-between;align-items:center;gap:4px 8px;height:6.6rem;min-height:6.6rem;padding:8px 12px;overflow:hidden}
.sec .sortbox>details.rd[open]>summary{height:auto;min-height:6.6rem}
.sec .sortbox>details.rd>summary .rt{flex:1 1 100%;min-width:0}
.sec .sortbox>details.rd>summary .tt{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;font-size:.95rem;line-height:1.25;letter-spacing:.02em}
.sec .sortbox>details.rd[open]>summary .tt{-webkit-line-clamp:unset;display:block}
.sec .sortbox>details.rd>summary .tt small{display:none}
.sec .sortbox>details.rd>summary .src,.sec .sortbox>details.rd>summary .sm .src{color:rgba(255,255,255,.88)}
.sec .sortbox>details.rd>summary .sm{margin:0;justify-content:flex-start;flex:1 1 auto;min-width:0}
.sec .sortbox>details.rd>summary:after{margin-left:auto}
.thumbrow{display:flex;gap:12px;align-items:center;margin:0 0 10px}.thumbrow img{width:140px;max-width:35%;border-radius:8px;flex:none}
.lvgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:4px 18px;align-items:start}
.obl{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:0 22px}
.rd[open] .body{columns:2 340px;column-gap:26px}
.rd h4{break-after:avoid;break-inside:avoid}.rd .body>.item,.rd .body>.chy{break-inside:avoid}
.cotext,#uptotext{max-width:75ch}
"""

SHOW_JS = r"""
(function(){var b=document.getElementById('ssbtn');if(!b)return;
var SD=b.dataset.showdate,KEY='ditm-showstart-v1:'+SD,PLAN=480,mem={},$=function(i){return document.getElementById(i)};
var store={get:function(k){try{var v=localStorage.getItem(k);return v===null?(mem[k]===undefined?null:mem[k]):v}catch(e){return mem[k]===undefined?null:mem[k]}},
 set:function(k,v){mem[k]=v;try{localStorage.setItem(k,v)}catch(e){}},del:function(k){delete mem[k];try{localStorage.removeItem(k)}catch(e){}}};
var parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',hourCycle:'h23',hour:'2-digit',minute:'2-digit',second:'2-digit'}),
 ctd=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'});
function ct(){var o={};parts.formatToParts(new Date()).forEach(function(p){if(p.type!=='literal')o[p.type]=parseInt(p.value,10)});return{h:o.hour%24,m:o.minute,s:o.second}}
function fmt(m){var h=Math.floor(m/60)%24,mm=m%60;return(h%12||12)+':'+(mm<10?'0':'')+mm}
function fmtp(m){return fmt(m)+' '+(Math.floor(m/60)%24<12?'AM':'PM')}
var rows=[].slice.call(document.querySelectorAll('.tr[data-off]')),start=null;
try{var o=JSON.parse(store.get(KEY)||'null');if(o&&typeof o.startMin==='number')start=o.startMin}catch(e){}
function base(){return start===null?PLAN:start}
function paint(){var st=base();
 rows.forEach(function(r){var off=+r.dataset.off,dur=+r.dataset.dur,s=st+off,e=s+dur,sm=r.querySelector('small');
  r.querySelector('b').textContent=fmt(s)+'\u2013'+fmt(e);r.dataset.range=fmt(s)+'\u2013'+fmt(e);
  r.dataset.flexTxt=r.dataset.stretch?('stretch to '+fmt(s+(+r.dataset.stretch))):'';if(!r.classList.contains('islive'))sm.textContent=r.dataset.flexTxt});
 $('ssind').textContent=start===null?'Planned start 8:00 AM':'Started '+fmtp(start);
 $('ssreset').disabled=start===null;b.setAttribute('aria-label',start===null?'Set show start to now':'Show started '+fmtp(start)+'. Tap to set start to now again');
 live()}
function live(){var st=base(),n=ct(),nowS=n.h*3600+n.m*60+n.s,onDay=ctd.format(new Date())===SD,active=start!==null||onDay,hit=null,left=0,over=false;
 var el=nowS-st*60;if(active){rows.forEach(function(r){var off=+r.dataset.off*60,dur=+r.dataset.dur*60;if(el>=off&&el<off+dur){hit=r;left=off+dur-el}});over=el>=3600}
 rows.forEach(function(r){var d=r.closest('details.rd'),L=r===hit;r.classList.toggle('islive',L);if(d)d.classList.toggle('live',L);var tl=d&&d.querySelector('.tl');
  if(L){r.querySelector('small').textContent='LIVE \u00B7 '+Math.floor(left/60)+':'+('0'+left%60).slice(-2)+' left'}else{r.querySelector('small').textContent=r.dataset.flexTxt||''}});
 [].forEach.call(document.querySelectorAll('.clock a'),function(a){a.classList.toggle('live',!!hit&&a.dataset.jump==='blk-'+hit.dataset.letter)});
 countdown(active,el,hit);
 $('sslive').textContent=hit?('LIVE: '+hit.dataset.letter+' \u00B7 '+hit.dataset.name+' \u00B7 '+Math.floor(left/60)+':'+('0'+left%60).slice(-2)+' left'):(active&&over?'Show time is up (60 min).':'')}
var cn=$('cwnext');
function fmtt(t){t=Math.max(0,t);var h=Math.floor(t/3600),m=Math.floor(t%3600/60),s=t%60;return h?h+':'+('0'+m).slice(-2)+':'+('0'+s).slice(-2):m+':'+('0'+s).slice(-2)}
function countdown(active,el,hit){if(!cn)return;var T=rows.length?(+rows[rows.length-1].dataset.off+ +rows[rows.length-1].dataset.dur)*60:3600,lab='',chip='',nm='',col='',t=null,msg='';
 if(!active){msg=(SD>ctd.format(new Date()))?'Show: '+b.dataset.showlabel+' \u00B7 8:00 AM':'Show\u2019s over'}
 else if(el<0){lab='Show starts in';t=-el}
 else if(el>=T){msg='Show\u2019s over'}
 else{var i=rows.indexOf(hit);if(i>=0&&i<rows.length-1){var nx=rows[i+1];lab='Next:';chip=nx.dataset.letter;nm=nx.dataset.name;col=nx.dataset.color;t=+nx.dataset.off*60-el}else{lab='Show ends in';t=T-el}}
 var cls='cwn'+(t!==null&&t<15?' red':t!==null&&t<60?' amber':'');cn.className=cls;
 $('cwn-l').textContent=msg||lab;var c=$('cwn-c');c.textContent=chip;c.style.display=chip?'inline-block':'none';c.style.background=col||'';
 $('cwn-n').textContent=nm;$('cwn-t').textContent=t===null?'':(chip?'in ':'')+fmtt(t);
 cn.setAttribute('aria-label',(msg||lab)+' '+nm+' '+(t===null?'':fmtt(t)))}
b.onclick=function(){var n=ct();start=n.h*60+n.m;store.set(KEY,JSON.stringify({startMin:start,setAt:new Date().toISOString()}));paint();
 var t=document.getElementById('toast');if(t){t.textContent='Show start set to '+fmtp(start);t.className='on';setTimeout(function(){t.className=''},1800)}};
$('ssreset').onclick=function(){start=null;store.del(KEY);paint()};
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
function row(i,isNew){var r=el('div','brkrow'+(isNew?'':' old'));
 if(isNew)r.appendChild(el('span','nw','NEW'));
 var lab=el('span','sb '+(i.label==='Hot'?'h':i.label==='Trending'?'t':'a'),(i.level==='alert'?'ALERT ':'')+String(i.label||'').toUpperCase()+' '+i.score);r.appendChild(lab);
 if(i.uncovered){r.appendChild(el('span','sb u','UNCOVERED \u00B7 CONFIRM BEFORE AIR'))}
 var u=safe(i.url),a;if(u){a=el('a','',i.title);a.href=u;a.target='_blank';a.rel='noopener noreferrer'}else a=el('span','',i.title);r.appendChild(a);
 var n=(i.sources||[]).length;r.appendChild(el('span','src',(i.source||'')+(n>1?' +'+(n-1)+' more':'')+' \u00B7 '+ago(Date.parse(i.firstSeen)||0)));
 if(i.matches&&i.matches.length)r.appendChild(el('span','src','['+i.matches.slice(0,4).join(', ')+']'));
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
def use_btn(sec, title, url=""):
    key = hashlib.sha1(f"{sec}|{url or title}".encode()).hexdigest()[:10]
    return (f'<button class="use" type="button" data-key="{key}" data-title="{esc(title)}" data-url="{esc(url)}" data-sec="{esc(sec)}" aria-pressed="false" '
            f'aria-label="Mark used on show: {esc(title)}" title="Mark used on show"><span class="ck"></span></button>')

def _by_score(lst):
    return sorted(lst, key=lambda it: (-(it.get("score") or 0), it.get("ord", 0)))


def studio_html(data, archive_href=None):
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
        acts = (CP(url) if url else "") + (use_btn(sec, it["title"], url) if use and sec else "")
        return (f'<div class="item" data-ord="{it.get("ord", 0)}" data-sc="{it.get("score", 0)}"><div class="tx">{main} <span class="src">{esc(it.get("source",""))}</span>{sc_studio(it)}<span class="upill">USED</span>{conf}</div><div class="acts">{acts}</div></div>')
    def linkrow(l):
        return f'<div class="item"><div class="tx">{A(l["url"], l["label"])}</div><div class="acts">{CP(l["url"])}</div></div>'
    def sec(id_, color, title, sub, body, wide=False, open_=False, fg="", count="", badges="", chip=""):
        # every section starts collapsed (open_ is kept only so old calls still work); STUDIO_JS restores the session's state
        chip_h = f'<span class="bl2">{chip}</span>' if chip else ""
        cnt_h = f'<span class="cnt" id="cnt-{id_}">{esc(count)}</span>' if count != "" else ""
        ptitle = html.unescape(re.sub(r"<[^>]+>", "", title))
        return (f'<details class="sec" id="{id_}"><summary style="background:{color};{fg}" title="{esc(ptitle)}"><span class="st">{chip_h}<span class="tt"><span class="tn">{title}</span><small>{sub}</small></span></span>'
                f'<span class="sm">{cnt_h}{badges}</span></summary><div class="body">{body}</div></details>')
    clock = data.get("showClock", [])
    clockbar = "".join(f'<a href="#blk-{c["letter"]}" data-jump="blk-{c["letter"]}" style="width:{c["minutes"]/60*100:.3f}%;background:{c["color"]}" title="{esc(c["title"])} · {c["timeRange"]}">{c["letter"]}{"★" if c["signature"] else ""}<small>{c["minutes"]}m</small></a>' for c in clock)
    thumb = data["headlines"].get("image")
    thumbhtml = f'<div class="thumbrow"><img src="{b64(asset(thumb["file"]), "image/jpeg")}" alt="Starship file photo"><div class="src">{esc(thumb["caption"])} · {A(thumb["credit_url"], "source")}</div></div>' if thumb else ""
    heads = (thumbhtml + '<div class="sortbox">' + "".join(item(i, sec="Headlines: RGV") for i in data["headlines"]["rgv"]) + '</div><div class="src" style="margin-top:6px;font-weight:800">TEXAS</div><div class="sortbox">'
             + "".join(item(i, sec="Headlines: Texas") for i in data["headlines"]["texas"]) + '</div>')
    # ---- cold open
    co = data["coldOpen"]
    conote = f'<p class="mut"><span class="cf">CONFIRM BEFORE AIR</span> teased but unconfirmed: {esc("; ".join(co["confirm"]))}. (Not part of the spoken text.)</p>' if co["confirm"] else ""
    altj = "".join(f"<br>{esc(a)}" for a in co["alternates"])
    coldopen = (f'<p class="cotext" id="cotext">{esc(co["text"])}</p><div class="coact">{CP(co["text"], "Copy cold open")}</div>'
                f'<div class="jingle">🎵 <span id="jtext">{esc(co["jingle"])}</span><small>Alternates:{altj}</small></div><div class="coact">{CP(co["jingle"], "Copy jingle")}</div>{conote}'
                f'<p class="mut">{co["words"]} words, about {max(15, round(co["words"] / 2.6))} seconds. Template: {"Monday" if co["template"] == "monday" else "daily briefing"} (cold-open.md).</p>')
    # ---- what I've been up to
    um = data["up_to_meta"]
    evs = ""
    for e in data["up_to"] + [dict(x, coming=True) for x in data["up_to_coming"]]:
        d = datetime.date.fromisoformat(e["date"]).strftime("%a %b %-d")
        cnt = f' <span class="src">({esc(upto_when(e))})</span>' if e["count"] > 1 else ""
        evs += (f'<div class="item"><div class="tx"><span class="src">{d}</span> <span class="pill">{esc(e["category"])}</span>{" <span class=pill>coming up</span>" if e.get("coming") else ""} {esc(e["label"])}{cnt}'
                f'<span class="upill">USED</span></div><div class="acts">{use_btn(UPTO_SEC, e["label"], "")}</div></div>')
    if not evs: evs = '<div class="noev">Quiet week on the family calendar.</div>'
    upto = (f'<p class="cotext" style="font-size:clamp(1.1rem,1.2vw + .85rem,1.5rem)" id="uptotext">{esc(data["up_to_script"])}</p>' +
            f'<div class="coact">{CP(data["up_to_script"], "Copy script")}</div><h4 style="margin:10px 0 2px">From the family calendar ({esc(um["banner"])})</h4><div class="sortbox">{evs}</div>'
            f'<p class="mut">Window: {esc(um.get("window", "past 7 days"))}{(", coming up " + esc(um["comingWindow"])) if um.get("comingWindow") else ""}. Calendar: {esc(um.get("calendar", ""))}.</p>'
            f'<p class="mut">Family-friendly only: school events, concerts, games, festivals, clubs and classes, holidays, community events and trips, in generic wording (kids are not named on air; the switch is NAME_KIDS_ON_AIR in family-calendar.yml). Medical, grooming, money, work, support, pick-ups, workouts, reservations and other people\'s parties are always left out.</p>'
            + (f'<p class="mut"><b>Internal note, not for air:</b> {esc(um["internal"])}</p>' if um.get("internal") else ""))
    # ---- national
    nat = '<div class="sortbox">'
    for k_, n in enumerate(data["nationalDesk"]):
        lks = "".join(linkrow(l) for l in n["links"])
        conf = f' <span class="cf">CONFIRM BEFORE AIR</span> <span class="src">{esc(conf_text(n))}</span>' if n.get("confirm") else ""
        nat += (f'<details class="rd" id="nat-{k_}" data-ord="{n.get("ord", k_)}" data-sc="{n.get("score", 0)}"><summary style="background:#6d597a"><span class="rt"><span class="tt">{esc(n["title"])}<small>tap to expand</small></span></span><span class="sm">{sc_studio(n)}<span class="upill">USED</span></span></summary><div class="body">'
                f'<div class="uhead"><span>Mark this story used on show</span>{use_btn("National Desk", n["title"], n["links"][0]["url"] if n["links"] else "")}</div>'
                f'<p><b>Fact:</b> {esc(n["summary"])}{conf}</p><p><b style="color:#b07dd6">Our take:</b> {esc(n["angle"])}</p><p><b style="color:#5aa9e6">Why it matters in the Valley:</b> {esc(n["valley"])}</p><p class="mut">{esc(n.get("detail",""))}</p>{lks}</div></details>')
    nat += "</div>"
    # ---- trending
    trn = '<p class="mut">What\'s trending around the nation. Separate from the National Desk (no duplicates). Source order: X trends/news, AP/Reuters, Google Trends, YouTube trending.</p>'
    trn += '<div class="sortbox">'
    for t in data.get("trending", []):
        c = trend_item_conf(t)
        conf = f' <span class="cf">CONFIRM BEFORE AIR</span> <span class="src">{esc(c)}</span>' if c else ""
        lks = "".join(linkrow(l) for l in t.get("links", []))
        media = ""
        if t.get("video_url"): media += f'<div class="src">Video: {A(t["video_url"], "watch")}{(" · credit: " + esc(t["image_credit"])) if t.get("image_credit") else ""}</div>'
        trn += (f'<div class="item trn" data-ord="{t.get("ord", 0)}" data-sc="{t.get("score", 0)}"><div class="tx"><b>{A(t["source_url"], t["title"]) if t.get("source_url") else esc(t["title"])}</b> <span class="pill">{esc(t["category"])}</span> '
                f'<span class="src">{esc(t.get("source", ""))}</span>{sc_studio(t)}<span class="upill">USED</span>{conf}<p>{esc(t["one_line"])}</p><p class="ang"><b>Riff:</b> {esc(t["suggested_angle"])}</p>{media}{lks}</div>'
                f'<div class="acts">{CP(t["source_url"]) if t.get("source_url") else ""}{use_btn("Trending", t["title"], t.get("source_url", ""))}</div></div>')
    trn += "</div>"
    tk = data["tech"]
    tech_h = f'<p class="mut"><b>{esc(tk["badge"])}</b> · {esc(tk["originLabel"])}</p>' + (f'<p class="mut">{esc(tk["note"])}</p>' if tk.get("note") else "")
    tech_h += '<p class="mut">Sub-segment of block J: about 90 seconds after the National Desk, before Trending. Pick 1 or 2 with an RGV or family angle. Local stays bigger.</p><div class="sortbox">'
    for k_, t in enumerate(tk["items"]):
        conf = f' <span class="cf">CONFIRM BEFORE AIR</span> <span class="src">{esc(t["confirm"])}</span>' if t["confirm"] else ""
        lks = "".join(linkrow(l) for l in t.get("links", []))
        pub = f' · {esc(t["published"])}' if t.get("published") else ""
        tech_h += (f'<div class="item trn tech" data-ord="{k_}" data-sc="0"><div class="tx"><b>{A(t["source_url"], t["title"]) if t.get("source_url") else esc(t["title"])}</b> <span class="pill">TECH</span> '
                   f'<span class="src">{esc(t.get("source", ""))}{pub}</span><span class="sb {"a" if tk["origin"] == "wires" else "t"}" title="{esc(tk["originLabel"])}">{esc(t["basis"])}</span><span class="upill">USED</span>{conf}'
                   f'<p>{esc(t["one_line"])}</p><p class="ang"><b>On-air angle:</b> {esc(t["angle"])}</p>{lks}</div>'
                   f'<div class="acts">{CP(t["source_url"]) if t.get("source_url") else ""}{use_btn("Tech", t["title"], t.get("source_url", ""))}</div></div>')
    if not tk["items"]: tech_h += '<p class="mut">No tech items loaded today.</p>'
    tech_h += "</div>"
    ob = data["obituaries"]
    if ob["count"]:
        obit_h = f'<p class="mut">{ob["count"]} obituaries The Monitor ran on Legacy.com, {esc(ob["windowLabel"])}. Names, ages, towns and funeral homes are only what each notice lists. Read about 45 seconds near the close (block L), no joke before or after.</p>'
        obit_h += (f'<p class="cotext" id="obscript">{esc(ob["script"])}</p><div class="coact">{CP(ob["script"], "Copy read")}{use_btn("Remembering Our Neighbors", "Obituary read (block L)", ob["sourceUrl"])}</div>'
                   '<p class="mut"><span class="cf">CONFIRM</span> name pronunciations before reading. Skip any name you are unsure of. ★ marks the names in the read.</p>')
        for g in ob["groups"]:
            obit_h += f'<h3 class="obh">{esc(g["label"])} <span class="mut">({len(g["items"])})</span></h3><ul class="obl">'
            for r in g["items"]:
                star = ' <span title="in the on-air read">★</span>' if r["url"] in ob["pickUrls"] else ""
                obit_h += f'<li>{A(r["url"], r["name"])}{star}<span class="mut">{esc(obit_line(r)[len(r["name"]):])}</span></li>'
            obit_h += "</ul>"
        obit_h += f'<div class="item"><div class="tx">{A(ob["sourceUrl"], ob["source"])}</div><div class="acts">{CP(ob["sourceUrl"])}</div></div>'
    else:
        obit_h = '<p class="mut">No obituaries loaded today. The on-air read is skipped.</p>'
    cells = "".join(f'<div class="{"mon" if d["date"]==w["monday"] else ""}"><b>{d["label"]} {d["dateLabel"]}</b><br>{icon(d["icon"], 44)}<div class="hi">{d["hi"]}°</div><div class="mut">{d["lo"] if d["lo"] is not None else "–"}°</div><div class="pp">{d["pop"]}% rain</div><div class="mut" style="font-size:.75rem">{esc(d["short"])}</div></div>' for d in w["days"][:7])
    upd = datetime.datetime.fromisoformat(w["updated"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
    alerts = "No active NWS alerts." if w.get("alerts") == [] else ("Alerts: " + ", ".join(w["alerts"]) if w.get("alerts") else "")
    weather = f'<div class="wk">{cells}</div><p>{alerts} Updated {upd.strftime("%b %-d %-I:%M %p")} CT.</p>' + "".join(linkrow({"label": t, "url": u}) for t, u in (("NWS forecast page for McAllen", w["pageUrl"]), ("NWS Brownsville office (BRO)", w["officeUrl"]), ("NWS API forecast (JSON)", w["apiUrl"])))
    hs = data["sports"]["highSchool"]
    sl, nl, nores, nonext = hs_texts(hs)
    hsb = f'<p class="mut">{esc(hs["sourceNote"])}</p><b>{esc(sl.capitalize())}</b><div class="scores">' + ("".join(item(r, sec="HS football") for r in hs["results"]) or f'<p class="mut">{esc(nores)}</p>') + f'</div><b>{esc(nl)}</b>' + ("".join(item(r, sec="HS football") for r in hs["next"]) or f'<p class="mut">{esc(nonext)}</p>') + item(hs["college"], sec="HS football")
    def scorebox(g, extra=""):
        s = data["sports"][g]
        sc = '<ul class="scores">' + ("".join(f"<li>{esc(b)} <span class='mut'>{esc(a)}</span></li>" for a, b in s["scores"]) or f"<li>No {g.upper()} games in this window.</li>") + "</ul>"
        if g == "nba": sc += "<b>Texas teams</b><ul class='scores'>" + "".join(f"<li>{esc(b)} <span class='mut'>{esc(a)}</span></li>" for a, b in s["texas"]) + "</ul>"
        return sc + item(s["scoreSource"], "Scores: " + s["scoreSource"]["title"], use=False) + "".join(item(n, sec=g.upper()) for n in s["notable"])
    mlb = data["sports"]["mlb"]
    sports_nfl = scorebox("nfl"); sports_nba = scorebox("nba")
    sports_mlb = f'<p><i>{esc(mlb["note"])}</i></p>' + "".join(item(n, sec="MLB") for n in mlb["notable"])
    colors = {"Elementary": "#2a9d8f", "Middle School": "#8e6bbf", "High School": "#e76f51"}
    mem = f'<p><b>{esc(data["memes"]["tagline"])}</b><br>{esc(data["memes"]["intro"])}</p>'
    mem += '<div class="lvgrid">'
    for lv in data["memes"]["levels"]:
        c = colors.get(lv["level"], "#888")
        mem += f'<div class="lvl" style="border-color:{c}"><h3 style="color:{c}">{lv["icon"]} {esc(lv["level"])}</h3>'
        for it in lv["items"]:
            is_motw = it["id"] == data["memes"].get("memeOfTheWeek")
            conf = f' <span class="cf">CONFIRM BEFORE AIR</span> <span class="src">{esc(conf_text(it))}</span>' if it.get("confirm") else ""
            lks = "".join(linkrow(l) for l in it["links"])
            mem += (f'<div class="mbox {"motw" if is_motw else ""}"><div class="uhead"><span>{esc(it["title"])} {"<span class=tag>Meme of the Week</span>" if is_motw else ""}<span class="upill">USED</span></span>'
                    f'{use_btn("Meme of the Week: " + lv["level"], it["title"], it["links"][0]["url"] if it["links"] else "")}</div>'
                    f'<p>{conf} {esc(it["what"])} <i>{esc(it["means"])}</i><br><b>How to bring it up:</b> {esc(it["tip"])}</p>{lks}</div>')
        mem += "</div>"
    mem += "</div>"
    rd = ""
    for r in data.get("rundown", []):
        chy = "".join(f'<span class="chy"><b>{esc(c["primary"])}</b> · {esc(c["secondary"])}</span>' for c in r["chyrons"])
        lis = lambda xs: "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in xs) + "</ul>"
        lks = "".join(linkrow(l) if l["url"].startswith("http") else f'<div class="item"><div class="tx">{esc(l["label"] + " (" + l["url"] + ")")}</div></div>' for l in r["links"]) or '<p class="mut">none</p>'
        flex = f'FLEX {r["trimTo"]}-{r["stretchTo"]} min' if r["flex"] else "fixed"
        conf = f'<h4>Confirm before air</h4><p><span class="cf">CONFIRM</span> {esc("; ".join(r["confirm"]))}</p>' if r["confirm"] else ""
        weave = f'<p class="weave">Weave: {esc(r["weave"])}</p>' if r.get("weave") else ""
        seg = f'<h4>Segue to the next block</h4><p>“{esc(r["segueNext"])}”</p>' if r.get("segueNext") else ""
        stretch = f' data-stretch="{r["stretchTo"]}"' if r["flex"] and r.get("stretchTo") else ""
        rd += (f'<details class="rd" id="blk-{r["letter"]}"><summary style="background:{r["color"]}"><span class="rt"><span class="bl">{r["letter"]}</span><span class="tt">{esc(r["title"])}{" ★" if r["signature"] else ""}<span class="tl">LIVE</span>'
               f'<small>{r["minutes"]} min · {flex}{" · Jess" if r["jess"] else ""}</small><span class="rbd"><span class="cnt">{len(r["talkingPoints"])} points</span><span class="cnt">{len(r["links"])} sources</span>{("<span class=cf>" + str(len(r["confirm"])) + " CONFIRM</span>") if r["confirm"] else ""}</span></span></span>'
               f'<span class="tr" data-off="{r["offset"]}" data-dur="{r["minutes"]}"{stretch} data-letter="{r["letter"]}" data-name="{esc(r["short"])}" data-color="{r["color"]}"><b>{r["timeRange"]}</b><small></small></span></summary>'
               f'<div class="body"><p class="mut">{esc(r["subject"])}</p>{weave}<h4>Talking points</h4>{lis(r["talkingPoints"])}<h4>Follow-up questions</h4>{lis(r["followUps"]) if r["followUps"] else "<p class=mut>none</p>"}'
               f'<h4>Transition lines</h4>{lis(r["transitions"]) if r["transitions"] else "<p class=mut>none</p>"}{seg}<h4>Chyrons (60 chars max)</h4><p>{chy}</p><h4>Sources</h4>{lks}{conf}</div></details>')
    nav = "".join(f'<a href="#{i}" data-jump="{i}">{t}</a>' for i, t in (("brk", "Breaking"), ("coldopen", "Cold open"), ("upto", "Up To"), ("rundown", "Rundown"), ("headlines", "Headlines"), ("trending", "Trending"), ("national", "National"), ("tech", "Tech"), ("obits", "Neighbors"), ("weather", "Weather"), ("hs", "HS Football"), ("nfl", "NFL"), ("nba", "NBA"), ("mlb", "MLB"), ("memes", "Meme of the Week"), ("used", "Used list")))
    mon = m["mode"] == "monday"
    used_body = ('<ul id="usedul"></ul><p class="mut">Tap the box next to any item when it is used on the show. Marks stay on this device until cleared, so nothing gets repeated. '
                 '"Log to repo" opens a pre-filled GitHub issue (label used-on-show) for the post-show job: it cuts clips from the recording and drafts social teasers for approval. Nothing posts by itself.</p>')
    nh, bh = sc_agg(data["headlines"]["rgv"] + data["headlines"]["texas"])
    nt_, bt_ = sc_agg(data.get("trending", []))
    nn_, bn_ = sc_agg(data["nationalDesk"])
    nm_ = sum(len(lv["items"]) for lv in data["memes"]["levels"])
    cfm = sum(1 for lv in data["memes"]["levels"] for it in lv["items"] if it.get("confirm"))
    n_nfl = len(data["sports"]["nfl"]["scores"]) + len(data["sports"]["nfl"]["notable"])
    n_nba = len(data["sports"]["nba"]["scores"]) + len(data["sports"]["nba"]["notable"])
    n_hs = len(hs["results"]) + len(hs["next"])
    wal = w.get("alerts")
    wb = ('<span class="cf">' + str(len(wal)) + ' ALERT' + ('S' if len(wal) != 1 else '') + '</span>') if wal else ""
    body = "".join([
        sec("coldopen", "#f2b705", "Cold Open &amp; Jingle", "read aloud · about 45 seconds", coldopen, wide=True, fg="color:#1b2430", count=f'{co["words"]} words', chip="A",
            badges=(f'<span class="cf">{len(co["confirm"])} CONFIRM</span>' if co["confirm"] else "")),
        sec("upto", "#d1495b", "What I've Been Up To", "this week · " + esc(um["banner"]), upto, wide=True, count=f'{len(data["up_to"]) + len(data["up_to_coming"])} item{"" if len(data["up_to"]) + len(data["up_to_coming"]) == 1 else "s"}', chip="B"),
        sec("rundown", "#264653", "Full 60-Minute Rundown" if mon else "Monday 8 AM Rundown", "tap a block for notes, questions, chyrons and links" if mon else f'next show: {m["nextShow"]["label"]}, 8-9 AM CT · tap a block', f'<div class="rdgrid">{rd}</div>', wide=True,
            count=f'{len(data.get("rundown", []))} blocks · 60 min'),
        sec("headlines", "#e4572e", "Top Headlines · RGV First", esc(m["hlSub"]), heads, count=f"{nh} stories", badges=bh),
        sec("trending", "#577590", "Trending News", "what's trending around the nation", trn, count=f"{nt_} items", badges=bt_, chip="J"),
        sec("national", "#6d597a", "The National Desk", "fact · take · Valley angle", nat, count=f"{nn_} stories", badges=bn_, chip="J"),
        sec("tech", "#3d5a80", "What's Happening in Tech", "quick hits · block J, after the National Desk", tech_h, count=f'{len(tk["items"])} items', chip="J",
            badges=(f'<span class="sb {"a" if tk["origin"] == "wires" else "t"}">{esc(tk["badge"])}</span>' + (f'<span class="cf">{sum(1 for x in tk["items"] if x["isConfirm"])} CONFIRM</span>' if any(x["isConfirm"] for x in tk["items"]) else ""))),
        sec("obits", "#5c6b7a", "Remembering Our Neighbors", "obituaries from The Monitor · block L, before the sign-off", obit_h, count=f'{ob["count"]} obituaries', chip="L"),
        sec("weather", "#2a7de1", "McAllen / RGV Weather", w["source"], weather, count="7 days", badges=wb),
        sec("hs", "#2a9d8f", "RGV High School Football", hs["round"], hsb, count=f"{n_hs} games"),
        sec("nfl", "#264653", esc(sport_title(data["sports"]["nfl"], False).replace("NFL ", "NFL · ", 1)), "scores + notable", sports_nfl, count=f"{n_nfl} items"),
        sec("nba", "#c1121f", "NBA", esc((data["sports"]["nba"].get("window", "") + " + Texas teams").strip(" +")), sports_nba, count=f"{n_nba} items"),
        sec("mlb", "#003f88", "MLB · Offseason", "no scores · hot stove", sports_mlb, count=f'{len(mlb["notable"])} items'),
        sec("memes", "#ff7f50", "Meme of the Week", "what the kids are talking about · for parents", mem, wide=True, count=f"{nm_} memes", chip="L",
            badges=(f'<span class="cf">{cfm} CONFIRM</span>' if cfm else "")),
        sec("used", "#1f9d55", "Used on Show", "running list · no repeats", used_body, wide=True, count="0 used")])
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
    showstart = (f'<div class="ss"><button id="ssbtn" type="button" data-showdate="{m["showDate"]}" data-showlabel="{datetime.date.fromisoformat(m["showDate"]).strftime("%a %b %-d")}" aria-label="Set show start to now">▶ Show Start</button>'
                 f'<span id="ssind" aria-live="polite">Planned start 8:00 AM</span><button id="ssreset" type="button" disabled title="Reset to 8:00 AM" aria-label="Reset show start to 8:00 AM">↺ 8:00</button><span id="sslive" aria-live="off"></span></div>')
    usedbar = (f'<div id="usedbar" data-repo="{REPO}"><span class="ubl">Used today <b id="ucount">0</b></span><span id="ustatus"></span>'
               f'<span class="ubb"><button id="ulog" type="button">Log to repo</button><button id="ucopy" type="button">Copy list</button><button id="uclear" type="button">Clear</button></span></div>')
    brk = (f'<section id="brk" aria-label="Breaking watch" data-built="{esc(data.get("generatedAt", ""))}" data-poll="120"><div class="brkh"><b>Breaking / New since build</b>'
           f'<span id="brkcount" class="pill">0</span><span id="brkmeta" class="mut">checking the breaking feed…</span><button id="brkref" type="button">Refresh</button></div>'
           f'<div id="brklist" aria-live="polite"></div></section>')
    arch = f'<p><a href="{esc(archive_href)}">All past packets and briefings</a></p>' if archive_href else ""
    chk = data.get("linkCheck")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self' https://api.weather.gov"><title>{esc(m["emailSubject"])} · Studio</title><style>{STUDIO_CSS}{STUDIO_CSS2}</style></head><body>
<div id="minibar" aria-hidden="true"><b id="mb-time">--:--</b><span id="mb-next"></span><a href="#top" data-jump="top" aria-label="Back to top">Top ↑</a></div>
<header id="top"><img src="{logo}" alt="Drew in the Morning"><div class="ht"><div class="k">Studio page · {esc(m["kicker"])} {('<span class="sample">'+esc(m["sampleLabel"])+'</span>') if m.get("sample") else ''}</div><div class="d">{esc(m["dateLabel"])}</div>{showstart}</div>
{clockw}</header>
<div class="toolbar"><div class="t">{esc(m["recap"])} · {esc(m["tagline"])}</div><div class="tools"><button id="theme" type="button" title="Toggle dark/light">Dark / Light</button><button id="smaller" type="button">A−</button><button id="bigger" type="button">A+</button><button id="expand" type="button">Expand all</button><button id="collapse" type="button">Collapse all</button><button id="sortbtn" type="button" title="Order items by trend score or by the original editorial order">Sort: Score</button><a id="brkbadge" class="btnlike" href="#brk" data-jump="brk" title="Breaking watch: new since this page was built">Breaking <b id="brkb">–</b></a></div></div>
{usedbar}
{brk}
<nav>{nav}</nav><div class="clock" aria-label="60 minute show clock">{clockbar}</div>
<main>{body}</main>
<footer>{arch}<b>Jump segues (menu):</b><ul>{segs}</ul>Every item links to its source and opens in a new tab; Copy link puts the URL on your clipboard for sharing on screen. CONFIRM BEFORE AIR = verify first. No trackers, no external scripts or fonts. The only network request is the header clock's weather lookup (api.weather.gov); the page works offline (the clock then shows the build-time temperature, and links need internet). Show Start times are computed in the page from each block's offset and length.{(" Links checked "+chk["date"]+": "+str(chk["ok"])+" ok, "+str(chk["blocked"])+" bot-blocked, "+str(chk["dead"])+" dead.") if chk else ""}</footer>
<div id="toast" role="status"></div><script>{STUDIO_JS}</script><script>{SHOW_JS}</script><script>{CLOCK_JS}</script><script>{BRK_JS}</script></body></html>"""


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
    # "latest": a real packet is never replaced by a sample/test build unless forced
    lp = os.path.join(pk, "latest.json")
    prev = json.load(open(lp)) if os.path.exists(lp) else None
    take = force or prev is None or not m.get("sample") or prev.get("sample")
    if take:
        json.dump({"date": m["date"], "sample": bool(m.get("sample")), "stem": name}, open(lp, "w"))
        open(os.path.join(docs, "index.html"), "w").write(studio_html(data, archive_href="packets/index.html"))
        open(os.path.join(out, "latest-studio.html"), "w").write(studio_html(data))
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
    a = ap.parse_args()
    OPTS["fetch_trends"] = a.fetch_trends; OPTS["score"] = not a.no_score
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
