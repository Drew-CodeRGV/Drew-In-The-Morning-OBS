#!/usr/bin/env python3
"""Tech-wire candidates for the "What's Happening in Tech" section (fallback only).

The section is built from Drew's Fast Company Daily email (read through the Gmail connector by the daily
refresh). When no issue from the last 48 hours exists, the refresh picks 3-5 stories from this list instead
and labels them as a fallback. This script only LISTS candidates (title, link, outlet, time, the feed's own
summary text); it never writes the packet and never invents a summary.

    python3 tools/tech_wires.py                 # JSON, newest first, last 48 h
    python3 tools/tech_wires.py --hours 24 --limit 6 --text
"""
from __future__ import annotations
import argparse, datetime, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trend_score as ts  # noqa: E402
import breaking_watch as bw  # noqa: E402
import ditm_yaml  # noqa: E402

ROOT = os.path.dirname(HERE)


def load_feeds(path: str | None = None) -> list[dict]:
    cfg = ditm_yaml.load(path or os.path.join(ROOT, "feeds.yml"))
    return [f for f in (cfg.get("tech_feeds") or []) if f.get("enabled") is not False]


def _summary(it: dict) -> str:
    t = re.sub(r"<[^>]+>", " ", it.get("text") or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()[:400]


def candidates(feeds: list[dict], now: datetime.datetime | None = None, hours: float = 48, fetch=ts.fetch_url) -> tuple[list[dict], dict]:
    """Return (items newest first, per-feed status). Items older than `hours` are dropped; undated items are kept last."""
    now = now or datetime.datetime.now(ts.UTC)
    out, status = [], {}
    for f in feeds:
        code, body = fetch(f["url"])
        if code != 200 or not body:
            status[f["id"]] = {"ok": False, "status": f"HTTP {code}", "items": 0}
            continue
        try:
            items = bw.parse_feed(body, {"id": f["id"], "name": f["name"], "kind": "national"})
        except ValueError as e:
            status[f["id"]] = {"ok": False, "status": f"parse error: {e}", "items": 0}
            continue
        n = 0
        for it in items:
            when = ts.parse_dt(it.get("published"))
            if when and (now - when).total_seconds() > hours * 3600:
                continue
            n += 1
            out.append({"title": it["title"], "url": it["url"], "source": f["name"], "published": it.get("published") or "",
                        "summary": _summary(it), "_t": when})
        status[f["id"]] = {"ok": True, "status": "ok", "items": n}
    floor = datetime.datetime.min.replace(tzinfo=ts.UTC)
    out.sort(key=lambda x: x["_t"] or floor, reverse=True)
    for x in out:
        x.pop("_t", None)
    return out, status


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hours", type=float, default=48)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--text", action="store_true", help="one line per item instead of JSON")
    ap.add_argument("--feeds", default=None)
    a = ap.parse_args(argv)
    items, status = candidates(load_feeds(a.feeds), hours=a.hours)
    items = items[: a.limit]
    if a.text:
        for i in items:
            print(f'{i["published"][:25]:25} {i["source"]:14} {i["title"][:90]}  {i["url"]}')
        print({k: v["status"] for k, v in status.items()}, file=sys.stderr)
    else:
        json.dump({"fetchedAt": datetime.datetime.now(ts.UTC).isoformat(timespec="seconds"), "status": status, "items": items}, sys.stdout, indent=2, ensure_ascii=False)
        print()
    return 0 if any(s["ok"] for s in status.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
