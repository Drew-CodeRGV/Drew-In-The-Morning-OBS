#!/usr/bin/env python3
"""Show's done (aired vs expired) and the post-show recap page."""
import json, os, re, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packet"))
import build_packet as bp  # noqa: E402


class ShowDoneSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = open(os.path.join(ROOT, "packet", "build_packet.py")).read()

    def test_storage_keys_and_ntfy_commands(self):
        self.assertIn("ditm-aired-v1", self.src)
        self.assertIn("ditm-expired-v1", self.src)
        self.assertIn("aired:1,unaired:1,expire:1,unexpire:1", self.src)
        self.assertIn("sendCmd('expire','*')", self.src)
        self.assertIn("c.cmd==='expire'&&id==='*'", self.src)

    def test_show_done_marks_ticks_aired_and_rest_expired(self):
        self.assertIn("id=\"showdone\"", self.src)
        self.assertIn("id=\"done-dlg\"", self.src)
        self.assertIn("Mark ticked stories as Aired", self.src)
        self.assertIn("function showDone", self.src)
        self.assertIn("ticks.push(id)", self.src)
        self.assertIn("rest.push(id)", self.src)

    def test_parked_sections_and_restore(self):
        self.assertIn('id="aired-box"', self.src)
        self.assertIn('id="expired-box"', self.src)
        self.assertIn("sd-restore", self.src)
        self.assertIn("function restoreOne", self.src)

    def test_chyron_page_does_not_register_board_commands(self):
        for rel in ("docs/chyron.html", "companion/chyron.template.html"):
            html = open(os.path.join(ROOT, rel)).read()
            m = re.search(r"CMDS=\{([^}]*)\}", html)
            self.assertTrue(m, rel)
            cmds = set(re.findall(r"(\w+):1", m.group(1)))
            for banned in ("aired", "unaired", "expire", "unexpire", "remove", "restore"):
                self.assertNotIn(banned, cmds, rel)

    def test_no_secrets_in_source(self):
        self.assertNotRegex(self.src, r"ditm-ros-[0-9a-f]{6,}")
        self.assertNotIn("p40-caldav", self.src)


class PostShowSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = open(os.path.join(ROOT, "packet", "build_packet.py")).read()

    def test_recap_is_drafts_only_and_skips_rumor_and_kids(self):
        self.assertIn("function skipSocial", self.src)
        self.assertIn("s.rumor||s.chisme", self.src)
        self.assertIn("s.kids||(s.desk&&/family/i.test(s.desk))", self.src)
        self.assertIn("Drafts only", self.src)
        self.assertIn("nothing is posted", self.src)
        self.assertIn("CONFIRM BEFORE AIR", self.src[self.src.find("function confirmTag"):self.src.find("function confirmTag") + 200])
        self.assertIn("id=\"ps-print\"", self.src)
        self.assertIn("ditm-aired-", self.src)
        self.assertIn("aired.json", self.src)

    def test_publish_writes_post_show_page(self):
        self.assertIn("post_show_html", self.src)
        self.assertIn('os.path.join(docs, "post-show")', self.src)
        self.assertIn("id=\"ditm-stories\"", self.src)
        self.assertNotIn("breaking.json", self.src.split("def publish")[1].split("def run")[0])


class ShowDoneFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        subprocess.run(
            [sys.executable, os.path.join(ROOT, "tests", "make_ui_fixture.py"), cls.tmp],
            check=True, capture_output=True,
        )
        cls.studio = open(os.path.join(cls.tmp, "out", "DITM-briefing-2026-11-19-studio.html")).read()
        cls.ps = open(os.path.join(cls.tmp, "out", "docs", "post-show", "index.html")).read()
        m = re.search(r'id="ditm-stories">(.*?)</script>', cls.studio, re.S)
        cls.catalog = json.loads(m.group(1).encode("utf-8").decode("unicode_escape") if "\\u003c" in m.group(1)[:20] else m.group(1))
        # catalog may contain \u003c sequences already as characters or escapes; json.loads handles both if raw \u is in JSON
        if isinstance(cls.catalog, str):
            cls.catalog = json.loads(cls.catalog)

    def test_controls_and_empty_parked_sections(self):
        for needle in ('id="showdone"', 'id="done-dlg"', 'id="done-go"', 'id="aired-box"',
                       'id="expired-box"', 'id="post-show"', 'id="ps-root"', 'id="ditm-stories"',
                       'id="ps-open"', "Show's done"):
            self.assertIn(needle, self.studio, needle)
        # boxes start empty; no card is pre-marked aired or expired
        self.assertRegex(self.studio, r'id="aired-box"></div>')
        self.assertRegex(self.studio, r'id="expired-box"></div>')
        self.assertNotRegex(self.studio, r'<div class="item[^"]*\baired\b')
        self.assertNotRegex(self.studio, r'<div class="item[^"]*\bexpired\b')

    def test_catalog_has_facts_only_and_stable_ids(self):
        self.assertGreater(len(self.catalog), 20)
        ids = [s["id"] for s in self.catalog]
        self.assertTrue(all(re.match(r"^r-[0-9a-f]{8,32}$", i) for i in ids), ids[:3])
        self.assertEqual(len(ids), len(set(ids)))
        for s in self.catalog:
            self.assertTrue(s["title"].strip(), s)
            # synopsis may be empty on some rows but must not be invented filler
            self.assertNotIn("lorem ipsum", (s.get("synopsis") or "").lower())
            self.assertIn("id", s)
            self.assertIn("desk", s)
            self.assertIn("confirm", s)
            self.assertIn("rumor", s)
            self.assertIn("kids", s)

    def test_ticks_reuse_use_checkbox_with_rmid(self):
        self.assertIn('aria-label="Mark as aired', self.studio)
        self.assertIn('class="use"', self.studio)
        self.assertGreater(self.studio.count('data-rmid="r-'), 20)

    def test_standalone_post_show_page_is_drafts_only(self):
        self.assertIn('id="ditm-stories"', self.ps)
        self.assertIn("window.ditmPostShow", self.ps)
        self.assertIn("skipSocial", self.ps)
        self.assertIn("Print / Save PDF", self.ps)
        self.assertNotRegex(self.ps, r"ditm-ros-[0-9a-f]{6,}")
        self.assertNotIn("p40-caldav", self.ps)
        # nothing in the page posts to a network except (none): CSP connect-src none
        self.assertIn("connect-src 'none'", self.ps)

    def test_publish_does_not_touch_protected_files(self):
        docs = os.path.join(self.tmp, "out", "docs")
        self.assertTrue(os.path.exists(os.path.join(docs, "post-show", "index.html")))
        self.assertTrue(os.path.exists(os.path.join(docs, "index.html")))
        self.assertFalse(os.path.exists(os.path.join(docs, "breaking.json")), "fixture must not create breaking.json")


class CatalogSkipRules(unittest.TestCase):
    def test_family_and_chisme_flags(self):
        family = {"title": "PTA fundraiser at school", "url": "https://example.com/pta", "_desk": "national"}
        # desk name Family & Kids marks kids
        e = bp.catalog_entry(family, "Family & Kids")
        self.assertTrue(e["kids"], e)
        rum = {"title": "Someone said a thing", "url": "https://example.com/r", "badge": "RUMOR · CONFIRM BEFORE AIR"}
        e2 = bp.catalog_entry(rum, "Chisme")
        self.assertTrue(e2["rumor"] or e2["chisme"], e2)
        e3 = bp.catalog_entry({"title": "City budget vote", "url": "https://example.com/b", "short": "Council votes."}, "City Hall")
        self.assertFalse(e3["kids"])
        self.assertFalse(e3["rumor"])
        self.assertTrue(e3["id"].startswith("r-"))


if __name__ == "__main__":
    unittest.main()
