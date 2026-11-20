#!/usr/bin/env python3
"""Obituaries from The Monitor (McAllen, TX) on Legacy.com, for the "Remembering Our Neighbors" section.

Source page (the one Drew linked):
    https://www.legacy.com/us/obituaries/local/texas/mcallen?publisher=The+Monitor

Legacy renders that page with Next.js and embeds the search results it shows as JSON inside the page itself
(the `self.__next_f.push` payload). This tool reads that embedded JSON from the public page, newest first, one
`&page=N` at a time, and keeps people whose obituary ran in The Monitor inside the window. It does NOT call any
API, log in, or open the individual obituary pages.

Per person it keeps ONLY: name, age (if listed), city (if the notice leads with it), date of death, the date The
Monitor ran the notice, funeral home (if listed), and the Legacy link. It never stores the obituary text, so no
cause of death, family detail or photo ever reaches the packet. A field that is not listed stays blank; nothing
is inferred or invented.

    python3 tools/obituaries.py --days 7            # JSON block for packet data["obituaries"]
    python3 tools/obituaries.py --days 14 --text    # readable list
    python3 tools/obituaries.py --days 7 --out /tmp/obits.json

Exit codes: 0 ok (even if zero found), 2 Legacy could not be read (blocked / changed / network). On exit 2 the
refresh should leave the previous `obituaries` block out and say so, never fill the section from memory.
"""
from __future__ import annotations
import argparse, datetime, html as html_mod, json, re, subprocess, sys, time, unicodedata, urllib.error, urllib.request

SOURCE_URL = "https://www.legacy.com/us/obituaries/local/texas/mcallen?publisher=The+Monitor"
PUBLISHER_SITE = "themonitor"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
TODAY_TZ = "America/Chicago"
MAX_PAGES = 8
FH_WORDS = ("funeral", "mortuary", "funeraria", "cremation", "memorial chapel")


class LegacyError(Exception):
    pass


# ---------- fetch ----------
def fetch(url: str, timeout: int = 30, retries: int = 1) -> tuple[int, str]:
    """GET one public Legacy page with a normal browser User-Agent. Uses the box's `curl` (Legacy's Cloudflare answers
    Python's urllib with a bot challenge, 403, but serves the same public page to curl with a browser User-Agent).
    Returns (status, body); (403, "") means Legacy challenged us, so a real browser is needed."""
    last = (0, "")
    for _ in range(retries + 1):
        try:
            r = subprocess.run(["curl", "-sL", "-m", str(timeout), "-A", UA, "-H", "Accept: text/html,application/xhtml+xml",
                                "-w", "\n%{http_code}", url], capture_output=True, timeout=timeout + 10)
            out = r.stdout.decode("utf-8", "replace")
            body, _, code = out.rpartition("\n")
            last = (int(code) if code.strip().isdigit() else 0, body if code.strip() == "200" else "")
            if last[0] == 200 or last[0] in (401, 403, 404, 410):
                break
        except FileNotFoundError:  # no curl: try urllib (may be challenged)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status, resp.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                return e.code, ""
            except Exception:
                return 0, ""
        except Exception:
            last = (0, "")
        time.sleep(1)
    return last


# ---------- parse ----------
_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)


def _flight_text(html: str) -> str:
    out = []
    for m in _PUSH.finditer(html):
        try:
            out.append(json.loads('"' + m.group(1) + '"'))
        except ValueError:
            continue
    return "".join(out)


def parse_page(html: str) -> tuple[list[dict], dict]:
    """Return (raw person records exactly as Legacy embeds them, paging info). Raises LegacyError if absent."""
    t = _flight_text(html)
    k = t.find('"full_name"')
    if k < 0:
        raise LegacyError("no obituary data found in the page (Legacy may have changed the page or served a block page)")
    j = t.rfind('[{"id"', 0, k)
    if j < 0:
        raise LegacyError("obituary list start not found")
    try:
        arr, _ = json.JSONDecoder().raw_decode(t[j:])
    except ValueError as e:
        raise LegacyError(f"obituary list is not valid JSON: {e}")
    paging = {}
    m = re.search(r'"page":(\d+),"page_size":(\d+),"total_pages":(\d+)(?:,"has_next":(true|false))?', t)
    if m:
        paging = {"page": int(m.group(1)), "page_size": int(m.group(2)), "total_pages": int(m.group(3))}
    return arr, paging


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _bio(p: dict) -> str:
    return html_mod.unescape(re.sub(r"<[^>]+>", " ", p.get("bio") or ""))


def _age(p: dict) -> int | None:
    """Only an age the notice itself states. Babies ("0", "1 Month") and anything unclear stay blank."""
    a = p.get("age")
    if isinstance(a, int) and 0 < a < 125:
        return a
    bio = _bio(p)[:220]
    for pat in (r",\s*(\d{1,3}),\s", r"^[^,]{3,70}?\s(\d{1,3}),\s+(?:died|passed)", r"\bat the age of (\d{1,3})\b", r"\bde (\d{1,3}) años"):
        m = re.search(pat, bio)
        if m and 0 < int(m.group(1)) < 125:
            return int(m.group(1))
    return None


