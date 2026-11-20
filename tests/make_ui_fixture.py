#!/usr/bin/env python3
"""Build the studio page the UI tests open: the real 2026-11-19 packet plus FICTIONAL chisme rows (tests/fixtures/chisme_sample.py).
    python3 tests/make_ui_fixture.py /tmp/ui     -> /tmp/ui/out/DITM-briefing-2026-11-19-studio.html"""
import datetime, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "tests", "fixtures"))
import chisme, chisme_sample  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ui"
os.makedirs(out, exist_ok=True)
pk = json.load(open(os.path.join(ROOT, "packet", "data", "packet-2026-11-19.json")))
now = datetime.datetime.now(datetime.timezone.utc)
pk["chisme"] = chisme.build(chisme_sample.rows(now), chisme.headline_titles(pk), now) | {"sources": {"reddit (fixture)": {"items": 3, "ok": True, "note": ""}, "instagram": {"items": 0, "ok": False, "note": "login wall"}}}
pj = os.path.join(out, "packet.json"); json.dump(pk, open(pj, "w"))
subprocess.run([sys.executable, os.path.join(ROOT, "packet", "build_packet.py"), pj, "--out", os.path.join(out, "out"), "--no-render", "--no-obs-update", "--force-latest"], check=True, capture_output=True)
print(os.path.join(out, "out", "DITM-briefing-2026-11-19-studio.html"))
