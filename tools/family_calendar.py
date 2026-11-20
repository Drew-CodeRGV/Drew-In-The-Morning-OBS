#!/usr/bin/env python3
"""Block B, "What I've Been Up To This Week", built from Drew's FAMILY calendar (a published iCloud ICS feed).

Reads the feed at run time from the env var DITM_FAMILY_ICS_URL or the box file /workspace/.ditm-private/family-ical-url
(webcal:// is fine). The URL is private: it is never printed, logged, written to a packet or put in the repo.

    python3 tools/family_calendar.py --mode daily            # past 7 days through today
    python3 tools/family_calendar.py --mode monday --today 2026-11-23   # previous Mon-Sun + a "coming up" list (next 7 days)
    python3 tools/family_calendar.py --mode daily --merge packet/data/packet-2026-11-19.json   # writes up_to* into that file
    python3 tools/family_calendar.py --ics-file some.ics --text      # local file (tests / debugging)

Needs `pip install icalendar recurring-ical-events` (recurring events are expanded properly, America/Chicago).

What goes on air (default is EXCLUDE when unsure): school events, concerts and recitals, games, meets and practices worth a
mention, festivals and parades, holiday events, clubs and classes (chess, dance, cotillion, scouts...), community events, trips.
Never: medical or health, grooming, bills and money, work admin, support appointments, pick-ups and drop-offs, routine workouts,
private reservations or dinners, other people's private parties, birthdays and retirements. Labels are built from rules, not copied
from event titles, so a kid's name or an adult's name never reaches the packet unless NAME_KIDS_ON_AIR is true (kids only).
Recurring activities collapse to one line ("chess club twice"). Output carries only counts of what was left out.
"""
from __future__ import annotations
import argparse, datetime, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ditm_yaml  # noqa: E402

TZ_NAME = "America/Chicago"
URL_FILE = "/workspace/.ditm-private/family-ical-url"
CONFIG_PATH = os.path.join(ROOT, "family-calendar.yml")
CALENDAR_LABEL = "Family calendar (iCloud, published feed)"


class CalendarError(Exception):
    """Never carries the feed URL."""


# ---------------------------------------------------------------- rules
def _rx(words: str) -> re.Pattern:
    return re.compile(r"(?<![a-z])(?:" + words + r")(?![a-z])", re.I)


# Checked FIRST. Anything that matches is left off the air.
EXCLUDE = [
    ("medical", _rx(r"laser|glasses|scratches|doctor|dr\.?|dds|dentist|dental|orthodont\w*|pediatric\w*|therap\w*|check-?up|vaccin\w*|shots?|surgery|urgent care|optometr\w*|eye exam|prescription|pharmacy|lab work|x-?ray|physical exam|dermatolog\w*|counsel\w*|med|meds|appointment|appt")),
    ("grooming", _rx(r"hair|haircut|barber|salon|nails?|mani|pedi|wax\w*|spa|facial|massage|lashes|brows?")),
    ("money", _rx(r"bills?|payments?|pay|rent|mortgage|insurance|tax(?:es)?|invoice|loan|bank|money|unemployment|twc|credit|cell phone|phone bill|utility|utilities|due|renew\w*|dmv|registration")),
    ("work", _rx(r"work|dj|meeting|call|interview|proposal|conference|webinar|client|deadline|submission|payroll|zoom|standup|shift")),
    ("support", _rx(r"support|counselor|caseworker|case worker|sponsor|aa|na|recovery")),
    ("pickup", _rx(r"pick-?\s?ups?|drop-?\s?offs?|snacks?|carpool|airport run|shuttle")),
    ("workout", _rx(r"gym|workout|work out|lift\w*|run|jog|peloton|yoga|pilates|crossfit|training session|trainer|spin")),
    ("photos", _rx(r"pics|pictures?|photos?|headshots?|photo ?shoot|portraits?")),
    ("private-meal", _rx(r"reservation|dinner|lunch|brunch|breakfast|date night|happy hour|drinks")),
    ("private-party", _rx(r"party|b-?day|birthday|bday|quince\w*|retirement|retire\w*|baby shower|bridal shower|wedding|funeral|wake|visitation|rosary|memorial|opening|\d+(?:st|nd|rd|th)|anniversary|reunion")),
]