def _city(p: dict) -> str:
    """The notice's own dateline ("Pharr - ...", "EDINBURG- ..."), when it has one. Never guessed from other fields."""
    m = re.match(r"^([A-Za-z][A-Za-z.'’ ]{1,28}?)\s?[-–—]\s", _bio(p).strip())
    if not m:  # "... of Mission, Texas passed away ..." in the notice's opening words
        m = re.search(r"\bof ([A-Z][a-z]+(?: [A-Z][a-z]+)?), (?:Texas|TX)\b", _bio(p)[:160])
        if not m:
            return ""
    c = _clean(m.group(1))
    return c.title() if c.isupper() else c


def _funeral_home(p: dict) -> str:
    for o in p.get("obituaries") or []:
        for af in o.get("affiliates") or []:
            n = _clean(af.get("publisher_name"))
            if n and any(w in n.lower() for w in FH_WORDS):
                return n.rstrip(" -").strip()
    bio = re.sub(r"\b(Tx|TX|Tex)\.(?= is| are)", "TX", _bio(p))
    m = re.search(r"([A-Z][^.\d]{3,80}?) (?:is|are) in charge", bio)
    if m:
        c = _clean(m.group(1)).replace(" @ ", " at ")
        low = c.lower()
        if any(w in low for w in FH_WORDS) and len(c) <= 60 and not any(w in low for w in ("www", "cemetery", "mausoleum", "church", "chapel of", " in ")):
            return c
    return ""


def normalize(p: dict) -> dict | None:
    """One Legacy person record -> our compact record, or None when The Monitor did not run a notice for them."""
    runs = []
    for o in p.get("obituaries") or []:
        for af in o.get("affiliates") or []:
            if af.get("site_name") == PUBLISHER_SITE and af.get("url", "").startswith("https://www.legacy.com/"):
                runs.append((o.get("date_posted_from") or "", af["url"]))
    runs = [r for r in runs if re.match(r"^\d{4}-\d{2}-\d{2}$", r[0])]
    name = _clean(p.get("full_name"))
    if not runs or not name:
        return None
    runs.sort()
    died = p.get("death_date") or ""
    return {
        "id": str(p.get("id") or p.get("person_id") or ""),
        "name": name,
        "age": _age(p),
        "city": _city(p),
        "died": died if re.match(r"^\d{4}-\d{2}-\d{2}$", died) else "",
        "published": runs[-1][0],          # most recent day The Monitor ran it
        "firstPublished": runs[0][0],
        "funeralHome": _funeral_home(p),
        "url": runs[-1][1],
    }


def _tokens(name: str) -> set[str]:
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\(.*?\)", " ", n)
    return {t for t in re.findall(r"[a-z]+", n) if t not in ("sr", "jr", "ii", "iii", "de", "la", "del", "los", "las")}


def merge_duplicates(rows: list[dict]) -> tuple[list[dict], int]:
    """Legacy sometimes has two or three person records for one notice (same death date, name spelled fuller or
    shorter). Merge those: same non-blank death date AND one name's words (2 or more) are all inside the other's."""
    rows = sorted(rows, key=lambda r: -len(_tokens(r["name"])))
    kept, merged = [], 0
    for r in rows:
        t = _tokens(r["name"])
        dup = None
        for k in kept:
            if r["died"] and r["died"] == k["died"] and len(t) >= 2 and t <= _tokens(k["name"]):
                dup = k
                break
        if dup:
            merged += 1
            dup["published"] = max(dup["published"], r["published"])
            for f in ("age", "city", "funeralHome"):
                dup[f] = dup[f] or r[f]
        else:
            kept.append(r)
    return kept, merged


# ---------- collect ----------
def today_chicago(now: datetime.datetime | None = None) -> datetime.date:
    if now is None:
        try:
            from zoneinfo import ZoneInfo
            now = datetime.datetime.now(ZoneInfo(TODAY_TZ))
        except Exception:
            now = datetime.datetime.now()
    return now.date()


