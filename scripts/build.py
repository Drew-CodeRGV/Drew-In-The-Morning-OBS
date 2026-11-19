#!/usr/bin/env python3
"""Regenerate OBS text files from obs-data.json.

Edit obs-data.json, then run this. Do not hand-edit the generated folders;
the next build replaces them.

    python scripts/build.py
    python scripts/build.py --check
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import obsio
import render

SUPPORTED_SCHEMAS = {1, 2, 3, 4}

# Handles that are safe to put on a pre-show card. Anything else in show.socials
# (an inbox that still says "confirm", for example) stays in the segment index.
# facebookPageId is a numeric id, not a handle, so it stays off the pre-show card.
ON_AIR_SOCIAL_KEYS = ("instagram", "tiktok", "youtube", "facebook", "x")

SOCIAL_LABELS = {
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube": "YouTube",
    "facebook": "Facebook",
    "facebookPageId": "Facebook",
    "x": "X",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build OBS text files from obs-data.json")
    parser.add_argument("--root", help="Repository root (defaults to the parent of scripts/)")
    parser.add_argument("--data", help="Path to obs-data.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate obs-data.json and print a count. Do not write files.",
    )
    args = parser.parse_args(argv)
    root = obsio.repo_root(args.root)
    source = obsio.data_path(root, args.data)
    try:
        data = obsio.load_json(source)
        plan = plan_outputs(data)
    except obsio.DataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.check:
        print(_summary(plan))
        return 0
    try:
        written = write_outputs(root, plan)
        state = render.refresh(root)
    except obsio.DataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(_summary(plan))
    print(f"Wrote {len(written)} files under {root}")
    print(render.describe(root, obsio.load_json(obsio.playlist_path(root)), state))
    return 0


def plan_outputs(data: dict) -> dict:
    _require_schema(data)
    limit = data.get("chyronMaxChars", 60)
    if not isinstance(limit, int) or limit < 1:
        raise obsio.DataError("chyronMaxChars must be a positive integer")
    show = _require_object(data, "show")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise obsio.DataError("segments must be a non-empty list")

    title = _require_text(show, "title", "show.title")
    show_chyrons = _show_chyrons(show, limit)
    call_ins = _call_ins(data, limit)
    for item in call_ins["chyrons"]:
        item["pool"] = "call"
    show_chyrons = show_chyrons + call_ins["chyrons"]
    _unique(show_chyrons, "id", "show or call-in chyron id")
    _unique(show_chyrons, "token", "show or call-in chyron filename")
    schema = data.get("schemaVersion", 1)
    segment_plans = [_segment_plan(segment, limit, schema) for segment in segments]
    _unique(segment_plans, "order", "segment order")
    _unique(segment_plans, "id", "segment id")
    _unique(segment_plans, "token", "segment filename")
    letters = [segment["letter"] for segment in segment_plans if segment["letter"]]
    if len(letters) != len(set(letters)):
        raise obsio.DataError("Two segments share a block letter")
    segue_count = _segue_count(data)

    ticker = show.get("tickerHeadlines", [])
    if not isinstance(ticker, list) or not all(isinstance(item, str) for item in ticker):
        raise obsio.DataError("show.tickerHeadlines must be a list of strings")

    return {
        "limit": limit,
        "generated": data.get("generated") or "",
        "disclaimer": show.get("disclaimer") or "",
        "show": {
            "title": title,
            "subtitle": _optional_text(show.get("subtitle")),
            "episodeDate": show.get("episodeDate") or "",
            "startTime": show.get("startTime") or "",
            "timezone": show.get("timezone") or "",
            "socials": show.get("socials") if isinstance(show.get("socials"), dict) else {},
            "format": _optional_text(show.get("format")),
            "cards": show.get("cards") if isinstance(show.get("cards"), dict) else {},
            "chyrons": show_chyrons,
        },
        "ticker": [obsio.one_line(item) for item in ticker if obsio.one_line(item)],
        "segments": segment_plans,
        "promoLines": call_ins["promoLines"],
        "channels": call_ins["channels"],
        "segueCount": segue_count,
    }


def write_outputs(root: Path, plan: dict) -> list[Path]:
    written: list[Path] = []

    def emit(relative: str, text: str) -> str:
        path = root / relative
        obsio.atomic_write(path, text)
        written.append(path)
        return relative

    for item in plan["show"]["chyrons"]:
        item["file"] = emit(
            f"chyrons/show-{item['token']}.txt",
            obsio.chyron_body(item["primary"], item["secondary"]),
        )
    for segment in plan["segments"]:
        order = f"{segment['order']:02d}"
        token = segment["token"]
        segment["titleFile"] = emit(
            f"segment-titles/{order}-{token}.txt",
            f"{segment['title']}\n",
        )
        headline_files = []
        for index, headline in enumerate(segment["headlines"], start=1):
            headline_files.append(
                emit(f"headlines/{order}-{token}-{index:02d}.txt", f"{headline}\n")
            )
        segment["headlineFiles"] = headline_files
        chyron_files = []
        for chyron in segment["chyrons"]:
            chyron_files.append(
                emit(
                    f"chyrons/{order}-{token}-{chyron['token']}.txt",
                    obsio.chyron_body(chyron["primary"], chyron["secondary"]),
                )
            )
        segment["chyronFiles"] = chyron_files

    emit("ticker/ticker.txt", _ticker_text(plan["ticker"]))
    for relative, text in _scene_files(plan).items():
        emit(relative, text)
    emit("show-notes/disclaimer.txt", _disclaimer_text(plan))
    emit("show-notes/segment-index.md", _segment_index(plan))
    playlist_relative = emit("playlist.json", _playlist_text(plan))

    keep = {path.resolve() for path in written if path.parent != root}
    for folder in obsio.GENERATED_DIRS:
        # current/ holds the live selection and is rewritten by render.refresh,
        # which also preserves the switcher position across a rebuild.
        if folder == "current":
            continue
        folder_path = (root / folder).resolve()
        obsio.prune(
            folder_path,
            {path for path in keep if folder_path in path.parents},
        )
    del playlist_relative
    return written


def _summary(plan: dict) -> str:
    chyron_count = len(plan["show"]["chyrons"]) + sum(
        len(segment["chyrons"]) for segment in plan["segments"]
    )
    call_count = sum(1 for item in plan["show"]["chyrons"] if item.get("pool") == "call")
    headline_count = sum(len(segment["headlines"]) for segment in plan["segments"])
    flagged = sum(1 for segment in plan["segments"] if segment["needsVerification"])
    flagged_word = "segment" if flagged == 1 else "segments"
    segue = f" {plan['segueCount']} segues." if plan.get("segueCount") else ""
    return (
        f"{len(plan['segments'])} segments, {chyron_count} chyrons "
        f"({call_count} call-in), {headline_count} headlines, "
        f"{len(plan['ticker'])} ticker lines. "
        f"{flagged} {flagged_word} flagged CONFIRM BEFORE AIR.{segue}"
    )


def _require_schema(data: dict) -> None:
    version = data.get("schemaVersion", 1)
    if version not in SUPPORTED_SCHEMAS:
        supported = ", ".join(str(item) for item in sorted(SUPPORTED_SCHEMAS))
        raise obsio.DataError(
            f"schemaVersion {version} is not supported (this script reads {supported})"
        )


def _require_object(data: dict, key: str) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise obsio.DataError(f"{key} must be an object")
    return value


def _require_text(container: dict, key: str, label: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise obsio.DataError(f"{label} must be a non-empty string")
    return obsio.one_line(value)


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise obsio.DataError("Expected a string")
    return obsio.one_line(value)


def _show_chyrons(show: dict, limit: int) -> list[dict]:
    items: list[dict] = []
    for key, fallback_id in (("hostChyron", "host"), ("jessChyron", "jess")):
        raw = show.get(key)
        if raw is None:
            continue
        items.append(_chyron(raw, limit, f"show.{key}", fallback_id))
    defaults = show.get("defaultChyrons") or []
    if not isinstance(defaults, list):
        raise obsio.DataError("show.defaultChyrons must be a list")
    for index, raw in enumerate(defaults):
        items.append(_chyron(raw, limit, f"show.defaultChyrons[{index}]"))
    _unique(items, "id", "show chyron id")
    _unique(items, "token", "show chyron filename")
    if not any(item["id"] == "host" for item in items):
        raise obsio.DataError("show.hostChyron is required")
    return items


def _segment_plan(segment: object, limit: int, schema: int = 1) -> dict:
    if not isinstance(segment, dict):
        raise obsio.DataError("Each segment must be an object")
    order = segment.get("order")
    if not isinstance(order, int):
        raise obsio.DataError("Each segment needs an integer order")
    identifier = _require_text(segment, "id", f"segment order {order} id")
    title = _require_text(segment, "title", f"segment {identifier} title")
    headlines = segment.get("headlines", [])
    if not isinstance(headlines, list) or not all(isinstance(item, str) for item in headlines):
        raise obsio.DataError(f"segment {identifier} headlines must be a list of strings")
    raw_chyrons = segment.get("chyrons", [])
    if not isinstance(raw_chyrons, list):
        raise obsio.DataError(f"segment {identifier} chyrons must be a list")
    chyrons = [
        _chyron(item, limit, f"segment {identifier} chyron {index}")
        for index, item in enumerate(raw_chyrons)
    ]
    _unique(chyrons, "id", f"segment {identifier} chyron id")
    _unique(chyrons, "token", f"segment {identifier} chyron filename")
    if "skippable" in segment and segment.get("skippable") is not None:
        skippable = _require_bool(segment, "skippable", identifier)
    elif schema >= 3:
        skippable = False
    else:
        skippable = _require_bool(segment, "skippable", identifier)
    jess = _require_bool(segment, "jessDropIn", identifier)
    flex = _optional_bool(segment, "flex", identifier)
    signature = _optional_bool(segment, "signature", identifier)
    recurring = _optional_bool(segment, "recurring", identifier)
    letter = _block_letter(segment, identifier)
    pending = segment.get("needsVerification") or []
    if not isinstance(pending, list) or not all(isinstance(item, str) for item in pending):
        raise obsio.DataError(f"segment {identifier} needsVerification must be a list of strings")
    points = segment.get("talkingPoints") or []
    if not isinstance(points, list) or not all(isinstance(item, str) for item in points):
        raise obsio.DataError(f"segment {identifier} talkingPoints must be a list of strings")
    sources = segment.get("sources") or []
    if not isinstance(sources, list) or not all(isinstance(item, str) for item in sources):
        raise obsio.DataError(f"segment {identifier} sources must be a list of strings")
    follow = _string_list(segment.get("followUpQuestions") or [], f"segment {identifier} followUpQuestions")
    transitions = _string_list(segment.get("transitionLines") or [], f"segment {identifier} transitionLines")
    links = _links(segment.get("links") or [], sources, identifier)
    return {
        "id": identifier,
        "token": obsio.safe_token(identifier, f"segment {identifier}"),
        "letter": letter,
        "order": order,
        "start": _optional_text(segment.get("start")),
        "end": _optional_text(segment.get("end")),
        "timeRange": _optional_text(segment.get("timeRange")),
        "durationMinutes": segment.get("durationMinutes"),
        "title": title,
        "subject": _optional_text(segment.get("subject")),
        "skippable": skippable,
        "flex": flex,
        "canTrimToMinutes": _optional_number(segment.get("canTrimToMinutes"), f"segment {identifier} canTrimToMinutes"),
        "canStretchToMinutes": _optional_number(segment.get("canStretchToMinutes"), f"segment {identifier} canStretchToMinutes"),
        "jessDropIn": jess,
        "signature": signature,
        "recurring": recurring,
        "headlines": [obsio.one_line(item) for item in headlines if obsio.one_line(item)],
        "chyrons": chyrons,
        "needsVerification": [obsio.one_line(item) for item in pending if obsio.one_line(item)],
        "talkingPoints": [obsio.one_line(item) for item in points if obsio.one_line(item)],
        "followUpQuestions": follow,
        "transitionLines": transitions,
        "sources": [item.strip() for item in sources if item.strip()],
        "links": links,
    }


def _chyron(raw: object, limit: int, label: str, fallback_id: str | None = None) -> dict:
    if not isinstance(raw, dict):
        raise obsio.DataError(f"{label} must be an object")
    identifier = raw.get("id") or fallback_id
    if not isinstance(identifier, str) or not identifier.strip():
        raise obsio.DataError(f"{label} needs an id")
    identifier = obsio.one_line(identifier)
    primary = raw.get("primary")
    secondary = raw.get("secondary", "")
    if not isinstance(primary, str) or not primary.strip():
        raise obsio.DataError(f"{label} primary must be a non-empty string")
    if not isinstance(secondary, str):
        raise obsio.DataError(f"{label} secondary must be a string")
    primary = obsio.one_line(primary)
    secondary = obsio.one_line(secondary)
    for part, text in (("primary", primary), ("secondary", secondary)):
        if len(text) > limit:
            raise obsio.DataError(
                f"{label} {part} is {len(text)} characters (max {limit}): {text}"
            )
    return {
        "id": identifier,
        "token": obsio.safe_token(identifier, label),
        "primary": primary,
        "secondary": secondary,
    }


def _require_bool(segment: dict, key: str, identifier: str) -> bool:
    value = segment.get(key)
    if not isinstance(value, bool):
        raise obsio.DataError(f"segment {identifier} {key} must be true or false")
    return value


def _string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise obsio.DataError(f"{label} must be a list of strings")
    return [obsio.one_line(item) for item in value if obsio.one_line(item)]


def _optional_number(value: object, label: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise obsio.DataError(f"{label} must be an integer or null")
    return value


def _links(raw: object, sources: list[str], identifier: str) -> list[dict]:
    if not isinstance(raw, list):
        raise obsio.DataError(f"segment {identifier} links must be a list")
    links = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            text = item.strip()
            if text:
                links.append({"label": text, "url": text if text.startswith("http") else ""})
            continue
        if not isinstance(item, dict):
            raise obsio.DataError(f"segment {identifier} links[{index}] must be an object")
        label = _optional_text(item.get("label"))
        url = _optional_text(item.get("url"))
        if label or url:
            links.append({"label": label or url, "url": url})
    for source in sources:
        text = source.strip()
        if text:
            links.append({"label": text, "url": text if text.startswith("http") else ""})
    return links


def _optional_bool(segment: dict, key: str, identifier: str) -> bool:
    if key not in segment or segment.get(key) is None:
        return False
    value = segment.get(key)
    if not isinstance(value, bool):
        raise obsio.DataError(f"segment {identifier} {key} must be true or false")
    return value


def _block_letter(segment: dict, identifier: str) -> str:
    raw = segment.get("letter")
    if isinstance(raw, str) and raw.strip():
        token = raw.strip()
        if len(token) != 1 or not token.isalpha():
            raise obsio.DataError(f"segment {identifier} letter must be a single A-Z letter")
        return token.upper()
    if len(identifier) >= 2 and identifier[0].isalpha() and identifier[1] in "-_":
        return identifier[0].upper()
    return ""


def _call_ins(data: dict, limit: int) -> dict:
    raw = data.get("callIns")
    if not raw:
        return {"chyrons": [], "promoLines": [], "channels": []}
    if not isinstance(raw, dict):
        raise obsio.DataError("callIns must be an object")
    items = raw.get("chyrons") or []
    if not isinstance(items, list):
        raise obsio.DataError("callIns.chyrons must be a list")
    chyrons = [_chyron(item, limit, f"callIns.chyrons[{index}]") for index, item in enumerate(items)]
    _unique(chyrons, "id", "call-in chyron id")
    promos = raw.get("promoLines") or []
    if not isinstance(promos, list) or not all(isinstance(item, str) for item in promos):
        raise obsio.DataError("callIns.promoLines must be a list of strings")
    channels_raw = raw.get("channels") or []
    if not isinstance(channels_raw, list):
        raise obsio.DataError("callIns.channels must be a list")
    channels = []
    for index, item in enumerate(channels_raw):
        if not isinstance(item, dict):
            raise obsio.DataError(f"callIns.channels[{index}] must be an object")
        channels.append(
            {
                "channel": _optional_text(item.get("channel")),
                "address": _optional_text(item.get("address")),
                "status": _optional_text(item.get("status")),
            }
        )
    return {
        "chyrons": chyrons,
        "promoLines": [obsio.one_line(item) for item in promos if obsio.one_line(item)],
        "channels": channels,
    }


def _segue_count(data: dict) -> int:
    if "segues" not in data or data.get("segues") in (None, []):
        return 0
    segues = data["segues"]
    if not isinstance(segues, list):
        raise obsio.DataError("segues must be a list")
    for index, item in enumerate(segues):
        if not isinstance(item, dict) or not str(item.get("line") or "").strip():
            raise obsio.DataError(f"segues[{index}] needs a line")
    return len(segues)


def _needs_confirm(text: str) -> bool:
    upper = text.upper()
    return any(token in upper for token in ("CONFIRM", "UNVERIFIED", "NOT SET UP"))


def _unique(items: list[dict], key: str, label: str) -> None:
    seen: set[object] = set()
    for item in items:
        value = item[key]
        if value in seen:
            raise obsio.DataError(f"Duplicate {label}: {value}")
        seen.add(value)


def _ticker_text(headlines: list[str]) -> str:
    if not headlines:
        return ""
    return "  •  ".join(headlines) + "  •  \n"


def _scene_files(plan: dict) -> dict[str, str]:
    show = plan["show"]
    cards = show["cards"]
    brb = _card(cards, "brb", "Be right back")
    live = _card(cards, "live", "LIVE")
    zone = _zone_label(show["timezone"])
    clock = _clock(show["startTime"])
    date_text = _long_date(show["episodeDate"])
    clock_bits = " ".join(bit for bit in (clock, zone) if bit)
    episode_bits = [bit for bit in (date_text, clock_bits) if bit]
    starts = f"Starts {clock_bits}" if clock_bits else ""
    files = {
        "scenes/show-title.txt": _line(show["title"]),
        "scenes/show-subtitle.txt": _line(show["subtitle"]),
        "scenes/episode-line.txt": _line(" · ".join(episode_bits)),
        "scenes/starts-at.txt": _line(starts.strip()),
        "scenes/timezone.txt": _line(show["timezone"]),
        "scenes/zone-label.txt": _line(zone),
        "scenes/live-bug.txt": _line(live),
        "scenes/brb-primary.txt": _line(brb),
        "scenes/brb-secondary.txt": _line(show["subtitle"] or show["title"]),
        "scenes/account-list.txt": _account_list(show["socials"]),
    }
    promos = plan.get("promoLines") or []
    if promos:
        files["scenes/call-promos.txt"] = "\n\n".join(promos) + "\n"
        for index, promo in enumerate(promos, start=1):
            files[f"scenes/call-promo-{index:02d}.txt"] = _line(promo)
    return files


def _card(cards: dict, key: str, fallback: str) -> str:
    value = cards.get(key)
    if isinstance(value, str) and value.strip():
        return obsio.one_line(value)
    return fallback


def _account_list(socials: dict) -> str:
    lines = []
    for key in ON_AIR_SOCIAL_KEYS:
        value = socials.get(key)
        if not isinstance(value, str) or not value.strip() or _needs_confirm(value):
            continue
        label = SOCIAL_LABELS.get(key, key[:1].upper() + key[1:])
        lines.append(f"{label} {obsio.one_line(value)}")
    return ("\n".join(lines) + "\n") if lines else ""


def _clock(hhmm: str) -> str:
    if not hhmm:
        return ""
    try:
        hour_text, minute_text = hhmm.split(":")
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise obsio.DataError(f"show.startTime must look like 08:00, got {hhmm!r}") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise obsio.DataError(f"show.startTime is out of range: {hhmm}")
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _long_date(iso_date: str) -> str:
    if not iso_date:
        return ""
    try:
        parsed = datetime.strptime(iso_date, "%Y-%m-%d")
    except ValueError as exc:
        raise obsio.DataError(
            f"show.episodeDate must be YYYY-MM-DD, got {iso_date!r}"
        ) from exc
    return f"{_WEEKDAYS[parsed.weekday()]}, {_MONTHS[parsed.month - 1]} {parsed.day}, {parsed.year}"


def _zone_label(timezone: str) -> str:
    if not timezone:
        return ""
    lowered = timezone.lower()
    if "chicago" in lowered or lowered in {"ct", "cst", "cdt", "central"}:
        return "CT"
    return timezone


def _line(text: str) -> str:
    text = text.strip()
    return f"{text}\n" if text else ""


def _disclaimer_text(plan: dict) -> str:
    text = plan["disclaimer"].strip()
    return f"{text}\n" if text else ""


def _segment_index(plan: dict) -> str:
    lines = [
        "# Segment index",
        "",
        "Generated from `obs-data.json` by `scripts/build.py`. Do not edit by hand.",
        "",
    ]
    if plan["generated"]:
        lines.append(f"Source generated field: {plan['generated']}.")
        lines.append("")
    if plan["show"].get("format"):
        lines.append(plan["show"]["format"])
        lines.append("")
    lines.append(
        "Start times are suggestions. The switcher jumps by block letter or order number; it does not follow a clock."
    )
    lines.append("")
    if plan["disclaimer"]:
        lines.append(f"> {plan['disclaimer']}")
        lines.append("")
    lines.extend(
        [
            "| Block | Order | Time | Min | Flex | Skip | Jess | Sig | Title | Chyrons | Headlines |",
            "|:-----:|------:|------|----:|:----:|:----:|:----:|:---:|-------|--------:|----------:|",
        ]
    )
    ordered = sorted(plan["segments"], key=lambda item: item["order"])
    for segment in ordered:
        when = segment.get("timeRange") or segment["start"] or ""
        flex = ""
        if segment.get("flex"):
            trim = segment.get("canTrimToMinutes")
            stretch = segment.get("canStretchToMinutes")
            flex = "yes" if trim is None and stretch is None else f"{trim}–{stretch}"
        lines.append(
            "| {letter} | {order} | {when} | {minutes} | {flex} | {skip} | {jess} | {sig} | {title} | {chyrons} | {headlines} |".format(
                letter=segment["letter"] or "",
                order=segment["order"],
                when=when,
                minutes=segment["durationMinutes"] if segment["durationMinutes"] is not None else "",
                flex=flex,
                skip="yes" if segment["skippable"] else "",
                jess="yes" if segment["jessDropIn"] else "",
                sig="yes" if segment["signature"] else "",
                title=_table_cell(segment["title"]),
                chyrons=len(segment["chyrons"]),
                headlines=len(segment["headlines"]),
            )
        )
    lines.extend(["", "## Cues", ""])
    for segment in ordered:
        letter = f"{segment['letter']} · " if segment["letter"] else ""
        marks = []
        if segment["signature"]:
            marks.append("SIGNATURE")
        if segment["recurring"]:
            marks.append("RECURRING")
        if segment.get("flex"):
            marks.append("FLEX")
        if segment["skippable"]:
            marks.append("SKIPPABLE")
        mark = f" — {', '.join(marks)}" if marks else ""
        lines.append(f"### {letter}order {segment['order']} · {segment['title']}{mark}")
        lines.append("")
        if segment["subject"]:
            lines.append(segment["subject"])
            lines.append("")
        if segment["talkingPoints"]:
            lines.extend(f"- {point}" for point in segment["talkingPoints"])
            lines.append("")
        if segment.get("followUpQuestions"):
            lines.append("Follow-ups:")
            lines.append("")
            lines.extend(f"- {point}" for point in segment["followUpQuestions"])
            lines.append("")
        if segment.get("transitionLines"):
            lines.append("Transitions:")
            lines.append("")
            lines.extend(f"- {point}" for point in segment["transitionLines"])
            lines.append("")
        if segment["headlines"]:
            lines.append("Headlines:")
            lines.append("")
            lines.extend(f"- {headline}" for headline in segment["headlines"])
            lines.append("")
        if segment["chyrons"]:
            lines.append("Chyrons:")
            lines.append("")
            for chyron in segment["chyrons"]:
                secondary = f" — {chyron['secondary']}" if chyron["secondary"] else ""
                lines.append(f"- {chyron['primary']}{secondary}")
            lines.append("")
        link_rows = segment.get("links") or [{"label": source, "url": source} for source in segment["sources"]]
        if link_rows:
            lines.append("Sources:")
            lines.append("")
            for link in link_rows:
                label = link.get("label") or link.get("url") or ""
                url = link.get("url") or ""
                if url.startswith("http://") or url.startswith("https://"):
                    shown = label if label and label != url else url
                    lines.append(f"- [{shown}]({url})" if shown != url else f"- <{url}>")
                else:
                    lines.append(f"- {label}")
            lines.append("")
        if segment["needsVerification"]:
            lines.append("**CONFIRM BEFORE AIR:**")
            lines.append("")
            lines.extend(f"- {item}" for item in segment["needsVerification"])
            lines.append("")
    lines.extend(["## CONFIRM BEFORE AIR", ""])
    flagged = [segment for segment in ordered if segment["needsVerification"]]
    if not flagged:
        lines.append("Nothing in `segments` is flagged.")
        lines.append("")
    for segment in flagged:
        letter = segment["letter"] or f"order {segment['order']}"
        lines.append(f"- **{letter}** (order {segment['order']}) {segment['title']}")
        lines.extend(f"  - {item}" for item in segment["needsVerification"])
    lines.append("")
    lines.extend(_call_in_section(plan))
    return "\n".join(lines).rstrip() + "\n"


def _call_in_section(plan: dict) -> list[str]:
    lines = ["## Call-ins", ""]
    channels = plan.get("channels") or []
    if channels:
        lines.append("Channels:")
        lines.append("")
        for channel in channels:
            status = channel["status"]
            prefix = "CONFIRM BEFORE AIR — " if _needs_confirm(status) else ""
            lines.append(
                f"- **{channel['channel'] or 'Channel'}** — {channel['address']} — {prefix}{status}".rstrip(" —")
            )
        lines.append("")
    socials = plan["show"].get("socials") or {}
    held = []
    reference = []
    for key, value in socials.items():
        if not isinstance(value, str) or not value.strip():
            continue
        if key in ON_AIR_SOCIAL_KEYS and not _needs_confirm(value):
            continue
        if _needs_confirm(value):
            held.append((key, obsio.one_line(value)))
        else:
            reference.append((key, obsio.one_line(value)))
    if held:
        lines.append("Accounts kept off the pre-show card until confirmed:")
        lines.append("")
        for key, value in held:
            lines.append(f"- **{key}** — {value}")
        lines.append("")
    if reference:
        lines.append("In the data, not on the pre-show card:")
        lines.append("")
        for key, value in reference:
            lines.append(f"- **{key}** — {value}")
        lines.append("")
    promos = plan.get("promoLines") or []
    if promos:
        lines.append("Promo lines (also `scenes/call-promo-01.txt` and up):")
        lines.append("")
        for index, promo in enumerate(promos, start=1):
            lines.append(f"{index}. {promo}")
        lines.append("")
    if not channels and not held and not reference and not promos:
        lines.append("No call-in block in obs-data.json.")
        lines.append("")
    return lines


def _table_cell(text: str) -> str:
    return text.replace("|", "\\|")


def _playlist_text(plan: dict) -> str:
    import json

    show_chyrons = [
        {"id": item["id"], "file": item["file"]} for item in plan["show"]["chyrons"]
    ]
    call_chyrons = [
        {"id": item["id"], "file": item["file"]}
        for item in plan["show"]["chyrons"]
        if item.get("pool") == "call"
    ]
    segments = []
    for segment in sorted(plan["segments"], key=lambda item: item["order"]):
        segments.append(
            {
                "id": segment["id"],
                "letter": segment["letter"],
                "order": segment["order"],
                "start": segment["start"],
                "end": segment.get("end") or "",
                "timeRange": segment.get("timeRange") or "",
                "durationMinutes": segment["durationMinutes"],
                "title": segment["title"],
                "subject": segment["subject"],
                "skippable": segment["skippable"],
                "flex": segment.get("flex", False),
                "canTrimToMinutes": segment.get("canTrimToMinutes"),
                "canStretchToMinutes": segment.get("canStretchToMinutes"),
                "jessDropIn": segment["jessDropIn"],
                "signature": segment["signature"],
                "recurring": segment["recurring"],
                "titleFile": segment["titleFile"],
                "headlines": segment["headlineFiles"],
                "chyrons": segment["chyronFiles"],
                "needsVerification": segment["needsVerification"],
            }
        )
    payload = {
        "playlistVersion": 2,
        "note": "Generated by scripts/build.py from obs-data.json. Do not edit.",
        "source": obsio.DATA_NAME,
        "generated": plan["generated"],
        "chyronMaxChars": plan["limit"],
        "show": {
            "title": plan["show"]["title"],
            "subtitle": plan["show"]["subtitle"],
            "format": plan["show"].get("format") or "",
            "chyrons": show_chyrons,
            "callChyrons": call_chyrons,
        },
        "segments": segments,
    }
    return json.dumps(payload, indent=2) + "\n"


if __name__ == "__main__":
    sys.exit(main())
