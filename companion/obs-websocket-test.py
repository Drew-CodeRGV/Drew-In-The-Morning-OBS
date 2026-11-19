#!/usr/bin/env python3
"""Push show blocks to OBS over WebSocket v5, without Companion.

    pip install obsws-python
    OBS_WEBSOCKET_PASSWORD='the-password-you-set-in-obs' python3 companion/obs-websocket-test.py --index 0
    OBS_WEBSOCKET_PASSWORD='...' python3 companion/obs-websocket-test.py --cycle --dwell 2

The password is read from the environment. It is not stored in this repo.
Default password is empty, which only works if OBS authentication is off.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

BLOCKS = Path(__file__).resolve().parent / "blocks.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run DITM blocks against OBS WebSocket 5")
    parser.add_argument("--host", default=os.environ.get("OBS_WEBSOCKET_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("OBS_WEBSOCKET_PORT", "4455")))
    parser.add_argument("--index", type=int, help="Push one block by index (0-12)")
    parser.add_argument("--letter", help="Push one block by letter")
    parser.add_argument("--cycle", action="store_true", help="Walk every block, then stop")
    parser.add_argument("--dwell", type=float, default=1.5, help="Seconds to hold each block during --cycle")
    parser.add_argument("--lower-third", action="store_true", help="Also try to enable DITM Lower Third")
    parser.add_argument("--list", action="store_true", help="Print the blocks and exit")
    args = parser.parse_args()

    document = json.loads(BLOCKS.read_text(encoding="utf-8"))
    blocks = document["blocks"]
    if args.list or not (args.cycle or args.index is not None or args.letter):
        for block in blocks:
            print(f"{block['index']:2}  {block['letter']}  {block['title']}")
        if args.list:
            return 0
        print("Pass --index, --letter, or --cycle to talk to OBS.", file=sys.stderr)
        return 2

    try:
        from obsws_python import ReqClient
    except ImportError:
        print("Install the client first: pip install obsws-python", file=sys.stderr)
        return 2

    password = os.environ.get("OBS_WEBSOCKET_PASSWORD", "")
    client = ReqClient(host=args.host, port=args.port, password=password, timeout=5)
    chosen = blocks
    if args.letter:
        letter = args.letter.upper()
        chosen = [block for block in blocks if block["letter"] == letter]
        if not chosen:
            print(f"No block {letter}", file=sys.stderr)
            return 1
    elif args.index is not None:
        if args.index < 0 or args.index >= len(blocks):
            print(f"Index must be 0 through {len(blocks) - 1}", file=sys.stderr)
            return 1
        chosen = [blocks[args.index]]

    for block in chosen:
        push(client, document, block, args.lower_third)
        print(f"Set {block['letter']}  {block['title']}")
        if args.cycle and block is not chosen[-1]:
            time.sleep(args.dwell)
    return 0


def push(client, document: dict, block: dict, lower_third: bool) -> None:
    sources = document["sources"]
    values = {
        sources["chyron"]: block["chyron"],
        sources["headline"]: block["headline"],
        sources["segmentTitle"]: block["title"],
        sources["blockLetter"]: block["letter"],
    }
    for name, text in values.items():
        client.set_input_settings(name, {"text": text}, True)
    client.set_current_program_scene(block["scene"])
    if not lower_third:
        return
    scene = document["scenes"]["host"]
    source = sources["lowerThird"]
    found = client.get_scene_item_id(scene, source)
    item_id = getattr(found, "scene_item_id", None)
    if item_id is None and isinstance(found, dict):
        item_id = found.get("sceneItemId")
    if item_id is None:
        raise RuntimeError(f"Could not resolve scene item id for {source!r} on {scene!r}")
    client.set_scene_item_enabled(scene, item_id, True)


if __name__ == "__main__":
    raise SystemExit(main())
