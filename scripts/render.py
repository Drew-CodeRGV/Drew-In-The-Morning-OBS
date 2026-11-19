"""Write current/ from playlist.json and a small state file.

OBS text sources point at current/. The switcher updates that folder; it does
not care what any segment is called.
"""

from __future__ import annotations

import json
from pathlib import Path

import obsio

STATE_NAME = "state.json"


def initial_state(playlist: dict) -> dict:
    segments = obsio.sorted_segments(playlist)
    order = segments[0]["order"] if segments else 0
    return {
        "segmentOrder": order,
        "headlineIndex": 0,
        "chyronIndex": 0,
        "chyronMode": "segment",
        "showChyronId": None,
        "callChyronIndex": 0,
    }


def load_state(root: Path, playlist: dict) -> dict:
    path = root / "current" / STATE_NAME
    if not path.exists():
        return initial_state(playlist)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return initial_state(playlist)
    if not isinstance(raw, dict):
        return initial_state(playlist)
    return raw


def normalize(state: dict, playlist: dict) -> dict:
    segments = obsio.sorted_segments(playlist)
    if not segments:
        return initial_state(playlist)

    order = state.get("segmentOrder")
    if not isinstance(order, int) or obsio.segment_by_order(playlist, order) is None:
        return initial_state(playlist)

    segment = obsio.segment_by_order(playlist, order)
    assert segment is not None
    normalized = {
        "segmentOrder": order,
        "headlineIndex": _clamp(state.get("headlineIndex"), len(segment["headlines"])),
        "chyronIndex": _clamp(state.get("chyronIndex"), len(segment["chyrons"])),
        "chyronMode": "segment",
        "showChyronId": None,
        "callChyronIndex": 0,
    }
    call_items = playlist["show"].get("callChyrons") or []
    normalized["callChyronIndex"] = _clamp(state.get("callChyronIndex"), len(call_items))
    show_ids = [item["id"] for item in playlist["show"]["chyrons"]]
    chosen = state.get("showChyronId")
    if state.get("chyronMode") == "show" and chosen in show_ids:
        normalized["chyronMode"] = "show"
        normalized["showChyronId"] = chosen
    elif state.get("chyronMode") == "call" and call_items:
        normalized["chyronMode"] = "call"
    return normalized


def refresh(root: Path, state: dict | None = None) -> dict:
    playlist = obsio.load_json(obsio.playlist_path(root))
    if "segments" not in playlist or "show" not in playlist:
        raise obsio.DataError("playlist.json is missing segments or show. Run scripts/build.py.")
    if state is None:
        state = load_state(root, playlist)
    state = normalize(state, playlist)
    _write_current(root, playlist, state)
    return state


def describe(root: Path, playlist: dict, state: dict) -> str:
    segment = obsio.segment_by_order(playlist, state["segmentOrder"])
    if segment is None:
        return "No segments in playlist.json."
    title = obsio.read_text(root / segment["titleFile"]).strip()
    primary = obsio.read_text(root / "current" / "chyron-primary.txt").strip()
    secondary = obsio.read_text(root / "current" / "chyron-secondary.txt").strip()
    headline = obsio.read_text(root / "current" / "headline.txt").strip()
    headline_count = len(segment["headlines"])
    chyron_count = len(segment["chyrons"])
    flags = [
        f"Jess on screen: {'yes' if segment['jessDropIn'] else 'no'}",
        f"skippable: {'yes' if segment['skippable'] else 'no'}",
    ]
    if segment.get("flex"):
        trim = segment.get("canTrimToMinutes")
        stretch = segment.get("canStretchToMinutes")
        if trim is None and stretch is None:
            flags.append("flex: yes")
        else:
            flags.append(f"flex: {trim}–{stretch} min")
    if segment.get("signature"):
        flags.append("signature: yes")
    if segment.get("recurring"):
        flags.append("recurring: yes")
    if segment.get("needsVerification"):
        flags.append("CONFIRM BEFORE AIR")
    clock = segment.get("start") or ""
    minutes = segment.get("durationMinutes")
    when = clock
    if minutes not in (None, ""):
        when = f"{when} · {minutes} min suggested".strip(" ·")
    if state["chyronMode"] == "call":
        call_items = playlist["show"].get("callChyrons") or []
        current = call_items[state["callChyronIndex"]]["id"] if call_items else "?"
        chyron_label = f"call:{state['callChyronIndex'] + 1}/{len(call_items)}:{current}"
    elif state["chyronMode"] == "show":
        chyron_label = f"show:{state['showChyronId']}"
    elif chyron_count:
        chyron_label = f"{state['chyronIndex'] + 1}/{chyron_count}"
    elif primary:
        chyron_label = "fallback:host"
    else:
        chyron_label = "none"
    if headline_count:
        headline_label = f"{state['headlineIndex'] + 1}/{headline_count}"
    else:
        headline_label = "none"
    chyron_text = primary if not secondary else f"{primary} — {secondary}"
    letter = segment.get("letter") or ""
    where = f"{letter} · order {segment['order']}" if letter else f"order {segment['order']}"
    lines = [
        f"On {where} · {title}",
        "  " + " · ".join([when] + flags),
        f"  Headline {headline_label}: {headline or '(blank)'}",
        f"  Chyron {chyron_label}: {chyron_text or '(blank)'}",
    ]
    return "\n".join(lines)


