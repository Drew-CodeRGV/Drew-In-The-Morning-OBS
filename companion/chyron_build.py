#!/usr/bin/env python3
"""Build docs/chyron.html (+ chyron.json): the news-style lower third for the OBS browser source.

The 12 blocks come from obs-data.json (the same source blocks.json is built from, via companion/build_companion.load_blocks),
plus each block's offset and length in the 60-minute show. The template is companion/chyron.template.html. Run by
companion/build_companion.py and by packet/build_packet.py (publish), so the daily refresh regenerates it.

    python3 companion/chyron_build.py [out_dir]      # default: docs/
"""
from __future__ import annotations
import base64, io, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import build_companion as bc  # noqa: E402


def chyron_data(obs: dict) -> dict:
    blocks = bc.load_blocks(obs)
    seg = {s["id"]: s for s in obs["segments"]}
    out = []
    for b in blocks:
        s = seg[b["id"]]
        prim, _, sec = b["chyron"].partition("\n")
        out.append({"index": b["index"], "letter": b["letter"], "color": b["color"], "offset": s["offsetMinutes"], "dur": s["durationMinutes"],
                    "headline": b["headline"], "kicker": prim, "sub": sec})
    total = sum(x["dur"] for x in out)
    assert total == 60 and out[0]["offset"] == 0, "show must be 60 minutes from offset 0"
    return {"generated": obs.get("generated", ""), "total": total, "blocks": out}


def logo_data_uri() -> str:
    from PIL import Image
    im = Image.open(ROOT / "logo" / "ditm_logo_bug.png").convert("RGBA")
    im.thumbnail((240, 240))
    buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def render(data: dict) -> str:
    t = (HERE / "chyron.template.html").read_text(encoding="utf-8")
    j = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return t.replace("__DATA__", j).replace("__LOGO__", logo_data_uri())


def write(out_dir, obs_path=None) -> list[str]:
    obs = json.loads(Path(obs_path or ROOT / "obs-data.json").read_text(encoding="utf-8"))
    data = chyron_data(obs)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "chyron.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "chyron.html").write_text(render(data), encoding="utf-8")
    return [str(out / "chyron.html"), str(out / "chyron.json")]


if __name__ == "__main__":
    print("\n".join(write(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs")))
