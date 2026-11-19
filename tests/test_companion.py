"""The Companion page is generated from obs-data.json and stays import-shaped."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CompanionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.check_call([sys.executable, str(ROOT / "companion" / "build_companion.py")], cwd=ROOT)

    def test_blocks_follow_the_show_json(self) -> None:
        data = json.loads((ROOT / "obs-data.json").read_text(encoding="utf-8"))
        document = json.loads((ROOT / "companion" / "blocks.json").read_text(encoding="utf-8"))
        blocks = document["blocks"]
        segments = sorted(data["segments"], key=lambda item: item["order"])
        self.assertEqual(len(blocks), 12)
        self.assertEqual([block["letter"] for block in blocks], list("ABCDEFGHIJKL"))
        limit = data["chyronMaxChars"]
        for block, segment in zip(blocks, segments):
            self.assertEqual(block["title"], segment["title"])
            self.assertEqual(block["color"], segment["color"])
            self.assertEqual(block["jess"], segment["jessDropIn"])
            primary, _, secondary = block["chyron"].partition("\n")
            self.assertLessEqual(len(primary), limit)
            self.assertLessEqual(len(secondary), limit)
            self.assertEqual(primary, segment["chyrons"][0]["primary"])
            self.assertEqual(block["headline"], segment["headlines"][0])

    def test_config_is_version_six_and_has_no_password(self) -> None:
        config = json.loads((ROOT / "companion" / "ditm-showblocks.companionconfig").read_text(encoding="utf-8"))
        self.assertEqual(config["type"], "full")
        self.assertEqual(config["version"], 6)
        password = config["instances"]["obs"]["config"]["password"]
        self.assertEqual(password, "")
        page = config["pages"]["1"]["controls"]
        self.assertEqual(page["0"]["0"]["style"]["text"].split("\n", 1)[0], "A")
        self.assertIn("PREV", page["2"]["3"]["style"]["text"])
        self.assertIn("NEXT", page["2"]["4"]["style"]["text"])
        self.assertIn("custom_ditm_block", page["0"]["5"]["style"]["text"])
        self.assertIn("CLEAR", page["0"]["6"]["style"]["text"])
        variables = config["custom_variables"]
        self.assertEqual(variables["ditm_block_index"]["defaultValue"], "0")
        self.assertIn("ditm_block", variables)

    def test_requests_use_overlay_and_named_sources(self) -> None:
        payload = json.loads((ROOT / "companion" / "obs-websocket-requests.json").read_text(encoding="utf-8"))
        first = payload["blocks"][0]["requests"]
        text = [item for item in first if item["requestType"] == "SetInputSettings"]
        self.assertEqual(len(text), 4)
        self.assertTrue(all(item["requestData"]["overlay"] is True for item in text))
        names = {item["requestData"]["inputName"] for item in text}
        self.assertEqual(
            names,
            {"DITM Chyron", "DITM Headline", "DITM Segment Title", "DITM Block Letter"},
        )
        scene = [item for item in first if item["requestType"] == "SetCurrentProgramScene"]
        self.assertEqual(scene[0]["requestData"]["sceneName"], "Main Host")


if __name__ == "__main__":
    unittest.main()
