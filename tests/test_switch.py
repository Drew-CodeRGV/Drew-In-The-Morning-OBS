"""The switcher and the build stay driven by obs-data.json.

These tests use a tiny fake show plus the shipped JSON. They fail if a
segment title or headline from the shipped show is copied into the operator
docs, the scripts, or the overlay.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402
import live  # noqa: E402
import obsio  # noqa: E402

DOCS = ("README.md", "OBS-setup.md")
SCAN_DIRS = ("scripts", "overlay", "tests")


def sample_show() -> dict:
    return {
        "schemaVersion": 1,
        "generated": "2026-01-01",
        "chyronMaxChars": 60,
        "show": {
            "title": "Sample Show",
            "subtitle": "Live from Somewhere",
            "episodeDate": "2026-11-23",
            "startTime": "08:00",
            "timezone": "America/Chicago",
            "socials": {"instagram": "@sample", "facebookPageId": "99"},
            "hostChyron": {"id": "host", "primary": "Host Name", "secondary": "The host"},
            "jessChyron": {"id": "jess", "primary": "Guest", "secondary": "Drop-in"},
            "defaultChyrons": [
                {"id": "socials", "primary": "@sample", "secondary": "IG"},
            ],
            "tickerHeadlines": ["Alpha story", "Beta story"],
            "disclaimer": "Check the news before air.",
        },
        "callIns": {
            "channels": [
                {
                    "channel": "Email",
                    "address": "show@example.com",
                    "status": "CONFIRM it is public",
                }
            ],
            "chyrons": [
                {"id": "ci1", "primary": "Phone the desk", "secondary": "Ask in chat"},
                {"id": "ci2", "primary": "Send a topic", "secondary": "Before Sunday"},
            ],
            "promoLines": ["Tell us what to cover next."],
        },
        "segments": [
            {
                "id": "a",
                "letter": "A",
                "order": 0,
                "start": "08:00",
                "durationMinutes": 3,
                "title": "Open",
                "subject": "Hello",
                "skippable": False,
                "jessDropIn": False,
                "headlines": ["Hello there"],
                "chyrons": [
                    {"id": "c1", "primary": "Host Name", "secondary": "Opening"},
                    {"id": "c2", "primary": "Second plate", "secondary": "Still opening"},
                ],
                "talkingPoints": ["Say hello"],
                "sources": [],
                "needsVerification": [],
            },
            {
                "id": "b",
                "letter": "B",
                "order": 1,
                "start": "08:03",
                "durationMinutes": 5,
                "title": "Optional bit",
                "subject": "Can drop",
                "skippable": True,
                "jessDropIn": False,
                "headlines": ["First optional", "Second optional"],
                "chyrons": [{"id": "c1", "primary": "Optional", "secondary": "Bit"}],
                "talkingPoints": [],
                "sources": ["https://example.com/story"],
                "needsVerification": ["Confirm the date"],
            },
            {
                "id": "c",
                "letter": "C",
                "order": 2,
                "start": "08:08",
                "durationMinutes": 3,
                "title": "Guest spot",
                "subject": "Guest",
                "skippable": True,
                "jessDropIn": True,
                "headlines": ["Guest is here"],
                "chyrons": [{"id": "c1", "primary": "Guest", "secondary": "Drop-in"}],
                "talkingPoints": [],
                "sources": [],
                "needsVerification": [],
            },
            {
                "id": "d",
                "letter": "D",
                "order": 3,
                "start": "08:11",
                "durationMinutes": 4,
                "title": "Close",
                "subject": "Sign-off",
                "skippable": False,
                "jessDropIn": False,
                "headlines": ["Goodbye"],
                "chyrons": [],
                "talkingPoints": [],
                "sources": ["Not a url, a notebook"],
                "needsVerification": [],
            },
        ],
    }


class SwitchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data_path = self.root / "obs-data.json"
        self._write_show(sample_show())
        self.assertEqual(build.main(["--root", str(self.root), "--data", str(self.data_path)]), 0)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_show(self, data: dict) -> None:
        self.data_path.write_text(json.dumps(data), encoding="utf-8")

    def _read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")

    def test_build_writes_screen_files_and_episode_line(self) -> None:
        self.assertEqual(self._read("segment-titles/00-a.txt"), "Open\n")
        self.assertEqual(self._read("headlines/00-a-01.txt"), "Hello there\n")
        self.assertEqual(self._read("chyrons/00-a-c1.txt"), "Host Name\nOpening\n")
        self.assertEqual(self._read("chyrons/show-host.txt"), "Host Name\nThe host\n")
        self.assertEqual(self._read("ticker/ticker.txt"), "Alpha story  •  Beta story  •  \n")
        self.assertEqual(
            self._read("scenes/episode-line.txt"),
            "Monday, November 23, 2026 · 8:00 AM CT\n",
        )
        self.assertEqual(self._read("scenes/starts-at.txt"), "Starts 8:00 AM CT\n")
        self.assertIn("Instagram @sample", self._read("scenes/account-list.txt"))
        self.assertNotIn("99", self._read("scenes/account-list.txt"))
        self.assertIn("facebookPageId", self._read("show-notes/segment-index.md"))
        self.assertEqual(self._read("current/segment-title.txt"), "Open\n")
        self.assertEqual(self._read("current/headline.txt"), "Hello there\n")
        self.assertEqual(self._read("current/chyron-primary.txt"), "Host Name\n")
        self.assertEqual(self._read("current/chyron-secondary.txt"), "Opening\n")
        self.assertEqual(self._read("current/scene-hint.txt"), "host\n")
        playlist = json.loads(self._read("playlist.json"))
        self.assertEqual([segment["order"] for segment in playlist["segments"]], [0, 1, 2, 3])

    def test_next_prev_goto_and_skip_follow_the_data(self) -> None:
        self.assertEqual(live.main(["--root", str(self.root), "next"]), 0)
        self.assertEqual(self._read("current/segment-title.txt"), "Optional bit\n")
        self.assertEqual(self._read("current/headline.txt"), "First optional\n")

        self.assertEqual(live.main(["--root", str(self.root), "headline", "next"]), 0)
        self.assertEqual(self._read("current/headline.txt"), "Second optional\n")
        self.assertEqual(live.main(["--root", str(self.root), "headline", "next"]), 0)
        self.assertEqual(self._read("current/headline.txt"), "First optional\n")
        self.assertEqual(live.main(["--root", str(self.root), "headline", "2"]), 0)
        self.assertEqual(self._read("current/headline.txt"), "Second optional\n")

        self.assertEqual(live.main(["--root", str(self.root), "prev"]), 0)
        self.assertEqual(self._read("current/segment-title.txt"), "Open\n")
        self.assertEqual(self._read("current/headline.txt"), "Hello there\n")

        self.assertEqual(live.main(["--root", str(self.root), "goto", "c"]), 0)
        self.assertEqual(self._read("current/segment-title.txt"), "Guest spot\n")
        self.assertEqual(self._read("current/scene-hint.txt"), "host-jess\n")
        self.assertIn("Jess on screen: yes", self._read("current/segment-meta.txt"))

        self.assertEqual(live.main(["--root", str(self.root), "goto", "0"]), 0)
        self.assertEqual(live.main(["--root", str(self.root), "skip"]), 0)
        self.assertEqual(self._read("current/segment-title.txt"), "Close\n")
        self.assertEqual(self._read("current/chyron-primary.txt"), "Host Name\n")
        self.assertIn("fallback:host", self._read("current/segment-meta.txt"))

        self.assertEqual(live.main(["--root", str(self.root), "next"]), 1)
        self.assertEqual(self._read("current/segment-title.txt"), "Close\n")
        self.assertEqual(live.main(["--root", str(self.root), "skip"]), 1)
        self.assertEqual(live.main(["--root", str(self.root), "goto", "missing"]), 1)
        self.assertEqual(live.main(["--root", str(self.root), "reset"]), 0)
        self.assertEqual(self._read("current/segment-title.txt"), "Open\n")

    def test_chyron_cycle_and_show_chyron(self) -> None:
        self.assertEqual(live.main(["--root", str(self.root), "chyron", "next"]), 0)
        self.assertEqual(self._read("current/chyron-primary.txt"), "Second plate\n")
        self.assertEqual(live.main(["--root", str(self.root), "chyron", "1"]), 0)
        self.assertEqual(self._read("current/chyron-primary.txt"), "Host Name\n")
        self.assertEqual(live.main(["--root", str(self.root), "chyron", "socials"]), 0)
        self.assertEqual(self._read("current/chyron-primary.txt"), "@sample\n")
        self.assertEqual(live.main(["--root", str(self.root), "chyron", "next"]), 0)
        self.assertEqual(self._read("current/chyron-primary.txt"), "Host Name\n")
        self.assertEqual(self._read("current/headline.txt"), "Hello there\n")

    def test_rebuild_keeps_position_and_drops_stale_files(self) -> None:
        self.assertEqual(live.main(["--root", str(self.root), "goto", "3"]), 0)
        stale = self.root / "headlines" / "01-b-01.txt"
        self.assertTrue(stale.exists())
        show = sample_show()
        show["segments"] = [segment for segment in show["segments"] if segment["id"] != "b"]
        self._write_show(show)
        self.assertEqual(build.main(["--root", str(self.root), "--data", str(self.data_path)]), 0)
        self.assertFalse(stale.exists())
        self.assertEqual(self._read("current/segment-title.txt"), "Close\n")

        show["segments"] = [segment for segment in show["segments"] if segment["order"] != 3]
        self._write_show(show)
        self.assertEqual(build.main(["--root", str(self.root), "--data", str(self.data_path)]), 0)
        self.assertEqual(self._read("current/segment-title.txt"), "Open\n")

    def test_overlong_chyron_is_rejected(self) -> None:
        show = sample_show()
        show["chyronMaxChars"] = 10
        show["segments"][0]["chyrons"][0]["primary"] = "12345678901"
        self._write_show(show)
        self.assertEqual(build.main(["--root", str(self.root), "--data", str(self.data_path), "--check"]), 1)
        self.assertEqual(self._read("current/chyron-primary.txt"), "Host Name\n")

    def test_letter_jump_and_call_rotation(self) -> None:
        self.assertEqual(live.main(["--root", str(self.root), "goto", "C"]), 0)
        self.assertEqual(self._read("current/segment-title.txt"), "Guest spot\n")
        self.assertEqual(self._read("current/scene-hint.txt"), "host-jess\n")
        self.assertEqual(live.main(["--root", str(self.root), "goto", "a"]), 0)
        self.assertEqual(self._read("current/segment-title.txt"), "Open\n")
        self.assertEqual(live.main(["--root", str(self.root), "chyron", "call"]), 0)
        self.assertEqual(self._read("current/chyron-primary.txt"), "Phone the desk\n")
        self.assertEqual(live.main(["--root", str(self.root), "chyron", "call"]), 0)
        self.assertEqual(self._read("current/chyron-primary.txt"), "Send a topic\n")
        self.assertEqual(self._read("scenes/call-promo-01.txt"), "Tell us what to cover next.\n")
        self.assertIn("CONFIRM BEFORE AIR", self._read("show-notes/segment-index.md"))

    def test_bad_schema_is_rejected(self) -> None:
        show = sample_show()
        show["schemaVersion"] = 99
        self._write_show(show)
        self.assertEqual(build.main(["--root", str(self.root), "--data", str(self.data_path), "--check"]), 1)


class ShippedShowTests(unittest.TestCase):
    def test_shipped_data_builds_and_chyrons_fit(self) -> None:
        source = ROOT / "obs-data.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        limit = data["chyronMaxChars"]
        with tempfile.TemporaryDirectory() as tmp:
            code = build.main(["--root", tmp, "--data", str(source)])
            self.assertEqual(code, 0)
            root = Path(tmp)
            for path in (root / "chyrons").glob("*.txt"):
                lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
                self.assertGreaterEqual(len(lines), 1, path.name)
                self.assertLessEqual(len(lines), 2, path.name)
                for line in lines:
                    self.assertLessEqual(len(line), limit, f"{path.name}: {line}")
            ticker = (root / "ticker" / "ticker.txt").read_text(encoding="utf-8").strip()
            for headline in data["show"]["tickerHeadlines"]:
                self.assertIn(headline, ticker)
            first = sorted(data["segments"], key=lambda segment: segment["order"])[0]
            self.assertEqual(
                (root / "current" / "segment-title.txt").read_text(encoding="utf-8").strip(),
                first["title"],
            )
            self.assertEqual(live.main(["--root", tmp, "goto", first["id"][0]]), 0)
            self.assertEqual(
                (root / "current" / "segment-title.txt").read_text(encoding="utf-8").strip(),
                first["title"],
            )
            signature = next(segment for segment in data["segments"] if segment.get("signature"))
            earlier = [
                segment
                for segment in data["segments"]
                if segment["order"] < signature["order"] and not segment.get("skippable", False)
            ][-1]
            self.assertEqual(live.main(["--root", tmp, "goto", str(earlier["order"])]), 0)
            self.assertEqual(live.main(["--root", tmp, "skip"]), 0)
            self.assertEqual(
                (root / "current" / "segment-title.txt").read_text(encoding="utf-8").strip(),
                signature["title"],
            )
            self.assertIn("Signature: yes", (root / "current" / "segment-meta.txt").read_text(encoding="utf-8"))
            self.assertEqual(live.main(["--root", tmp, "chyron", "call"]), 0)
            primary = data["callIns"]["chyrons"][0]["primary"]
            self.assertEqual(
                (root / "current" / "chyron-primary.txt").read_text(encoding="utf-8").strip(),
                primary,
            )
            account = (root / "scenes" / "account-list.txt").read_text(encoding="utf-8")
            self.assertIn(data["show"]["socials"]["instagram"], account)
            self.assertNotIn(data["show"]["socials"]["showEmail"], account)
            index = (root / "show-notes" / "segment-index.md").read_text(encoding="utf-8")
            self.assertIn("CONFIRM BEFORE AIR", index)
            self.assertIn(data["show"]["socials"]["showEmail"], index)
            playlist = json.loads((root / "playlist.json").read_text(encoding="utf-8"))
            if data.get("schemaVersion", 1) >= 3:
                self.assertTrue(any(segment.get("flex") for segment in playlist["segments"]))
                self.assertTrue(playlist["segments"][0].get("timeRange") or playlist["segments"][0].get("start"))
                linked = data["segments"][1].get("links") or []
                if linked:
                    self.assertIn(linked[0]["url"], index)

    def test_operator_facing_files_do_not_hardcode_this_episode(self) -> None:
        data = json.loads((ROOT / "obs-data.json").read_text(encoding="utf-8"))
        banned: list[str] = []
        for segment in data["segments"]:
            if len(segment["title"].strip()) >= 12:
                banned.append(segment["title"])
            for headline in segment["headlines"]:
                if len(headline.strip()) >= 12:
                    banned.append(headline)
            for chyron in segment["chyrons"]:
                for part in (chyron["primary"], chyron["secondary"]):
                    if part and len(part.strip()) >= 18:
                        banned.append(part)
        for headline in data["show"]["tickerHeadlines"]:
            if len(headline.strip()) >= 12:
                banned.append(headline)
        for chyron in data.get("callIns", {}).get("chyrons", []):
            for part in (chyron["primary"], chyron["secondary"]):
                if part and len(part.strip()) >= 18:
                    banned.append(part)
        text_parts = []
        for name in DOCS:
            text_parts.append((ROOT / name).read_text(encoding="utf-8"))
        skip_tests = {
            ROOT / "tests" / "test_breaking_watch.py",
            ROOT / "tests" / "test_trend_score.py",
            ROOT / "tests" / "test_tech_section.py",
            ROOT / "tests" / "test_obituaries.py",
            ROOT / "tests" / "test_family_calendar.py",
        }
        for folder in SCAN_DIRS:
            for path in (ROOT / folder).rglob("*"):
                if "fixtures" in path.parts or path in skip_tests:
                    continue
                if path.suffix.lower() in {".py", ".html", ".css", ".js", ".md"}:
                    text_parts.append(path.read_text(encoding="utf-8"))
        blob = "\n".join(text_parts)
        for item in banned:
            self.assertNotIn(item, blob, f"hardcoded show copy: {item}")


if __name__ == "__main__":
    unittest.main()