def collect(days: int = 7, today: datetime.date | None = None, fetcher=fetch, max_pages: int = MAX_PAGES) -> dict:
    """Walk the listing newest first until a whole page is older than the window. `days` counts today, so days=7 on
    Nov 19 keeps Nov 13 through Nov 19 and days=14 keeps Nov 6 through Nov 19. Dates are the day The Monitor ran the notice."""
    today = today or today_chicago()
    start = today - datetime.timedelta(days=days - 1)
    people: dict[str, dict] = {}
    pages_read, total_pages = 0, None
    for page in range(1, max_pages + 1):
        url = SOURCE_URL + (f"&page={page}" if page > 1 else "")
        code, html = fetcher(url)
        if code != 200 or not html:
            if page == 1:
                raise LegacyError(f"Legacy returned HTTP {code} for the listing page")
            break
        raw, paging = parse_page(html)
        pages_read += 1
        total_pages = paging.get("total_pages", total_pages)
        newest = ""
        for p in raw:
            r = normalize(p)
            if not r:
                continue
            newest = max(newest, r["published"])
            if r["id"] and r["id"] not in people:
                people[r["id"]] = r
        # Rows inside a page are newest-first, but pages can overlap, so stop only when a full page is outside the window.
        if not raw or (newest and newest < start.isoformat()):
            break
    items = [r for r in people.values() if start.isoformat() <= r["published"] <= today.isoformat()]
    items, merged = merge_duplicates(items)
    items.sort(key=lambda r: r["name"].lower())
    items.sort(key=lambda r: r["published"], reverse=True)
    return {
        "source": "Legacy.com · The Monitor (McAllen, TX)",
        "sourceUrl": SOURCE_URL,
        "window": {"from": start.isoformat(), "to": today.isoformat(), "days": days},
        "fetchedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "pagesRead": pages_read,
        "mergedDuplicates": merged,
        "items": items,
    }


def to_text(block: dict) -> str:
    w = block["window"]
    lines = [f'Remembering Our Neighbors · {len(block["items"])} obituaries in The Monitor, {w["from"]} to {w["to"]}', block["sourceUrl"], ""]
    for r in block["items"]:
        bits = [r["name"] + (f', {r["age"]}' if r.get("age") else "")]
        if r.get("city"): bits.append(r["city"])
        if r.get("died"): bits.append("died " + r["died"])
        bits.append("ran " + r["published"])
        if r.get("funeralHome"): bits.append(r["funeralHome"])
        lines.append(" · ".join(bits) + "\n    " + r["url"])
    return "\n".join(lines)


# ---------- grouping + on-air read (used by packet/build_packet.py) ----------
def _d(s: str) -> datetime.date:
    return datetime.date.fromisoformat(s)


def _md(d: datetime.date) -> str:
    return f"{d.strftime('%b')} {d.day}"


def span_label(a: datetime.date, b: datetime.date) -> str:
    if a == b:
        return _md(a)
    return f"{_md(a)}\u2013{b.day}" if a.month == b.month else f"{_md(a)} \u2013 {_md(b)}"


def week_groups(items: list[dict], to: str | None = None, start: str | None = None) -> list[dict]:
    """Group by 7-day blocks counting back from `to` (the day the list was pulled), newest block first, newest notice first
    inside a block. Returns [{label, from, to, items}]; empty blocks are dropped."""
    rows = [r for r in items if r.get("published")]
    if not rows:
        return []
    end = _d(to) if to else max(_d(r["published"]) for r in rows)
    blocks: dict[int, list[dict]] = {}
    for r in rows:
        k = max(0, (end - _d(r["published"])).days // 7)
        blocks.setdefault(k, []).append(r)
    out = []
    for k in sorted(blocks):
        hi = end - datetime.timedelta(days=7 * k)
        lo = hi - datetime.timedelta(days=6)
        if start and _d(start) > lo:
            lo = _d(start)
        grp = sorted(blocks[k], key=lambda r: r["name"].lower())
        grp.sort(key=lambda r: r["published"], reverse=True)
        out.append({"label": span_label(lo, hi), "from": lo.isoformat(), "to": hi.isoformat(), "items": grp})
    return out


def read_picks(items: list[dict], to: str | None = None, n: int = 6) -> list[dict]:
    """The handful to read on air: from the newest 7 days, newest first, preferring notices that list both an age and a town."""
    groups = week_groups(items, to)
    first = groups[0]["items"] if groups else []
    full = [r for r in first if r.get("age") and r.get("city")]
    rest = [r for r in first if r not in full]
    return (full + rest)[:n]


def read_phrase(r: dict) -> str:
    s = r["name"]
    if r.get("age"):
        s += f", {r['age']}"
    if r.get("city"):
        s += f", of {r['city']}"
    return s


def read_script(items: list[dict], to: str | None = None, n: int = 6) -> str:
    """A short, gentle read. Names, ages and towns exactly as the notices list them; never a cause of death."""
    picks = read_picks(items, to, n)
    if not picks:
        return ""
    names = "; ".join(read_phrase(r) for r in picks)
    return ("We want to take a moment to remember some of our neighbors we lost over the past week. " + names + ". "
            "Our thoughts are with their families and friends. You'll find these and more in The Monitor's obituaries on Legacy dot com.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--days", type=int, default=7, help="window in days, counting today (7 = today and the 6 days before)")
    ap.add_argument("--text", action="store_true", help="print a readable list instead of JSON")
    ap.add_argument("--out", help="also write the JSON block to this file")
    a = ap.parse_args(argv)
    try:
        block = collect(a.days)
    except LegacyError as e:
        print(f"obituaries: could not read Legacy: {e}", file=sys.stderr)
        return 2
    if a.out:
        with open(a.out, "w") as f:
            json.dump(block, f, indent=2, ensure_ascii=False)
    print(to_text(block) if a.text else json.dumps(block, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
