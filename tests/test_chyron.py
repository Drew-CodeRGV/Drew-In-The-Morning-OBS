"""The OBS chyron page: built from obs-data.json, command-only control, no secrets, wired into both builds."""
import json, os, re, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "companion"))
import chyron_build  # noqa: E402


class ChyronBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        chyron_build.write(cls.tmp)
        cls.html = open(os.path.join(cls.tmp, "chyron.html")).read()
        cls.data = json.load(open(os.path.join(cls.tmp, "chyron.json")))

    def test_twelve_blocks_on_the_sixty_minute_show(self):
        d = self.data
        self.assertEqual(d["total"], 60)
        self.assertEqual([b["letter"] for b in d["blocks"]], list("ABCDEFGHIJKL"))
        offs = [b["offset"] for b in d["blocks"]]
        self.assertEqual(offs, sorted(offs))
        self.assertEqual(offs[0], 0)
        self.assertEqual(d["blocks"][-1]["offset"] + d["blocks"][-1]["dur"], 60)

    def test_every_block_has_headline_and_line(self):
        for b in self.data["blocks"]:
            self.assertTrue(b["headline"].strip(), b)
            self.assertTrue(b["sub"].strip() or b["kicker"].strip(), b)
            self.assertRegex(b["color"], r"^#[0-9a-fA-F]{6}$")

    def test_data_embedded_in_page_matches_json(self):
        m = re.search(r"window\.DITM_DATA=(\{.*?\});\n", self.html, re.S)
        self.assertTrue(m)
        self.assertEqual(json.loads(m.group(1).replace("<\\/", "</"))["blocks"], self.data["blocks"])

    def test_news_look_and_no_title_or_letter(self):
        h = self.html
        self.assertIn("linear-gradient", h)
        self.assertIn("data:image/png;base64", h)          # logo bug embedded
        self.assertNotIn("id=\"seg\"", h)
        self.assertNotIn("id=\"letter\"", h)
        self.assertIn("background:transparent", h.replace(" ", ""))

    def test_commands_are_a_fixed_whitelist(self):
        m = re.search(r"CMDS=\{([^}]*)\}", self.html)
        cmds = set(re.findall(r"(\w+):1", m.group(1)))
        self.assertEqual(cmds, {"start", "stop", "hold", "resume", "toggle", "next", "prev", "goto", "clear", "show"})
        self.assertIn("hasOwnProperty", self.html)
        self.assertNotIn("eval(", self.html)
        self.assertNotIn("innerHTML", self.html)            # text only ever goes in via textContent

    def test_topic_is_not_in_the_public_page(self):
        self.assertNotRegex(self.html, r"ditm-ros-[0-9a-f]{6,}")
        self.assertIn("?topic=", open(os.path.join(ROOT, "companion", "chyron.template.html")).read() + "?topic=")
        self.assertNotIn("api_key", self.html.lower())
        self.assertNotIn("p40-caldav", self.html)

    def test_csp_only_allows_ntfy(self):
        m = re.search(r"connect-src ([^;\"']*(?:'self')?[^;\"]*)", self.html)
        self.assertTrue(m)
        self.assertIn("https://ntfy.sh", m.group(1))
        self.assertNotIn("*.", m.group(1))

    def test_build_hooks(self):
        for rel in ("packet/build_packet.py", "companion/build_companion.py"):
            self.assertIn("chyron_build", open(os.path.join(ROOT, rel)).read(), rel)


class DashboardLink(unittest.TestCase):
    def test_dashboard_has_hold_and_ntfy(self):
        s = open(os.path.join(ROOT, "packet", "build_packet.py")).read()
        for needle in ('id="chhold"', 'id="mb-hold"', "https://ntfy.sh", "window.ditmRos", "ditm-chyron-topic-v1"):
            self.assertIn(needle, s)
        self.assertNotRegex(s, r"ditm-ros-[0-9a-f]{6,}")


if __name__ == "__main__":
    unittest.main()
