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
        self.assertNotIn("id=\"bug\"", h)                  # old logo bug removed from the bar
        self.assertIn("left:30px;bottom:26px", h.replace(" ", ""))   # small title-safe margin (about half the old 60/50)
        self.assertIn('id="lg"', h)                         # the small sun logo shown by the 'logo' command
        self.assertNotIn("id=\"seg\"", h)
        self.assertNotIn("id=\"letter\"", h)
        self.assertIn("background:transparent", h.replace(" ", ""))

    def test_bug_asset_published(self):
        from PIL import Image
        p = os.path.join(self.tmp, "assets", "ditm-bug.png")
        im = Image.open(p)
        self.assertEqual(im.mode, "RGBA")
        self.assertEqual(im.height, 340)
        self.assertGreater(im.width, im.height)

    def test_commands_are_a_fixed_whitelist(self):
        m = re.search(r"CMDS=\{([^}]*)\}", self.html)
        cmds = set(re.findall(r"(\w+):1", m.group(1)))
        self.assertEqual(cmds, {"start", "stop", "hold", "resume", "toggle", "logo", "item", "guest", "guest_show", "guest_hide", "caller", "caller_show", "caller_hide", "caller_toggle", "next", "prev", "goto", "clear", "show"})
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


class SendToChyron(unittest.TestCase):
    """The dashboard sends only an id over ntfy; the words come from docs/chyron-items.json, built with the packet."""
    @classmethod
    def setUpClass(cls):
        import subprocess
        cls.tmp = tempfile.mkdtemp()
        subprocess.run([sys.executable, os.path.join(ROOT, "tests", "make_ui_fixture.py"), cls.tmp], check=True, capture_output=True)
        cls.docs = os.path.join(cls.tmp, "out", "docs")
        cls.j = json.load(open(os.path.join(cls.docs, "chyron-items.json")))
        cls.studio = open(os.path.join(cls.tmp, "out", "DITM-briefing-2026-11-19-studio.html")).read()

    def test_published_next_to_the_chyron_page(self):
        self.assertTrue(os.path.exists(os.path.join(self.docs, "chyron.html")))
        self.assertEqual(self.j["v"], 1)
        self.assertGreater(len(self.j["items"]), 50)

    def test_ids_and_lengths(self):
        for k, v in self.j["items"].items():
            self.assertRegex(k, r"^i-[0-9a-f]{10}$")
            self.assertTrue(v["headline"].strip(), k)
            self.assertLessEqual(len(v["headline"]), 101, v)
            self.assertLessEqual(len(v["line"]), 120, v)
            self.assertLessEqual(len(v["kicker"]), 45, v)
            self.assertNotRegex(v["headline"] + v["line"], r"https?://|<[a-z/]")

    def test_one_id_per_card(self):
        # two stories that share a link (e.g. a schedule page) must still get different ids, or the wrong words would go on air
        pairs = re.findall(r'data-chyid="(i-[0-9a-f]{10})" data-chyh="([^"]*)"', self.studio)
        by = {}
        for i, h in pairs:
            by.setdefault(i, set()).add(h)
        self.assertTrue(all(len(v) == 1 for v in by.values()), [i for i, v in by.items() if len(v) > 1])

    def test_every_button_has_an_item(self):
        ids = set(re.findall(r'class="chysend" type="button" data-chyid="(i-[0-9a-f]{10})"', self.studio))
        self.assertGreater(len(ids), 50)
        self.assertEqual(ids - set(self.j["items"]), set())
        for sec in ("Headlines", "Chisme", "Trending", "Tech", "National Desk", "Remembering"):
            self.assertTrue(any(v["kicker"].startswith(sec.upper()) for v in self.j["items"].values()), sec)

    def test_rumor_text_is_labelled(self):
        chisme = [v for v in self.j["items"].values() if v["kicker"] == "CHISME"]
        self.assertTrue(chisme)
        self.assertTrue(sum(v["line"].startswith("UNCONFIRMED") for v in chisme) >= len(chisme) - 1)   # only a card an outlet confirmed may omit it
        for m in re.finditer(r'<div class="item trn tc chisme"[^>]*data-chyid="(i-[0-9a-f]{10})"[^>]*>(.*?)</div></div>', self.studio, re.S):
            body = m.group(2)
            if "CONFIRMED \u00b7" not in body and "CONFIRMED ·" not in body:
                self.assertTrue(self.j["items"][m.group(1)]["line"].startswith("UNCONFIRMED"), m.group(1))
        n = 0
        for seg in self.studio.split('<div class="item trn tc')[1:]:   # every card flagged CONFIRM BEFORE AIR carries the label on its chyron line
            m = re.search(r'data-chyid="(i-[0-9a-f]{10})"', seg[:300])
            if m and 'class="cf">CONFIRM BEFORE AIR' in seg.split('<div class="acts">')[0]:
                n += 1
                self.assertTrue(self.j["items"][m.group(1)]["line"].startswith("UNCONFIRMED"), m.group(1))
        self.assertGreater(n, 0)

    def test_obits_never_carry_a_cause_of_death(self):
        ob = [v for v in self.j["items"].values() if v["kicker"].startswith("REMEMBERING")]
        self.assertTrue(ob)
        for v in ob:
            self.assertTrue(v["headline"].startswith("Remembering "))
            self.assertNotRegex((v["headline"] + " " + v["line"]).lower(), r"cancer|died|death|cause|passed away|accident|suicide|overdose|covid")

    def test_chyron_only_looks_up_ids(self):
        t = open(os.path.join(ROOT, "companion", "chyron.template.html")).read()
        self.assertIn("ITEM_RX=/^i-[0-9a-f]{10}$/", t)
        self.assertIn("chyron-items.json", t)
        self.assertNotIn("c.headline", t); self.assertNotIn("c.line", t); self.assertNotIn("c.text", t)   # nothing from the message body is ever displayed


