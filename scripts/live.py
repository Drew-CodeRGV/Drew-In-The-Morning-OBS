#!/usr/bin/env python3
"""Copy one segment's generated files into current/ so OBS can refresh.

Point OBS text sources at current/. Run this during the show:

    python scripts/live.py repl
    python scripts/live.py next
    python scripts/live.py prev
    python scripts/live.py goto <letter-or-order-or-id>
    python scripts/live.py skip
    python scripts/live.py chyron next
    python scripts/live.py chyron call
    python scripts/live.py headline next
    python scripts/live.py serve

The rundown is a menu. `goto` takes a block letter, an order number, or a
segment id from obs-data.json. `skip` jumps forward to the next block whose
skippable flag is false, so a signature block is a landing spot, not something
this command jumps over. Suggested start times are not a clock.
"""

from __future__ import annotations

import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import obsio
import render

HELP = """\
Usage: python scripts/live.py [--root PATH] <command> [args]

  list                         Show the menu in suggested order
  status                       Show what current/ is displaying
  next                         Next block, including skippable ones
  prev                         Previous block
  goto <letter|order|id>       Jump to any block. A letter matches the block id
  skip                         Jump forward to the next block that is not skippable
  reset                        Back to the first block
  chyron next|prev|<n>|<id>    This block's lower thirds, or a show-level plate
  chyron call                  Cycle the call-in promo plates
  headline next|prev|<n>       Cycle this block's headlines
  repl                         Type the commands above until you quit
  serve [--port 8765]          Serve this folder for OBS browser sources

Examples:
  python scripts/live.py goto A
  python scripts/live.py goto 0
  python scripts/live.py chyron call
  python scripts/live.py serve --port 8765

OBS browser source: http://127.0.0.1:8765/overlay/lower-third.html
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root_arg = _take_option(args, "--root")
    port_arg = _take_option(args, "--port")
    root = obsio.repo_root(root_arg)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(HELP, end="")
        return 0 if args else 2
    command, rest = args[0], args[1:]
    try:
        if command == "serve":
            port = int(port_arg or (rest[0] if rest else "8765"))
            return serve(root, port)
        if port_arg is not None and command != "serve":
            print("ERROR: --port is only used with serve", file=sys.stderr)
            return 2
        if command == "repl":
            return repl(root)
        return dispatch(root, command, rest)
    except obsio.DataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0


def dispatch(root: Path, command: str, rest: list[str]) -> int:
    _warn_if_stale(root)
    playlist = _playlist(root)
    state = render.normalize(render.load_state(root, playlist), playlist)
    segments = obsio.sorted_segments(playlist)

    if command == "list":
        print(_format_list(playlist, state))
        return 0
    if command == "status":
        refreshed = render.refresh(root, state)
        print(render.describe(root, playlist, refreshed))
        return 0
    if command == "next":
        return _move(root, playlist, state, _neighbor(segments, state, 1), "No next segment.")
    if command == "prev":
        return _move(root, playlist, state, _neighbor(segments, state, -1), "No previous segment.")
    if command == "goto":
        if len(rest) != 1:
            print("ERROR: goto needs a block letter, an order number, or a segment id", file=sys.stderr)
            return 2
        found = _find(segments, rest[0])
        if found is None:
            print(f"ERROR: no segment matches {rest[0]!r}", file=sys.stderr)
            print(_format_list(playlist, state), file=sys.stderr)
            return 1
        return _move(root, playlist, state, found, "")
    if command == "skip":
        found = _next_required(segments, state["segmentOrder"])
        if found is None:
            print("ERROR: no later non-skippable segment. Staying put.", file=sys.stderr)
            print(render.describe(root, playlist, render.refresh(root, state)))
            return 1
        return _move(root, playlist, state, found, "")
    if command == "reset":
        if not segments:
            print("ERROR: playlist has no segments", file=sys.stderr)
            return 1
        return _move(root, playlist, state, segments[0], "")
    if command == "chyron":
        return _chyron(root, playlist, state, rest)
    if command == "headline":
        return _headline(root, playlist, state, rest)
    print(f"ERROR: unknown command {command!r}", file=sys.stderr)
    print(HELP, end="", file=sys.stderr)
    return 2


def repl(root: Path) -> int:
    playlist = _playlist(root)
    title = playlist["show"].get("title") or "OBS"
    print(f"{title} switcher. Type help, or quit to leave.")
    while True:
        playlist = _playlist(root)
        state = render.normalize(render.load_state(root, playlist), playlist)
        segment = obsio.segment_by_order(playlist, state["segmentOrder"])
        label = segment["title"] if segment else "no segment"
        if segment and segment.get("letter"):
            prompt_id = segment["letter"]
        elif segment:
            prompt_id = str(segment["order"])
        else:
            prompt_id = "-"
        try:
            line = input(f"[{prompt_id}] {label} > ")
        except EOFError:
            print()
            return 0
        parts = line.strip().split()
        if not parts:
            continue
        if parts[0] in {"quit", "exit", "q"}:
            return 0
        if parts[0] == "help":
            print(HELP, end="")
            continue
        code = dispatch(root, parts[0], parts[1:])
        if code == 2 and parts[0] not in {"goto", "chyron", "headline"}:
            continue


def serve(root: Path, port: int) -> int:
    handler = _handler(root)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as exc:
        print(f"ERROR: could not listen on 127.0.0.1:{port}: {exc}", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{port}/overlay/lower-third.html"
    print(f"Serving {root}")
    print(f"Lower third: {url}")
    print(f"Headline card: http://127.0.0.1:{port}/overlay/headline-card.html")
    print(f"Pre-show: http://127.0.0.1:{port}/overlay/preshow.html")
    print(f"Outro: http://127.0.0.1:{port}/overlay/outro.html")
    print(f"BRB: http://127.0.0.1:{port}/overlay/brb.html")
    print("Ctrl-C stops the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


def _handler(root: Path) -> type[SimpleHTTPRequestHandler]:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if any(part.startswith(".") for part in path.split("/") if part):
                self.send_error(404)
                return
            super().do_GET()

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Access-Control-Allow-Origin", "*")
            super().end_headers()

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            # Keep the show terminal quiet; OBS polls these files constantly.
            return

    return Handler


def _move(root: Path, playlist: dict, state: dict, segment: dict | None, empty: str) -> int:
    if segment is None:
        print(f"ERROR: {empty}", file=sys.stderr)
        print(render.describe(root, playlist, render.refresh(root, state)))
        return 1
    state["segmentOrder"] = segment["order"]
    state["headlineIndex"] = 0
    state["chyronIndex"] = 0
    state["chyronMode"] = "segment"
    state["showChyronId"] = None
    refreshed = render.refresh(root, state)
    print(render.describe(root, playlist, refreshed))
    return 0


def _chyron(root: Path, playlist: dict, state: dict, rest: list[str]) -> int:
    segment = obsio.segment_by_order(playlist, state["segmentOrder"])
    if segment is None:
        print("ERROR: no current segment", file=sys.stderr)
        return 1
    if not rest:
        print("ERROR: chyron needs next, prev, a number, or a show chyron id", file=sys.stderr)
        return 2
    show_ids = [item["id"] for item in playlist["show"]["chyrons"]]
    head = rest[0]
    if head == "show":
        if len(rest) != 2:
            print("ERROR: chyron show <id>", file=sys.stderr)
            return 2
        return _use_show_chyron(root, playlist, state, rest[1], show_ids)
    if head == "call":
        return _cycle_call_chyron(root, playlist, state)
    if head in {"next", "prev"}:
        if state["chyronMode"] == "call":
            return _cycle_call_chyron(root, playlist, state, backward=(head == "prev"))
        count = len(segment["chyrons"])
        if count == 0:
            print("ERROR: this segment has no chyrons", file=sys.stderr)
            return 1
        if state["chyronMode"] == "show":
            state["chyronIndex"] = 0 if head == "next" else count - 1
        elif head == "next":
            state["chyronIndex"] = (state["chyronIndex"] + 1) % count
        else:
            state["chyronIndex"] = (state["chyronIndex"] - 1) % count
        state["chyronMode"] = "segment"
        state["showChyronId"] = None
    elif head.isdigit():
        count = len(segment["chyrons"])
        number = int(head)
        if number < 1 or number > count:
            print(f"ERROR: this segment has {count} chyrons", file=sys.stderr)
            return 1
        state["chyronMode"] = "segment"
        state["chyronIndex"] = number - 1
        state["showChyronId"] = None
    elif head in show_ids and len(rest) == 1:
        return _use_show_chyron(root, playlist, state, head, show_ids)
    else:
        print(f"ERROR: unknown chyron {head!r}. Show chyrons: {', '.join(show_ids)}", file=sys.stderr)
        return 1
    refreshed = render.refresh(root, state)
    print(render.describe(root, playlist, refreshed))
    return 0


def _cycle_call_chyron(root: Path, playlist: dict, state: dict, backward: bool = False) -> int:
    items = playlist["show"].get("callChyrons") or []
    if not items:
        print("ERROR: obs-data.json has no call-in chyrons. Run scripts/build.py after adding callIns.", file=sys.stderr)
        return 1
    if state.get("chyronMode") == "call":
        step = -1 if backward else 1
        state["callChyronIndex"] = (int(state.get("callChyronIndex") or 0) + step) % len(items)
    else:
        state["callChyronIndex"] = len(items) - 1 if backward else 0
    state["chyronMode"] = "call"
    state["showChyronId"] = None
    refreshed = render.refresh(root, state)
    print(render.describe(root, playlist, refreshed))
    return 0


def _use_show_chyron(root: Path, playlist: dict, state: dict, identifier: str, show_ids: list[str]) -> int:
    if identifier not in show_ids:
        print(f"ERROR: no show chyron {identifier!r}. Choices: {', '.join(show_ids)}", file=sys.stderr)
        return 1
    state["chyronMode"] = "show"
    state["showChyronId"] = identifier
    refreshed = render.refresh(root, state)
    print(render.describe(root, playlist, refreshed))
    return 0


def _headline(root: Path, playlist: dict, state: dict, rest: list[str]) -> int:
    segment = obsio.segment_by_order(playlist, state["segmentOrder"])
    if segment is None:
        print("ERROR: no current segment", file=sys.stderr)
        return 1
    count = len(segment["headlines"])
    if not rest:
        print("ERROR: headline needs next, prev, or a number", file=sys.stderr)
        return 2
    if count == 0:
        print("ERROR: this segment has no headlines", file=sys.stderr)
        return 1
    head = rest[0]
    if head == "next":
        state["headlineIndex"] = (state["headlineIndex"] + 1) % count
    elif head == "prev":
        state["headlineIndex"] = (state["headlineIndex"] - 1) % count
    elif head.isdigit():
        number = int(head)
        if number < 1 or number > count:
            print(f"ERROR: this segment has {count} headlines", file=sys.stderr)
            return 1
        state["headlineIndex"] = number - 1
    else:
        print(f"ERROR: unknown headline command {head!r}", file=sys.stderr)
        return 2
    refreshed = render.refresh(root, state)
    print(render.describe(root, playlist, refreshed))
    return 0


def _neighbor(segments: list[dict], state: dict, step: int) -> dict | None:
    orders = [segment["order"] for segment in segments]
    try:
        index = orders.index(state["segmentOrder"])
    except ValueError:
        return segments[0] if segments else None
    target = index + step
    if target < 0 or target >= len(segments):
        return None
    return segments[target]


def _next_required(segments: list[dict], order: int) -> dict | None:
    later = [segment for segment in segments if segment["order"] > order and not segment["skippable"]]
    return later[0] if later else None


def _find(segments: list[dict], token: str) -> dict | None:
    try:
        order = int(token)
    except ValueError:
        order = None
    if order is not None:
        for segment in segments:
            if segment["order"] == order:
                return segment
        return None
    if len(token) == 1 and token.isalpha():
        letter = token.upper()
        matches = [segment for segment in segments if segment.get("letter") == letter]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise obsio.DataError(f"More than one block uses letter {letter}")
    for segment in segments:
        if segment["id"] == token or segment["id"].lower() == token.lower():
            return segment
    return None


def _format_list(playlist: dict, state: dict) -> str:
    lines = []
    for segment in obsio.sorted_segments(playlist):
        marker = ">" if segment["order"] == state["segmentOrder"] else " "
        flags = []
        if segment["skippable"]:
            flags.append("skippable")
        if segment.get("flex"):
            flags.append("flex")
        if segment["jessDropIn"]:
            flags.append("jess")
        if segment.get("signature"):
            flags.append("signature")
        if segment.get("recurring"):
            flags.append("recurring")
        if segment.get("needsVerification"):
            flags.append("CONFIRM")
        suffix = f"  ({', '.join(flags)})" if flags else ""
        start = segment.get("timeRange") or segment.get("start") or ""
        letter = segment.get("letter") or " "
        lines.append(
            f"{marker} {letter:<2} {segment['order']:>2}  {start:<11}  {segment['title']}{suffix}"
        )
    return "\n".join(lines)


def _playlist(root: Path) -> dict:
    path = obsio.playlist_path(root)
    if not path.exists():
        raise obsio.DataError("playlist.json is missing. Run: python scripts/build.py")
    return obsio.load_json(path)


def _warn_if_stale(root: Path) -> None:
    data = root / obsio.DATA_NAME
    playlist = obsio.playlist_path(root)
    if data.exists() and playlist.exists() and data.stat().st_mtime > playlist.stat().st_mtime:
        print(
            "WARNING: obs-data.json is newer than playlist.json. Run: python scripts/build.py",
            file=sys.stderr,
        )


def _take_option(args: list[str], name: str) -> str | None:
    if name not in args:
        return None
    index = args.index(name)
    if index + 1 >= len(args):
        raise SystemExit(f"ERROR: {name} needs a value")
    value = args[index + 1]
    del args[index : index + 2]
    return value


if __name__ == "__main__":
    sys.exit(main())