# (key, regex, category, template or None). First match wins. `{k}` = kid prefix ("" / "Fleet's " / "our son's ").
# A None template means the label comes from label_for(); labels are never a raw copy of the title (see label_for).
INCLUDE = [
    ("chess", _rx(r"chess"), "club", "{k}chess club"),
    ("hiphop", _rx(r"hip[- ]?hop"), "dance", "{k}hip hop class"),
    ("tap", _rx(r"tap"), "dance", "{k}tap class"),
    ("cotillion", _rx(r"cotillion"), "club", "{k}cotillion"),
    ("recital", _rx(r"recital|nutcracker"), "dance", "{k}recital"),
    ("choir", _rx(r"choir|chorus"), "music", "{k}choir"),
    ("allstate", _rx(r"all[- ]?state"), "music", "{k}all-state"),
    ("concert", _rx(r"concert|band|orchestra|musical|talent show"), "music", None),
    ("picnic", _rx(r"pic\s?nic"), "school event", "a school picnic"),
    ("teacher", _rx(r"meet the teacher"), "school event", "meet the teacher night"),
    ("assembly", _rx(r"awards?|assembly|graduation|honor roll|njhs|ceremony|field trip|school (?:thing|event|program|play|show)|open house"), "school event", "a school event"),
    ("festival", _rx(r"festival|fiesta|carnival|fair|parade|hoco|homecoming|pep rally|field day|book fair"), "school event", None),
    ("dance", _rx(r"dance|ballet|jazz|folklorico"), "dance", "{k}dance class"),
    ("topgolf", _rx(r"top ?golf"), "outing", "a Topgolf outing"),
    ("sports", _rx(r"cross country|baseball|football|soccer|softball|volleyball|basketball|swim|track|tennis|golf|esports|tournament|scrimmage"), "sports", None),
    ("scouts", _rx(r"scouts?|troop|cub|den meeting|campout|camporee"), "club", "{k}scouts"),
    ("club", _rx(r"robotics|4-?h|ffa|uil|debate|stem"), "club", None),
    ("holiday", _rx(r"friendsgiving|thanksgiving|christmas|posada|halloween|trunk or treat|easter|fourth of july|4th of july|new year|santa|tamalada|el grito|pumpkin patch|tree lighting|corn maze"), "holiday", None),
    ("trip", _rx(r"trip|vacation|travel|cruise|camping|beach|padre|disney|zoo|museum|getaway"), "trip", None),
    ("community", _rx(r"community|volunteer|service project|food drive|toy drive|vbs|neighborhood|farmers market|expo|exhibit"), "community", None),
]

SPORT_RX = re.compile(r"(?<![a-z])(cross country|baseball|football|soccer|softball|volleyball|basketball|swim|track|tennis|golf|esports)(?![a-z])", re.I)
KIND_RX = re.compile(r"(?<![a-z])(game|practice|meet|tournament|match|scrimmage|camp)(?![a-z])", re.I)
GENERIC = {"festival": "a school or community event", "holiday": "a holiday event", "trip": "a trip", "community": "a community event", "concert": "a concert", "club": ""}
# Words that may appear in a title we say almost as written (festival, holiday, parade...). One unknown word and we fall back to a generic label,
# because an unknown capitalized word is probably somebody's name.
SAFE_WORDS = set("""the a an of and at fall winter spring summer school community holiday christmas thanksgiving friendsgiving halloween posada easter new year
festival fiesta carnival fair parade hoco homecoming pep rally field day book dance open house region clinic concert fall band choir pumpkin patch tree lighting
corn maze trunk or treat el grito tamalada fourth july 4th santa cross country elementary middle high jr sr isd""".split())


def label_for(key: str, title: str, pre: str, cfg: dict) -> str:
    if key == "sports":
        m = SPORT_RX.search(title); sport = m.group(1).lower() if m else "sports"
        kind = KIND_RX.search(title); kind = kind.group(1).lower() if kind else ""
        return pre + (f"{sport} {kind}".strip() if kind != "camp" else f"{sport} camp")
    t = re.sub(r"[^\w\s&'’.,-]", "", title)
    t = re.sub(r"\bpic\s?nic\b", "picnic", t, flags=re.I).replace("&", "and").strip()
    words = re.findall(r"[A-Za-z]+", t)
    ok = set(w.lower() for w in cfg.get("known_places", []))
    if t and len(t) <= 48 and not re.search(r"\d|@|http|['’]s\b", t) and words and all(w.lower() in SAFE_WORDS or w.lower() in ok for w in words):
        core = re.sub(r"(?i)^(the|a|an|our)\s+", "", t)
        if key == "concert":
            core = core.lower()
            return pre + core if pre else "the " + core
        return "the " + core if not re.match(r"(?i)^(a|an|the|our)\b", t) else t
    if key == "concert":
        return pre + "concert" if pre else "a concert"
    if key == "holiday":
        m = INCLUDE_BY_KEY["holiday"].search(title)
        kw = m.group(0).lower() if m else ""
        if kw in ("friendsgiving", "pumpkin patch", "corn maze", "tree lighting", "trunk or treat"):
            return "a " + (kw.title() if kw == "friendsgiving" else kw)
        return f"a {kw.title()} event" if kw else GENERIC["holiday"]
    return GENERIC.get(key, "")


