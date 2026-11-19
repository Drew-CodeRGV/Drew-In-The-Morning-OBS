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

SHORT = {"A": "Open", "B": "Starbase", "C": "Jess·GTA 6", "D": "Ballot Box", "E": "City Hall", "F": "Zoho/Park", "G": "Metro",
         "H": "Open Block", "I": "National", "J": "Listeners", "K": "Meme", "L": "Kids Talk", "M": "Wrap"}

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
    m["fileStem"] = f"DITM-packet-{m['date']}" + ("-SAMPLE" if m.get("sample") else "")
    w = data["weather"]
    if do_weather or "days" not in w:
        refresh_weather(w)
    w["monday"] = m["date"]
    # show clock + rundown from the run-of-show source of truth
    if obs_path and os.path.exists(obs_path):
        obs = json.load(open(obs_path))
        data["showClock"] = [{"letter": s["letter"], "id": s["id"], "title": s["title"], "short": SHORT.get(s["letter"], s["letter"]),
                              "start": s["start"], "end": s["end"], "timeRange": s["timeRange"], "minutes": s["durationMinutes"],
                              "flex": s["flex"], "trimTo": s["canTrimToMinutes"], "stretchTo": s["canStretchToMinutes"],
                              "jess": s["jessDropIn"], "signature": s["signature"], "color": s["color"]} for s in obs["segments"]]
        data["rundown"] = [{"letter": s["letter"], "title": s["title"], "subject": s["subject"], "timeRange": s["timeRange"],
                            "minutes": s["durationMinutes"], "flex": s["flex"], "trimTo": s["canTrimToMinutes"], "stretchTo": s["canStretchToMinutes"],
                            "color": s["color"], "jess": s["jessDropIn"], "signature": s["signature"],
                            "talkingPoints": s["talkingPoints"], "followUps": s["followUpQuestions"], "transitions": s["transitionLines"],
                            "chyrons": s["chyrons"], "links": s["links"], "confirm": s["needsVerification"]} for s in obs["segments"]]
        data["segues"] = [x["line"] for x in obs["segues"] if "National" in x["from"] or "National" in x["to"] or "Meme" in x["to"] or "Listener" in x["to"]][:8]
    assert sum(s["minutes"] for s in data.get("showClock", [])) in (0, 60), "show clock must total 60 minutes"
    # every item needs a URL, else flag
    def fix(item):
        if isinstance(item, dict) and "title" in item and not item.get("url") and not item.get("links"):
            item["confirm"] = (item.get("confirm") or "") + " NO VERIFIED LINK: CONFIRM BEFORE AIR"
    for k in ("rgv", "texas"): [fix(i) for i in data["headlines"][k]]
    for n in data["nationalDesk"]: fix(n)
    hs = data["sports"]["highSchool"]
    [fix(i) for i in hs["results"] + hs["next"]]
    return data

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
    for r in data.get("rundown", []):
        for l in r["links"]: add("Run of show: " + r["letter"], l["label"], l["url"])
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

def jess_star(s): return " ★" if s.get("signature") else ""