def _clamp(value: object, count: int) -> int:
    if count <= 0:
        return 0
    try:
        index = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        index = 0
    return max(0, min(index, count - 1))


def _active_chyron(root: Path, playlist: dict, segment: dict, state: dict) -> tuple[Path | None, str]:
    if state["chyronMode"] == "call":
        items = playlist["show"].get("callChyrons") or []
        if items:
            item = items[state["callChyronIndex"]]
            return root / item["file"], f"call:{item['id']}"
    if state["chyronMode"] == "show":
        for item in playlist["show"]["chyrons"]:
            if item["id"] == state["showChyronId"]:
                return root / item["file"], f"show:{item['id']}"
    if segment["chyrons"]:
        return root / segment["chyrons"][state["chyronIndex"]], "segment"
    for item in playlist["show"]["chyrons"]:
        if item["id"] == "host":
            return root / item["file"], "fallback:host"
    return None, "none"


def _write_current(root: Path, playlist: dict, state: dict) -> None:
    current = root / "current"
    current.mkdir(parents=True, exist_ok=True)
    segment = obsio.segment_by_order(playlist, state["segmentOrder"])
    if segment is None:
        raise obsio.DataError("State points at a segment that is not in playlist.json.")

    title = obsio.read_text(root / segment["titleFile"]).strip()
    obsio.atomic_write(current / "segment-title.txt", f"{title}\n" if title else "")

    headline_lines: list[str] = []
    for relative in segment["headlines"]:
        headline_lines.append(obsio.read_text(root / relative).strip())
    obsio.atomic_write(
        current / "headlines.txt",
        ("\n".join(line for line in headline_lines if line) + "\n") if headline_lines else "",
    )
    if segment["headlines"]:
        active = headline_lines[state["headlineIndex"]]
    else:
        active = ""
    obsio.atomic_write(current / "headline.txt", f"{active}\n" if active else "")

    chyron_file, chyron_label = _active_chyron(root, playlist, segment, state)
    if chyron_file is None:
        primary, secondary = "", ""
        body = ""
    else:
        body = obsio.read_text(chyron_file)
        if not body.endswith("\n"):
            body += "\n"
        primary, secondary = obsio.split_chyron(body)
    obsio.atomic_write(current / "chyron.txt", body)
    obsio.atomic_write(current / "chyron-primary.txt", f"{primary}\n" if primary else "")
    obsio.atomic_write(current / "chyron-secondary.txt", f"{secondary}\n" if secondary else "")

    hint = obsio.SCENE_HOST_JESS if segment["jessDropIn"] else obsio.SCENE_HOST
    obsio.atomic_write(current / "scene-hint.txt", f"{hint}\n")
    obsio.atomic_write(current / "segment-meta.txt", _meta(segment, state, chyron_label, primary, secondary))
    obsio.atomic_write(current / STATE_NAME, json.dumps(state, indent=2) + "\n")

    owned = {(current / name).resolve() for name in obsio.CURRENT_FILES}
    obsio.prune(current, owned)


def _meta(segment: dict, state: dict, chyron_label: str, primary: str, secondary: str) -> str:
    headline_count = len(segment["headlines"])
    if headline_count:
        headline_label = f"{state['headlineIndex'] + 1} of {headline_count}"
    else:
        headline_label = "none"
    lines = [
        f"Block: {segment.get('letter') or ''}",
        f"Order: {segment['order']}",
        f"Id: {segment['id']}",
        f"Title: {segment.get('title') or ''}",
        f"Subject: {segment.get('subject') or ''}",
        f"Time: {segment.get('timeRange') or segment.get('start') or ''}",
        f"Minutes: {segment.get('durationMinutes') if segment.get('durationMinutes') is not None else ''}",
        f"Jess on screen: {'yes' if segment['jessDropIn'] else 'no'}",
        f"Skippable: {'yes' if segment['skippable'] else 'no'}",
        f"Flex: {'yes' if segment.get('flex') else 'no'}",
        f"Trim to: {segment.get('canTrimToMinutes') if segment.get('canTrimToMinutes') is not None else ''}",
        f"Stretch to: {segment.get('canStretchToMinutes') if segment.get('canStretchToMinutes') is not None else ''}",
        f"Signature: {'yes' if segment.get('signature') else 'no'}",
        f"Recurring: {'yes' if segment.get('recurring') else 'no'}",
        f"Headline: {headline_label}",
        f"Chyron: {chyron_label}",
        f"Chyron primary: {primary}",
        f"Chyron secondary: {secondary}",
        f"Scene hint: {obsio.SCENE_HOST_JESS if segment['jessDropIn'] else obsio.SCENE_HOST}",
    ]
    pending = segment.get("needsVerification") or []
    if pending:
        lines.append("CONFIRM BEFORE AIR:")
        lines.extend(f"- {item}" for item in pending)
    return "\n".join(lines) + "\n"