INCLUDE_BY_KEY = {k: rx for k, rx, _c, _t in INCLUDE}


def load_config(path: str | None = None) -> dict:
    cfg = ditm_yaml.load(path or CONFIG_PATH) if os.path.exists(path or CONFIG_PATH) else {}
    cfg = cfg or {}
    flag = os.environ.get("DITM_NAME_KIDS_ON_AIR")
    if flag is not None:
        cfg["NAME_KIDS_ON_AIR"] = flag.strip().lower() in ("1", "true", "yes", "on")
    cfg["NAME_KIDS_ON_AIR"] = bool(cfg.get("NAME_KIDS_ON_AIR", False))
    cfg.setdefault("household", "the family")
    cfg["kids"] = [k for k in (cfg.get("kids") or []) if isinstance(k, dict) and k.get("name")]
    cfg["extra_exclude"] = [str(x) for x in (cfg.get("extra_exclude") or [])]
    cfg["known_places"] = [str(x) for x in (cfg.get("known_places") or [])]
    return cfg


# ---------------------------------------------------------------- fetch
def feed_url() -> str:
    u = os.environ.get("DITM_FAMILY_ICS_URL", "").strip()
    if not u and os.path.exists(URL_FILE):
        u = open(URL_FILE).read().strip()
    if not u:
        raise CalendarError("no feed URL: set DITM_FAMILY_ICS_URL or create " + URL_FILE)
    if u.startswith("webcal://"):
        u = "https://" + u[len("webcal://"):]
    return u


def fetch_ics(timeout: int = 40) -> bytes:
    url = feed_url()
    last = "unknown error"
    for _ in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DITM-family-calendar/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            if b"BEGIN:VCALENDAR" not in body[:2000]:
                raise CalendarError("the feed did not return a calendar")
            return body
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except CalendarError:
            raise
        except Exception as e:  # never include the exception text: it can contain the URL
            last = type(e).__name__
    raise CalendarError("could not read the family calendar feed (" + last + ")")


# ---------------------------------------------------------------- events
def _tz():
    from zoneinfo import ZoneInfo
    return ZoneInfo(TZ_NAME)


def today_chicago() -> datetime.date:
    return datetime.datetime.now(_tz()).date()


def read_events(ics: bytes, start: datetime.date, end: datetime.date) -> list[dict]:
    """Expanded events (recurrences included) overlapping [start, end] inclusive, as {title, date, allday}."""
    try:
        import icalendar, recurring_ical_events
    except ImportError as e:
        raise CalendarError("missing packages: pip install icalendar recurring-ical-events") from e
    cal = icalendar.Calendar.from_ical(ics)
    tz = _tz()
    out = []
    for ev in recurring_ical_events.of(cal).between(start, end + datetime.timedelta(days=1)):
        if str(ev.get("STATUS", "")).upper() == "CANCELLED":
            continue
        s = ev["DTSTART"].dt
        allday = not isinstance(s, datetime.datetime)
        d = s if allday else (s.astimezone(tz) if s.tzinfo else s).date()
        e_ = ev.get("DTEND")
        last = d
        if e_ is not None:
            ed = e_.dt
            last = ed if not isinstance(ed, datetime.datetime) else (ed.astimezone(tz) if ed.tzinfo else ed).date()
            if allday or (isinstance(ed, datetime.datetime) and ed.time() == datetime.time(0, 0)):
                last = last - datetime.timedelta(days=1)  # DTEND is exclusive
            last = max(last, d)
        if d > end or last < start:
            continue
        out.append({"title": str(ev.get("SUMMARY", "")).strip(), "date": max(d, start), "last": min(last, end), "allday": allday})
    out.sort(key=lambda e: (e["date"], e["title"]))
    return out


# ---------------------------------------------------------------- classify
def _kid_hits(title: str, cfg: dict) -> list[dict]:
    hits = []
    for k in cfg["kids"]:
        names = [k["name"]] + list(k.get("aliases") or [])
        if any(re.search(r"(?<![A-Za-z])" + re.escape(n) + r"(?![A-Za-z])", title, re.I) for n in names):
            hits.append(k)
    return hits