# ---------------------------------------------------------------- PRINT (one page)
PRINT_CSS = """
@page { size: 11in 8.5in; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
html, body { width: 11in; height: 8.5in; background: #fff }
body { font-family: Inter, 'Helvetica Neue', Arial, sans-serif; color: #1b2430; font-size: 8.3pt; line-height: 1.22; -webkit-print-color-adjust: exact; print-color-adjust: exact }
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
.thumb { float: right; width: 1.05in; margin: 0 0 3px 6px; border-radius: 6px; border: 1px solid #1b2430 }
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
footer { flex: none; font-size: 7.2pt; color: #4a5a6b; font-weight: 600; display: flex; justify-content: space-between; gap: 10px }
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
    clockhtml = f'<div class="clock"><div class="clockbar">{bar}</div><div class="clockleg"><span><b>8:00</b></span>{leg}<span><b>9:00</b></span></div></div>'
    # headlines
    hl = data["headlines"]; img = hl.get("image")
    items = ""
    for i, it in enumerate([x for x in hl["rgv"] if not x.get("noprint")][:7]):
        pre = ""
        if img and img.get("forItem") == i:
            pre = f'<img class="thumb" src="{b64(asset(img["file"]), "image/jpeg")}">'
        items += f'<li>{pre}<a href="{esc(it["url"])}"><b>{esc(it["short"])}</b> <span class="src">{esc(it["source"])}</span></a></li>'
    tx = "".join(f'<li><a href="{esc(it["url"])}">{esc(it["short"])} <span class="src">{esc(it["source"].split(" · ")[0])}</span></a></li>' for it in hl["texas"][:1])
    headlines = card("headlines", "#e4572e", "Top Headlines · RGV First", "week + weekend", f'<ul class="hl">{items}</ul><div class="cap">{esc(img["caption"]) if img else ""}</div><div style="font-weight:900;font-size:7.8pt;letter-spacing:.06em;margin-top:2px;color:#33404f">TEXAS</div><ul class="hl">{tx}</ul>')
    # national
    nat = ""
    for n in [x for x in data["nationalDesk"] if x.get("print")][:4]:
        conf = '<span class="cf">CONFIRM</span> ' if n.get("confirm") else ""
        nat += f'<li><a href="{esc(n["links"][0]["url"])}"><span class="nt">{esc(n.get("ptitle") or n["title"])}</span></a> {conf}<br>{esc(n.get("pfact") or n["summary"])}<br><span class="lab" style="color:#6d597a">Take:</span> {esc(n.get("pangle") or n["angle"])} <span class="lab" style="color:#2a6f97">Valley:</span> {esc(n.get("pvalley") or n["valley"])}</li>'
    national = card("national", "#6d597a", "The National Desk", "smaller · local leads", f'<ul class="nat">{nat}</ul>')
    onshow = card("onshow", "#264653", "On the Show", "Mon 8-9 AM CT", '<b>Starbase · Ballot Box · City Hall · National Desk · Kids Talk (Jess).</b> Questions: DMs or ditm@drewlentz.com <span class="cf">CONFIRM</span>')
    # weather
    cells = ""
    for dday in w["days"][:7]:
        mon = ' class="mon"' if dday["date"] == w["monday"] else ""
        cells += f'<div{mon}><div class="dd">{dday["label"]} {dday["dateLabel"].split()[1]}</div>{icon(dday["icon"], 26)}<div class="hi">{dday["hi"]}°</div><div class="lo">{dday["lo"] if dday["lo"] is not None else "–"}°</div><div class="pp">{dday["pop"]}%</div></div>'
    mon_day = next((x for x in w["days"] if x["date"] == w["monday"]), None)
    mon_txt = f'<b>Show morning ({mon_day["label"]} {mon_day["dateLabel"]}):</b> {esc(mon_day["short"])}, high {mon_day["hi"]}°, rain {mon_day["pop"]}%, wind {esc(mon_day["wind"])}. ' if mon_day else ""
    upd = datetime.datetime.fromisoformat(w["updated"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
    alerts = "No NWS alerts." if w.get("alerts") == [] else ("Alerts: " + ", ".join(w["alerts"]) if w.get("alerts") else "")
    weather = card("weather", "#2a7de1", "McAllen / RGV Weather", "hi / lo / rain %", f'<div class="wk">{cells}</div><div class="wnote">{mon_txt}{alerts} <span class="src">NWS {esc(w["office"])} · updated {upd.strftime("%b %-d %-I:%M %p")} CT · <a href="{esc(w["pageUrl"])}">forecast</a></span></div>')
    # sports
    hs = data["sports"]["highSchool"]
    ab = {"Brownsville Vets": "B'ville Vets", "Brownsville Pace": "B'ville Pace", "McAllen Memorial": "Memorial", "Mission Vets": "M. Vets", "Gregory-Portland": "Greg-Portland", "Flour Bluff": "Flour Bluff"}
    def abv(t):
        for k, v in ab.items(): t = t.replace(k, v)
        return t
    res = "".join(f'<li><a href="{esc(r["url"])}">{esc(abv(r["short"]))}</a></li>' for r in hs["results"][:10])
    nxt = "".join(f'<li><a href="{esc(r["url"])}">{esc(r["short"])}</a></li>' for r in hs["next"])
    hsc = card("hs", "#2a9d8f", "RGV High School Football", "bi-district scores", f'<ul class="scores">{res}</ul><div style="font-weight:900;font-size:7.8pt;margin-top:2px">THIS WEEK · AREA ROUND</div><ul>{nxt}</ul>')
    nfl = data["sports"]["nfl"]; nba = data["sports"]["nba"]; mlb = data["sports"]["mlb"]
    nf = "".join(f'<li>{esc(b)}</li>' for a, b in nfl["scores"])
    nb = "".join(f'<li>{esc(b)}</li>' for a, b in nba["scores"]) + "".join(f'<li><b>{esc(b)}</b></li>' for a, b in nba["texas"])
    nn = lambda g, k: "".join(f'<li><a href="{esc(n["url"])}">{esc(n["short"])}</a></li>' for n in g["notable"][:k])
    H = lambda t, extra="": f'<div style="font-weight:900;font-size:7.8pt;letter-spacing:.06em;margin:2px 0 1px;color:#33404f">{t} {extra}</div>'
    pro = card("pro", "#264653", "NFL · NBA · MLB", "scores + notable", H("NFL WEEK 10", f'<a class="src" href="{esc(nfl["scoreSource"]["url"])}">NFL.com</a>') + f'<ul class="scores">{nf}</ul>' + H("NBA TUE NOV 17 + TEXAS TEAMS", f'<a class="src" href="{esc(nba["scoreSource"]["url"])}">Basketball-Ref</a>') + f'<ul class="scores">{nb}</ul><ul>{nn(nba, 1)}</ul>')
    mlbc = card("mlb", "#003f88", "MLB · Offseason, no scores", "hot stove", f'<ul>{nn(mlb, 2)}</ul>')
    # memes
    lvls = ""
    colors = {"Elementary": "#2a9d8f", "Middle School": "#8e6bbf", "High School": "#e76f51"}
    for lv in data["memes"]["levels"]:
        c = colors.get(lv["level"], "#333")
        mi = ""
        for it in lv["items"]:
            is_motw = it["id"] == data["memes"].get("memeOfTheWeek")
            conf = '<span class="cf">CONFIRM</span> ' if it.get("confirm") else ""
            tag = '<span class="tag">Meme of the Week</span> ' if is_motw else ""
            body = f'<a href="{esc(it["links"][0]["url"])}"><b>{esc(it["title"].replace(" (Meme of the Week)", ""))}</b></a> {tag}{conf}<br>{esc(it.get("pwhat") or it["what"])}<br><span class="tip" style="color:{c}">Say:</span> <span class="tip">{esc(it.get("ptip") or it["tip"])}</span>'
            mi += f'<div class="mi{" motw" if is_motw else ""}">{body}</div>'
        lvls += f'<div class="lv" style="border-color:{c}"><h3 style="color:{c}">{lv["icon"]} {esc(lv["level"])}</h3>{mi}</div>'
    memes = card("memes", "#ff7f50", "Meme of the Week", "what the kids are talking about", f'<div style="font-weight:800;margin-bottom:3px">{esc(data["memes"]["tagline"])}</div>{lvls}')
    foot_src = "Sources: NWS · RGVSports · KRGV · Texas Tribune · ABC · NFL.com · Basketball-Reference · MLB.com · Know Your Meme · full list in sources file"
    chk = data.get("linkCheck")
    chk_s = f" · Links checked {chk['date']}: {chk['ok']} ok, {chk['blocked']} bot-blocked, {chk['dead']} dead" if chk else ""
    html_ = f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(m["title"])} {esc(m["date"])}</title><style>{PRINT_CSS}</style></head><body><div class="page">
<header><img class="logo" src="{logo}"><div class="title"><div class="k">Monday Show Packet · 8 AM CT</div><div class="d">{esc(m["dateLabel"])}</div><div class="t">{esc(m["recap"])} · Live from McAllen, Texas</div></div><div class="badge">{('<span class="s">'+esc(m["sampleLabel"])+'</span>') if m.get("sample") else ''}<div class="n">{esc(m["tagline"])}</div><div class="n">{esc(m["handles"])}</div></div></header>
{clockhtml}
<div class="grid"><div class="col" style="flex:1">{headlines}{national}{onshow}</div><div class="col">{weather}{hsc}{pro}</div><div class="col">{memes}{mlbc}</div></div>
<footer><span>{esc(foot_src)}{esc(chk_s)}</span><span>Items are clickable links · CONFIRM = verify before air</span></footer>
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
    clock_leg = " · ".join(f'<b>{c["letter"]}</b> {esc(c["short"])} {c["start"]}' for c in data.get("showClock", []))
    rgv = "".join(li(A(i, i["title"]) + f' <span style="color:#66788c;font-size:12px">{esc(i["source"])}</span>') for i in data["headlines"]["rgv"])
    tx = "".join(li(A(i) + f' <span style="color:#66788c;font-size:12px">{esc(i["source"])}</span>') for i in data["headlines"]["texas"])
    img_html = f'<img src="{thumb_src}" width="160" align="right" style="border-radius:6px;margin:0 0 6px 10px" alt="Starship"><div style="font-size:11px;color:#66788c;clear:both">{esc(thumb["caption"])}</div>' if thumb else ""
    nat = ""
    for n in data["nationalDesk"]:
        conf = f' <b style="color:#c1121f">[CONFIRM BEFORE AIR: {esc(conf_text(n))}]</b>' if n.get("confirm") else ""
        lks = " · ".join(f'<a href="{esc(l["url"])}" style="color:#6d597a">{esc(l["label"])}</a>' for l in n["links"][:3])
        nat += f'<p style="margin:0 0 8px"><b>{esc(n["title"])}</b>{conf}<br>{esc(n["summary"])}<br><b style="color:#6d597a">Our take:</b> {esc(n["angle"])}<br><b style="color:#2a6f97">Why it matters in the Valley:</b> {esc(n["valley"])}<br><span style="font-size:12px">{lks}</span></p>'
    cells = "".join(f'<td align="center" style="{F}font-size:12px;padding:4px;border:1px solid #d5dde6;{"background:#fff3c4;" if d["date"]==w["monday"] else ""}"><b>{d["label"]} {d["dateLabel"].split()[1]}</b><br><span style="font-size:22px">{EMOJI[d["icon"]]}</span><br><b style="font-size:16px">{d["hi"]}°</b> / {d["lo"] if d["lo"] is not None else "–"}°<br><span style="color:#2a7de1">{d["pop"]}% rain</span></td>' for d in w["days"][:7])
    upd = datetime.datetime.fromisoformat(w["updated"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
    weather = f'<table width="100%" cellpadding="0" cellspacing="2"><tr>{cells}</tr></table><div style="font-size:12px;color:#4a5a6b;margin-top:4px">Source: <a href="{esc(w["pageUrl"])}">NWS {esc(w["office"])} forecast for McAllen</a>, updated {upd.strftime("%b %-d %-I:%M %p")} CT.</div>'
    hs = data["sports"]["highSchool"]
    hsb = "<ul style='margin:0;padding-left:18px'>" + "".join(li(A(r)) for r in hs["results"]) + "</ul><b>This week (area round):</b><ul style='margin:0;padding-left:18px'>" + "".join(li(A(r)) for r in hs["next"]) + f"</ul><div style='font-size:12px'>{A(hs['college'])}</div>"
    def lst(g, key="scores"):
        s = data["sports"][g]
        sc = "<br>".join(esc(b) for a, b in s.get("scores", []))
        nn = "<ul style='margin:6px 0 0;padding-left:18px'>" + "".join(li(A(i, i["short"] if False else i["title"])) for i in s["notable"]) + "</ul>"
        return sc, nn
    nfl = data["sports"]["nfl"]; nba = data["sports"]["nba"]; mlb = data["sports"]["mlb"]
    nflb = "<br>".join(esc(b) for a, b in nfl["scores"]) + f"<br><span style='font-size:12px'>Source: {A(nfl['scoreSource'], 'NFL.com')}</span>" + lst("nfl")[1]
    nbab = "<br>".join(esc(b) for a, b in nba["scores"]) + "<br><b>Texas teams:</b> " + ", ".join(esc(b) for a, b in nba["texas"]) + f"<br><span style='font-size:12px'>Source: {A(nba['scoreSource'], 'Basketball-Reference')}</span>" + lst("nba")[1]
    mlbb = f"<i>{esc(mlb['note'])}</i>" + lst("mlb")[1]
    memes = f'<div style="font-weight:bold;margin-bottom:6px">{esc(data["memes"]["tagline"])}. {esc(data["memes"]["intro"])}</div>'
    for lv in data["memes"]["levels"]:
        memes += f'<div style="font-weight:bold;font-size:15px;margin:8px 0 4px">{lv["icon"]} {esc(lv["level"])}</div>'
        for it in lv["items"]:
            tag = ' <span style="background:#e4572e;color:#fff;font-size:11px;padding:1px 5px;border-radius:3px">MEME OF THE WEEK</span>' if it["id"] == data["memes"].get("memeOfTheWeek") else ""
            conf = f' <b style="color:#c1121f">[CONFIRM BEFORE AIR: {esc(conf_text(it))}]</b>' if it.get("confirm") else ""
            lk = " · ".join(f'<a href="{esc(l["url"])}" style="color:#1b2430">{esc(l["label"])}</a>' for l in it["links"])
            memes += f'<p style="margin:0 0 8px"><b>{esc(it["title"])}</b>{tag}{conf}<br>{esc(it["what"])} <i>{esc(it["means"])}</i><br><b>How to bring it up:</b> {esc(it["tip"])}<br><span style="font-size:12px">{lk}</span></p>'
    rundown = "<ol style='margin:0;padding-left:20px'>" + "".join(f'<li style="margin-bottom:3px"><b>{esc(c["timeRange"])}</b> {esc(c["title"])} ({c["minutes"]} min{", flex" if c["flex"] else ""}{", Jess" if c["jess"] else ""})</li>' for c in data.get("showClock", [])) + "</ol>"
    body = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{esc(m["title"])}</title></head><body style="margin:0;padding:0;background:#fffdf6"><table width="100%" cellpadding="0" cellspacing="0" style="background:#fffdf6"><tr><td align="center"><table width="680" cellpadding="0" cellspacing="0" style="width:680px;max-width:100%">
<tr><td style="padding:12px 0"><table width="100%" cellpadding="0" cellspacing="0"><tr><td width="190"><img src="{logo_src}" width="180" alt="Drew in the Morning" style="background:#fff;border:2px solid #1b2430;border-radius:10px;padding:4px"></td><td style="{F}padding-left:12px"><div style="font-size:12px;letter-spacing:2px;font-weight:bold;color:#b5651d">MONDAY SHOW PACKET · 8 AM CT</div><div style="font-size:26px;font-weight:bold;color:#1b2430">{esc(m["dateLabel"])}</div><div style="font-size:13px;color:#4a5a6b">{esc(m["recap"])}</div>{('<div style="margin-top:4px"><span style="background:#e4572e;color:#fff;font-size:12px;font-weight:bold;padding:3px 9px;border-radius:99px">'+esc(m["sampleLabel"])+'</span></div>') if m.get("sample") else ''}</td></tr></table></td></tr>
<tr><td><table width="100%" cellpadding="0" cellspacing="0" style="border:1.5px solid #1b2430;border-radius:6px;border-collapse:separate"><tr>{clock}</tr></table><div style="{F}font-size:12px;color:#33404f;padding:3px 0">{clock_leg} (★ = signature segment; full 60-minute plan, blocks marked flex can be trimmed or stretched)</div></td></tr>
{sec("Top Headlines · RGV First", "#e4572e", img_html + "<ul style='margin:0;padding-left:18px'>" + rgv + "</ul><b>Texas:</b><ul style='margin:0;padding-left:18px'>" + tx + "</ul>")}
{sec("McAllen / RGV Weather", "#2a7de1", weather)}
{sec("RGV High School Football", "#2a9d8f", hsb)}
{sec("NFL · Week 10", "#264653", nflb)}
{sec("NBA", "#c1121f", nbab)}
{sec("MLB · Offseason (no scores)", "#003f88", mlbb)}
{sec("Meme of the Week · What the Kids Are Talking About", "#ff7f50", memes)}
{sec("The National Desk", "#6d597a", nat)}
{sec("On the Show: Monday's 60-minute plan", "#264653", rundown + '<div style="font-size:12px;color:#4a5a6b">Studio page and run of show have notes and links for every block.</div>')}
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
    W(bar); W("DREW IN THE MORNING · MONDAY SHOW PACKET"); W(m["dateLabel"].upper() + " · 8:00 AM CT · Live from McAllen, Texas")
    if m.get("sample"): W("*** " + m["sampleLabel"] + " ***")
    W(m["recap"]); W(m["tagline"]); W(bar); W()
    W("SHOW CLOCK (60 minutes; FLEX = can trim/stretch; * = signature segment)")
    for c in data.get("showClock", []):
        W(f"  {c['timeRange']:<11} {c['letter']}  {c['title']} ({c['minutes']} min{', FLEX ' + str(c['trimTo']) + '-' + str(c['stretchTo']) if c['flex'] else ''}{', Jess' if c['jess'] else ''}){' *' if c['signature'] else ''}")
    W()
    W("TOP HEADLINES · RGV FIRST")
    for i in data["headlines"]["rgv"]:
        W(wrap("- " + i["title"] + f" ({i['source']})")); W("    " + i["url"])
    W("  Texas:")
    for i in data["headlines"]["texas"]:
        W(wrap("- " + i["title"] + f" ({i['source']})")); W("    " + i["url"])
    W("  Photo: " + data["headlines"]["image"]["caption"] + " " + data["headlines"]["image"]["credit_url"]); W()
    W("THE NATIONAL DESK (smaller; local leads)")
    for n in data["nationalDesk"]:
        W(f"- {n['title'].upper()}"); W(wrap("FACT: " + n["summary"], "    ")); W(wrap("OUR TAKE: " + n["angle"], "    ")); W(wrap("WHY IT MATTERS IN THE VALLEY: " + n["valley"], "    "))
        if n.get("detail"): W(wrap("DETAIL: " + n["detail"], "    "))
        if n.get("confirm"): W(wrap("CONFIRM BEFORE AIR: " + conf_text(n), "    "))
        for l in n["links"]: W(f"    {l['label']}: {l['url']}")
    W()
    W("WEATHER · McALLEN / RGV (" + w["source"] + ")")
    for d in w["days"][:7]:
        W(f"  {d['label']} {d['dateLabel']:<7} {'<< SHOW DAY ' if d['date']==w['monday'] else ''}{d['short']}, high {d['hi']}F / low {d['lo'] if d['lo'] is not None else '--'}F, rain {d['pop']}%, wind {d['wind']}")
    W("  Alerts: " + ("none active" if w.get("alerts") == [] else (", ".join(w["alerts"]) if w.get("alerts") else "not checked")))
    W(f"  Updated {w['updated']} (UTC). Forecast page: {w['pageUrl']}"); W(f"  NWS Brownsville office: {w['officeUrl']}"); W(f"  API: {w['apiUrl']}"); W()
    hs = data["sports"]["highSchool"]
    W("RGV HIGH SCHOOL FOOTBALL PLAYOFFS · " + hs["round"])
    for r in hs["results"]:
        W(f"  - {r['title']}" + (f"  [CONFIRM BEFORE AIR: {conf_text(r)}]" if r.get("confirm") else "")); W("      " + r["url"])
    W("  This week (area round):")
    for r in hs["next"]:
        W(wrap("- " + r["title"], "    ")); W("      " + r["url"])
    W("  College: " + hs["college"]["title"] + "  " + hs["college"]["url"]); W()
    for g, label in (("nfl", "NFL · WEEK 10"), ("nba", "NBA")):
        s = data["sports"][g]
        W(label + "  (scores: " + s["scoreSource"]["url"] + ")")
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
    W(); W("ON THE SHOW: see run-of-show-monday.md (13 blocks, 60 minutes) and the studio page for notes, follow-up questions and links.")
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
:root{--bg:#fffdf6;--fg:#1b2430;--card:#fff;--line:#1b2430;--mut:#5a6b7d;--acc:#e4572e;--link:#0b5cad;--chip:#f1ece0}
[data-theme=dark]{--bg:#10151c;--fg:#eef2f6;--card:#1a222d;--line:#4c5d70;--mut:#9fb0c2;--link:#7cc0ff;--chip:#263140}
*{box-sizing:border-box}html{font-size:var(--fs,17px)}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Inter,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;line-height:1.4}
a{color:var(--link)}header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:3px solid var(--line);padding:8px 16px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
header img{height:64px;background:#fff;border-radius:10px;border:2px solid #1b2430;padding:2px 8px}
.ht .k{font-size:.72rem;letter-spacing:.14em;font-weight:800;color:#b5651d;text-transform:uppercase}.ht .d{font-size:1.55rem;font-weight:900;line-height:1.05}
.ht .t{font-size:.8rem;color:var(--mut);font-weight:600}.tools{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
button{font:inherit;cursor:pointer;border:2px solid var(--line);background:var(--chip);color:var(--fg);border-radius:8px;padding:4px 10px;font-weight:700}
button:hover{background:var(--acc);color:#fff}
.sample{background:var(--acc);color:#fff;border-radius:99px;padding:2px 10px;font-weight:800;font-size:.8rem}
nav{display:flex;gap:6px;flex-wrap:wrap;padding:8px 16px;background:var(--bg)}nav a{background:var(--chip);border-radius:99px;padding:3px 10px;font-weight:700;font-size:.85rem;text-decoration:none;color:var(--fg);border:1px solid var(--line)}
.clock{display:flex;margin:6px 16px;height:46px;border-radius:10px;overflow:hidden;border:2px solid var(--line)}
.clock a{display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;font-weight:900;text-decoration:none;border-right:1px solid rgba(255,255,255,.6);font-size:.85rem;line-height:1}.clock a small{font-size:.6rem;font-weight:700;opacity:.9}
main{padding:6px 16px 40px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:12px;align-items:start}
details{background:var(--card);border:2px solid var(--line);border-radius:12px;overflow:hidden}details.wide{grid-column:1/-1}
summary{cursor:pointer;list-style:none;padding:8px 12px;color:#fff;font-weight:900;letter-spacing:.06em;text-transform:uppercase;display:flex;justify-content:space-between;gap:8px}
summary::-webkit-details-marker{display:none}summary small{font-weight:600;text-transform:none;letter-spacing:0;opacity:.95}
summary:after{content:'\\25BE';margin-left:6px}details:not([open]) summary:after{content:'\\25B8'}
.body{padding:10px 14px}.item{display:flex;gap:8px;align-items:flex-start;padding:5px 0;border-bottom:1px dashed var(--line)}.item:last-child{border:0}
.item .tx{flex:1}.item .tx>a{font-weight:700}.src{color:var(--mut);font-size:.8rem;font-weight:600}
.cp{font-size:.7rem;padding:2px 7px;flex:none}.cf{display:inline-block;background:#c1121f;color:#fff;font-size:.7rem;font-weight:900;border-radius:4px;padding:0 5px}
.wk{display:grid;grid-template-columns:repeat(auto-fit,minmax(78px,1fr));gap:6px;text-align:center}.wk div{border:2px solid var(--line);border-radius:10px;padding:4px}.wk .mon{background:#fff3c4;border-color:#f2a900;color:#1b2430}
.hi{font-size:1.25rem;font-weight:900}.mut{color:var(--mut)}.pp{color:#2a7de1;font-weight:800}
.scores{columns:2;column-gap:20px;margin:0;padding:0;list-style:none}.scores li{padding:1px 0;break-inside:avoid}
.lvl{border-left:6px solid;padding-left:10px;margin:8px 0}.lvl h3{margin:0 0 4px;text-transform:uppercase;letter-spacing:.05em;font-size:.95rem}
.motw{background:#fff1e8;color:#1b2430;border:2px dashed #e4572e;border-radius:10px;padding:4px 8px}.motw a{color:#0b5cad}
.tag{background:#e4572e;color:#fff;font-weight:900;font-size:.7rem;padding:1px 6px;border-radius:4px}
.rd{border:2px solid var(--line);border-radius:10px;margin:6px 0;background:var(--card)}.rd>summary{border-radius:0}
.rd h4{margin:8px 0 3px;font-size:.85rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}.rd ul{margin:0;padding-left:20px}
.chy{display:inline-block;background:#1b2430;color:#fff;border-radius:6px;padding:2px 8px;margin:2px;font-size:.85rem}.chy b{color:#ffd23f}
#toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#1b2430;color:#fff;padding:8px 16px;border-radius:99px;font-weight:700;opacity:0;transition:.25s;pointer-events:none;z-index:9}#toast.on{opacity:1}
footer{padding:10px 16px 30px;color:var(--mut);font-size:.8rem}
@media print{header,nav,.tools{position:static}.cp{display:none}}
"""
STUDIO_JS = """
(function(){var r=document.documentElement,t=localStorage.getItem('ditm-theme')||(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');r.setAttribute('data-theme',t);
var fs=parseInt(localStorage.getItem('ditm-fs')||'17',10);r.style.setProperty('--fs',fs+'px');
function toast(m){var e=document.getElementById('toast');e.textContent=m;e.className='on';setTimeout(function(){e.className=''},1400)}
document.getElementById('theme').onclick=function(){t=t==='dark'?'light':'dark';r.setAttribute('data-theme',t);localStorage.setItem('ditm-theme',t)};
document.getElementById('bigger').onclick=function(){fs=Math.min(26,fs+2);r.style.setProperty('--fs',fs+'px');localStorage.setItem('ditm-fs',fs)};
document.getElementById('smaller').onclick=function(){fs=Math.max(13,fs-2);r.style.setProperty('--fs',fs+'px');localStorage.setItem('ditm-fs',fs)};
document.getElementById('expand').onclick=function(){document.querySelectorAll('details').forEach(function(d){d.open=true})};
document.getElementById('collapse').onclick=function(){document.querySelectorAll('main > details').forEach(function(d){d.open=false})};
function copy(u){if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(u).then(function(){toast('Link copied')},fb)}else fb();function fb(){var a=document.createElement('textarea');a.value=u;document.body.appendChild(a);a.select();try{document.execCommand('copy');toast('Link copied')}catch(e){toast(u)}a.remove()}}
document.addEventListener('click',function(e){var b=e.target.closest('.cp');if(b){e.preventDefault();copy(b.dataset.url)}
 var c=e.target.closest('[data-jump]');if(c){var d=document.getElementById(c.dataset.jump);if(d){var p=d.closest('details.sec');if(p)p.open=true;d.open=true;d.scrollIntoView({behavior:'smooth',block:'start'})}e.preventDefault()}});
})();
"""