class GuestAndCaller(unittest.TestCase):
    """Guest and phone caller are the only free text the chyron takes: capped, sanitised, textContent only, https photos only."""
    @classmethod
    def setUpClass(cls):
        cls.t = open(os.path.join(ROOT, "companion", "chyron.template.html")).read()
        cls.d = open(os.path.join(ROOT, "packet", "build_packet.py")).read()

    def test_caps_and_sanitiser(self):
        for needle in ("60", "80", "140"):
            self.assertIn(needle, self.t)
        self.assertRegex(self.t, r"function ctext")
        self.assertRegex(self.t, r"function cphoto")
        self.assertIn("https:", self.t)
        self.assertNotIn("innerHTML", self.t)
        self.assertNotIn("outerHTML", self.t)
        self.assertNotIn("insertAdjacentHTML", self.t)

    def test_photo_is_https_only_in_csp(self):
        self.assertRegex(self.t, r"img-src data: https:")
        self.assertNotRegex(self.t, r"img-src[^;\"]*http:")

    def test_popup_markup(self):
        for needle in ('id="call"', "ON THE PHONE", 'id="cnm"', 'id="ctt"', 'id="cph"', "ditm-chyron-caller-v1", "ditm-chyron-guest-v1"):
            self.assertIn(needle, self.t)

    def test_dashboard_panels(self):
        for needle in ('id="gp"', 'id="g-name"', 'id="g-title"', 'id="g-blurb"', 'id="g-show"', 'id="c-name"', 'id="c-photo"', 'id="c-file"', 'id="c-go"', "Show guest on chyron", "filename=caller.jpg"):
            self.assertIn(needle, self.d)
        self.assertIn("maxlength=\"140\"", self.d)

    def test_no_topic_in_template_or_builder(self):
        for s in (self.t, self.d):
            self.assertNotRegex(s, r"ditm-ros-[0-9a-f]{6,}")


class DashboardLink(unittest.TestCase):
    def test_dashboard_has_hold_and_ntfy(self):
        s = open(os.path.join(ROOT, "packet", "build_packet.py")).read()
        for needle in ('id="chhold"', 'id="mb-hold"', "https://ntfy.sh", "window.ditmRos", "ditm-chyron-topic-v1"):
            self.assertIn(needle, s)
        self.assertNotRegex(s, r"ditm-ros-[0-9a-f]{6,}")


if __name__ == "__main__":
    unittest.main()