def _kid_prefix(hits: list[dict], cfg: dict) -> str:
    if not hits:
        return ""
    if cfg["NAME_KIDS_ON_AIR"]:
        if len(hits) == 1:
            return hits[0]["name"] + "'s "
        return " and ".join(h["name"] for h in hits) + "'s "
    roles = {(h.get("role") or "").strip() for h in hits}
    if len(hits) == 1 and roles != {""}:
        return roles.pop() + "'s "
    if len(hits) > 1:
        return "the kids' "
    return ""


def _strip_names(title: str, cfg: dict) -> str:
    t = title
    for k in cfg["kids"]:
        for n in [k["name"]] + list(k.get("aliases") or []):
            t = re.sub(r"(?<![A-Za-z])" + re.escape(n) + r"(?:['’]s)?(?![A-Za-z])", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" -–—:,")


def classify(title: str, cfg: dict) -> dict:
    """-> {"keep": bool, "reason": str, "key", "category", "label"(noun phrase)}."""
    t = title.strip()
    if not t:
        return {"keep": False, "reason": "blank"}
    kids = _kid_hits(t, cfg)
    scrubbed = _strip_names(t, cfg)
    for reason, rx in EXCLUDE:
        if rx.search(scrubbed):
            return {"keep": False, "reason": reason}
    for w in cfg["extra_exclude"]:
        if re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", scrubbed, re.I):
            return {"keep": False, "reason": "extra"}
    for key, rx, cat, tpl in INCLUDE:
        if not rx.search(scrubbed):
            continue
        pre = _kid_prefix(kids, cfg)
        label = tpl.format(k=pre) if tpl else label_for(key, scrubbed, pre, cfg)
        if not label:           # nothing safe and specific to say: leave it off
            return {"keep": False, "reason": "unsure"}
        return {"keep": True, "reason": "included", "key": key, "category": cat, "label": label, "kids": [k["name"] for k in kids]}
    return {"keep": False, "reason": "unsure"}


# ---------------------------------------------------------------- build
TIMES = {2: "twice", 3: "three times", 4: "four times", 5: "five times"}


def _dow(d: datetime.date) -> str:
    return d.strftime("%A")


def collapse(events: list[dict], cfg: dict) -> tuple[list[dict], dict]:
    """One item per activity. Returns (items sorted by first date, {excluded: n, included: n, reasons: {...}})."""
    groups: dict[tuple, dict] = {}
    stats = {"seen": len(events), "included": 0, "excluded": 0, "reasons": {}}
    for ev in events:
        c = classify(ev["title"], cfg)
        if not c["keep"]:
            stats["excluded"] += 1
            stats["reasons"][c["reason"]] = stats["reasons"].get(c["reason"], 0) + 1
            continue
        stats["included"] += 1
        # recurring activities (same rule + same kids) collapse; one-offs keep their own line
        gk = (c["key"], tuple(c["kids"]), c["label"])
        g = groups.get(gk)
        if g is None:
            groups[gk] = {"date": ev["date"].isoformat(), "dates": [ev["date"].isoformat()], "label": c["label"], "category": c["category"], "key": c["key"]}
        else:
            if ev["date"].isoformat() not in g["dates"]:
                g["dates"].append(ev["date"].isoformat())
    items = []
    for g in groups.values():
        g["dates"].sort()
        g["date"] = g["dates"][0]
        g["count"] = len(g["dates"])
        items.append(g)
    items.sort(key=lambda g: (g["date"], g["label"]))
    return items, stats


def when_phrase(g: dict, past: bool) -> str:
    n = g["count"]
    if n > 1:
        return TIMES.get(n, f"{n} times")
    return "on " + _dow(datetime.date.fromisoformat(g["date"]))