def studio_html(data):
    m, w = data["meta"], data["weather"]
    logo = b64(asset("assets/DITM_SunLogo.png"), "image/png")
    A = lambda url, text, extra="": f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer" {extra}>{esc(text)}</a>'
    CP = lambda url: f'<button class="cp" data-url="{esc(url)}" title="Copy link" aria-label="Copy link">Copy link</button>'
    def item(it, text=None):
        conf = f' <span class="cf">CONFIRM BEFORE AIR</span> <span class="src">{esc(conf_text(it))}</span>' if it.get("confirm") else ""
        url = it.get("url") or ""
        main = A(url, text or it["title"]) if url else esc(text or it["title"])
        return f'<div class="item"><div class="tx">{main} <span class="src">{esc(it.get("source",""))}</span>{conf}</div>{CP(url) if url else ""}</div>'
    def sec(id_, color, title, sub, body, wide=False, open_=True):
        return f'<details class="sec{" wide" if wide else ""}" id="{id_}"{" open" if open_ else ""}><summary style="background:{color}"><span>{title}</span><small>{sub}</small></summary><div class="body">{body}</div></details>'
    clock = data.get("showClock", [])
    clockbar = "".join(f'<a href="#blk-{c["letter"]}" data-jump="blk-{c["letter"]}" style="width:{c["minutes"]/60*100:.3f}%;background:{c["color"]}" title="{esc(c["title"])} · {c["timeRange"]}">{c["letter"]}{"★" if c["signature"] else ""}<small>{c["minutes"]}m</small></a>' for c in clock)
    thumb = data["headlines"].get("image")
    thumbhtml = f'<img src="{b64(asset(thumb["file"]), "image/jpeg")}" alt="Starship file photo" style="float:right;width:160px;border-radius:8px;margin:0 0 6px 10px"><div class="src" style="clear:both">{esc(thumb["caption"])} · {A(thumb["credit_url"], "source")}</div>' if thumb else ""
    heads = thumbhtml + "".join(item(i) for i in data["headlines"]["rgv"]) + '<div class="src" style="margin-top:6px;font-weight:800">TEXAS</div>' + "".join(item(i) for i in data["headlines"]["texas"])
    nat = ""
    for n in data["nationalDesk"]:
        lks = "".join(f'<div class="item"><div class="tx">{A(l["url"], l["label"])}</div>{CP(l["url"])}</div>' for l in n["links"])
        conf = f' <span class="cf">CONFIRM BEFORE AIR</span> <span class="src">{esc(conf_text(n))}</span>' if n.get("confirm") else ""
        nat += f'<details class="rd" open><summary style="background:#6d597a"><span>{esc(n["title"])}</span><small>click to collapse</small></summary><div class="body"><p><b>Fact:</b> {esc(n["summary"])}{conf}</p><p><b style="color:#b07dd6">Our take:</b> {esc(n["angle"])}</p><p><b style="color:#5aa9e6">Why it matters in the Valley:</b> {esc(n["valley"])}</p><p class="mut">{esc(n.get("detail",""))}</p>{lks}</div></details>'
    cells = "".join(f'<div class="{"mon" if d["date"]==w["monday"] else ""}"><b>{d["label"]} {d["dateLabel"]}</b><br>{icon(d["icon"], 44)}<div class="hi">{d["hi"]}°</div><div class="mut">{d["lo"] if d["lo"] is not None else "–"}°</div><div class="pp">{d["pop"]}% rain</div><div class="mut" style="font-size:.75rem">{esc(d["short"])}</div></div>' for d in w["days"][:7])
    upd = datetime.datetime.fromisoformat(w["updated"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
    alerts = "No active NWS alerts." if w.get("alerts") == [] else ("Alerts: " + ", ".join(w["alerts"]) if w.get("alerts") else "")
    weather = f'<div class="wk">{cells}</div><p>{alerts} Updated {upd.strftime("%b %-d %-I:%M %p")} CT.</p>' + "".join(f'<div class="item"><div class="tx">{A(u, t)}</div>{CP(u)}</div>' for t, u in (("NWS forecast page for McAllen", w["pageUrl"]), ("NWS Brownsville office (BRO)", w["officeUrl"]), ("NWS API forecast (JSON)", w["apiUrl"])))
    hs = data["sports"]["highSchool"]
    hsb = f'<p class="mut">{esc(hs["sourceNote"])}</p><div class="scores">' + "".join(item(r) for r in hs["results"]) + '</div><b>This week (area round)</b>' + "".join(item(r) for r in hs["next"]) + item(hs["college"])
    def scorebox(g, extra=""):
        s = data["sports"][g]
        sc = '<ul class="scores">' + "".join(f"<li>{esc(b)} <span class='mut'>{esc(a)}</span></li>" for a, b in s["scores"]) + "</ul>"
        if g == "nba": sc += "<b>Texas teams</b><ul class='scores'>" + "".join(f"<li>{esc(b)} <span class='mut'>{esc(a)}</span></li>" for a, b in s["texas"]) + "</ul>"
        return sc + item(s["scoreSource"], "Scores: " + s["scoreSource"]["title"]) + "".join(item(n) for n in s["notable"])
    mlb = data["sports"]["mlb"]
    sports_nfl = scorebox("nfl"); sports_nba = scorebox("nba")
    sports_mlb = f'<p><i>{esc(mlb["note"])}</i></p>' + "".join(item(n) for n in mlb["notable"])
    colors = {"Elementary": "#2a9d8f", "Middle School": "#8e6bbf", "High School": "#e76f51"}
    mem = f'<p><b>{esc(data["memes"]["tagline"])}</b><br>{esc(data["memes"]["intro"])}</p>'
    for lv in data["memes"]["levels"]:
        c = colors.get(lv["level"], "#888")
        mem += f'<div class="lvl" style="border-color:{c}"><h3 style="color:{c}">{lv["icon"]} {esc(lv["level"])}</h3>'
        for it in lv["items"]:
            is_motw = it["id"] == data["memes"].get("memeOfTheWeek")
            conf = f' <span class="cf">CONFIRM BEFORE AIR</span> <span class="src">{esc(conf_text(it))}</span>' if it.get("confirm") else ""
            lks = "".join(f'<div class="item"><div class="tx">{A(l["url"], l["label"])}</div>{CP(l["url"])}</div>' for l in it["links"])
            mem += f'<div class="{"motw" if is_motw else ""}"><p><b>{esc(it["title"])}</b> {"<span class=tag>Meme of the Week</span>" if is_motw else ""}{conf}<br>{esc(it["what"])} <i>{esc(it["means"])}</i><br><b>How to bring it up:</b> {esc(it["tip"])}</p>{lks}</div>'
        mem += "</div>"
    rd = ""
    for r in data.get("rundown", []):
        chy = "".join(f'<span class="chy"><b>{esc(c["primary"])}</b> · {esc(c["secondary"])}</span>' for c in r["chyrons"])
        lis = lambda xs: "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in xs) + "</ul>"
        lks = "".join(f'<div class="item"><div class="tx">{(A(l["url"], l["label"]) if l["url"].startswith("http") else esc(l["label"] + " (" + l["url"] + ")"))}</div>{CP(l["url"]) if l["url"].startswith("http") else ""}</div>' for l in r["links"])
        flex = f'FLEX: trim to {r["trimTo"]} / stretch to {r["stretchTo"]} min' if r["flex"] else "fixed"
        conf = f'<h4>Confirm before air</h4><p><span class="cf">CONFIRM</span> {esc("; ".join(r["confirm"]))}</p>' if r["confirm"] else ""
        rd += f'<details class="rd" id="blk-{r["letter"]}"><summary style="background:{r["color"]}"><span>{r["letter"]} · {esc(r["title"])}{" ★" if r["signature"] else ""}</span><small>{r["timeRange"]} · {r["minutes"]} min · {flex}{" · Jess" if r["jess"] else ""}</small></summary><div class="body"><p class="mut">{esc(r["subject"])}</p><h4>Talking points</h4>{lis(r["talkingPoints"])}<h4>Follow-up questions</h4>{lis(r["followUps"]) if r["followUps"] else "<p class=mut>none</p>"}<h4>Transition lines</h4>{lis(r["transitions"]) if r["transitions"] else "<p class=mut>none</p>"}<h4>Chyrons (60 chars max)</h4><p>{chy}</p><h4>Sources</h4>{lks}{conf}</div></details>'
    nav = "".join(f'<a href="#{i}" data-jump="{i}">{t}</a>' for i, t in (("rundown", "Rundown"), ("headlines", "Headlines"), ("national", "National"), ("weather", "Weather"), ("hs", "HS Football"), ("nfl", "NFL"), ("nba", "NBA"), ("mlb", "MLB"), ("memes", "Meme of the Week")))
    body = "".join([
        sec("rundown", "#264653", "Full 60-Minute Rundown", "click a block to expand its notes, questions, chyrons and links", rd, wide=True),
        sec("headlines", "#e4572e", "Top Headlines · RGV First", "week + weekend", heads),
        sec("national", "#6d597a", "The National Desk", "fact · take · Valley angle", nat),
        sec("weather", "#2a7de1", "McAllen / RGV Weather", w["source"], weather),
        sec("hs", "#2a9d8f", "RGV High School Football", hs["round"], hsb),
        sec("nfl", "#264653", "NFL · Week 10", "scores + notable", sports_nfl),
        sec("nba", "#c1121f", "NBA", "Tue Nov 17 + Texas teams", sports_nba),
        sec("mlb", "#003f88", "MLB · Offseason (no scores)", "hot stove", sports_mlb),
        sec("memes", "#ff7f50", "Meme of the Week · What the Kids Are Talking About", "for parents", mem, wide=True)])
    segs = "".join(f"<li>{esc(s)}</li>" for s in data.get("segues", []))
    chk = data.get("linkCheck")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(m["title"])} · {esc(m["date"])} · Studio</title><style>{STUDIO_CSS}</style></head><body>
<header><img src="{logo}" alt="Drew in the Morning"><div class="ht"><div class="k">Studio page · Monday 8 AM CT</div><div class="d">{esc(m["dateLabel"])}</div><div class="t">{esc(m["recap"])} · {esc(m["tagline"])}</div></div>{('<span class="sample">'+esc(m["sampleLabel"])+'</span>') if m.get("sample") else ''}
<div class="tools"><button id="theme" title="Toggle dark/light">Dark / Light</button><button id="smaller">A−</button><button id="bigger">A+</button><button id="expand">Expand all</button><button id="collapse">Collapse all</button></div></header>
<nav>{nav}</nav><div class="clock" aria-label="60 minute show clock">{clockbar}</div>
<main>{body}</main>
<footer><b>Segue ideas:</b><ul>{segs}</ul>Every item links to its source and opens in a new tab; Copy link puts the URL on your clipboard for sharing on screen. CONFIRM BEFORE AIR = verify first. No trackers, no external scripts or fonts: this page works offline (links need internet).{(" Links checked "+chk["date"]+": "+str(chk["ok"])+" ok, "+str(chk["blocked"])+" bot-blocked, "+str(chk["dead"])+" dead.") if chk else ""}</footer>
<div id="toast" role="status"></div><script>{STUDIO_JS}</script></body></html>"""

# ---------------------------------------------------------------- render
def run(cmd, **k): return subprocess.run(cmd, capture_output=True, text=True, **k)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--obs-data", default=os.path.join(HERE, "..", "obs-data.json"))
    ap.add_argument("--refresh-weather", action="store_true"); ap.add_argument("--check-links", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="skip Chrome (PDF/PNG/screenshot)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    data = prepare(json.load(open(a.data)), a.obs_data, a.refresh_weather)
    stem = os.path.join(a.out, data["meta"]["fileStem"])
    urls = all_urls(data)
    if a.check_links:
        det = check_links(sorted({u["url"] for u in urls if u["url"].startswith("http")}))
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
    if a.no_render: return
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
    print("built:", stem + ".*")

if __name__ == "__main__":
    main()