def _join(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + (", and " if len(parts) > 2 else " and ") + parts[-1]


def make_script(items: list[dict], coming: list[dict], mode: str, cfg: dict) -> str:
    """20-40 seconds, talk-show light. Past-tense for the week that was; future-tense for 'coming up'."""
    house = cfg.get("household") or "the family"
    cap = lambda s: s[0].upper() + s[1:]
    def phr(xs, n):
        shown = xs[:n]
        s = _join([f"{g['label']} {when_phrase(g, True)}" for g in shown])
        return s + (", plus a few other things" if len(xs) > n else "")
    if not items and not coming:
        return (f"Quiet week on the family calendar. No big events, which honestly sounds nice. Jess, what's the best thing you did with your free time lately? "
                "Okay, let's get into the Valley.")
    out = []
    if items:
        out.append(f"Busy week at {house}. We had {phr(items, 6)}." if len(items) >= 3 else f"Here's our week at {house}: {phr(items, 6)}.")
    else:
        out.append(f"Pretty quiet week at {house}.")
    if coming:
        shown = coming[:4]
        out.append("Coming up this week: " + _join([f"{g['label']} {when_phrase(g, False)}" for g in shown]) + (", and a couple more things." if len(coming) > 4 else "."))
    out.append("Jess, what was your favorite part of the week? Okay, let's get into the Valley.")
    return " ".join(out)


def week_windows(mode: str, today: datetime.date) -> tuple[tuple, tuple | None]:
    if mode == "monday":
        prev_mon = today - datetime.timedelta(days=today.weekday() + 7)
        past = (prev_mon, prev_mon + datetime.timedelta(days=6))
        return past, (today, today + datetime.timedelta(days=6))
    return (today - datetime.timedelta(days=6), today), None


def build(ics: bytes, mode: str = "daily", today: datetime.date | None = None, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    today = today or today_chicago()
    past, coming = week_windows(mode, today)
    lo = past[0]; hi = (coming or past)[1]
    events = read_events(ics, lo, hi)
    in_past = [e for e in events if past[0] <= e["date"] <= past[1]]
    items, st = collapse(in_past, cfg)
    citems, cst = ([], {"seen": 0, "included": 0, "excluded": 0, "reasons": {}})
    if coming:
        in_coming = [e for e in events if coming[0] <= e["date"] <= coming[1]]
        citems, cst = collapse(in_coming, cfg)
    lab = lambda a, b: f"{a.strftime('%b')} {a.day}\u2013{b.day}" if a.month == b.month else f"{a.strftime('%b')} {a.day} \u2013 {b.strftime('%b')} {b.day}"
    excl = st["excluded"] + cst["excluded"]
    meta = {
        "calendar": CALENDAR_LABEL, "mode": mode, "window": lab(*past) + f", {past[1].year}",
        "comingWindow": (lab(*coming) + f", {coming[1].year}") if coming else "",
        "status": "found" if (items or citems) else "none",
        "nameKidsOnAir": cfg["NAME_KIDS_ON_AIR"],
        "internal": f"{excl} calendar item{'' if excl == 1 else 's'} left off the air (medical, personal, money, work, private or unsure); {st['included'] + cst['included']} qualifying occurrence{'' if st['included'] + cst['included'] == 1 else 's'} used. Names never leave this note.",
        "excludedCount": excl, "usedCount": st["included"] + cst["included"], "builtAt": datetime.datetime.now(_tz()).isoformat(timespec="seconds"),
    }
    strip = lambda gs: [{"date": g["date"], "label": g["label"], "category": g["category"], "count": g["count"]} for g in gs]
    return {"up_to": strip(items), "up_to_coming": strip(citems), "up_to_script": make_script(items, citems, mode, cfg), "up_to_meta": meta}


def to_text(res: dict) -> str:
    m = res["up_to_meta"]
    lines = [f"{m['calendar']} · {m['window']}" + (f" · coming up {m['comingWindow']}" if m["comingWindow"] else ""), "", "SCRIPT: " + res["up_to_script"], ""]
    for g in res["up_to"]:
        lines.append(f"  {g['date']} · {g['category']} · {g['label']}" + (f" (x{g['count']})" if g["count"] > 1 else ""))
    for g in res["up_to_coming"]:
        lines.append(f"  COMING {g['date']} · {g['category']} · {g['label']}" + (f" (x{g['count']})" if g["count"] > 1 else ""))
    lines += ["", "INTERNAL: " + m["internal"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--mode", choices=("daily", "monday"), default="daily")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today in America/Chicago); for monday mode pass the show Monday")
    ap.add_argument("--ics-file", help="read a local .ics instead of the private feed")
    ap.add_argument("--config", help="family-calendar.yml path")
    ap.add_argument("--merge", help="packet data JSON to update in place (up_to, up_to_coming, up_to_script, up_to_meta)")
    ap.add_argument("--out", help="also write the result JSON here")
    ap.add_argument("--text", action="store_true")
    a = ap.parse_args(argv)
    try:
        ics = open(a.ics_file, "rb").read() if a.ics_file else fetch_ics()
        today = datetime.date.fromisoformat(a.today) if a.today else None
        res = build(ics, a.mode, today, load_config(a.config))
    except CalendarError as e:
        print(f"family_calendar: {e}", file=sys.stderr)
        return 2
    if a.out:
        json.dump(res, open(a.out, "w"), indent=2, ensure_ascii=False)
    if a.merge:
        d = json.load(open(a.merge))
        for k in ("up_to", "up_to_coming", "up_to_script", "up_to_meta"):
            d[k] = res[k]
        json.dump(d, open(a.merge, "w"), indent=2, ensure_ascii=False)
    print(to_text(res) if a.text else json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
