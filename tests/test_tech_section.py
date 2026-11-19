import copy, datetime, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "packet"))
import tech_wires as tw  # noqa: E402
import trend_score as ts  # noqa: E402
import build_packet as bp  # noqa: E402

NOW = datetime.datetime(2026, 11, 19, 12, 30, tzinfo=ts.UTC)


def rss(items):
    out = '<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
    for title, link, when, desc in items:
        out += f"<item><title>{title}</title><link>{link}</link><pubDate>{when.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate><description>{desc}</description></item>"
    return out + "</channel></rss>"


def hrs(h):
    return NOW - datetime.timedelta(hours=h)


class Wires(unittest.TestCase):
    FEEDS = [{"id": "v", "name": "The Verge", "url": "https://v.test/f"}, {"id": "t", "name": "TechCrunch", "url": "https://t.test/f"},
             {"id": "x", "name": "Dead", "url": "https://x.test/f"}]

    def fetch(self, url, timeout=20, retries=1):
        pages = {"https://v.test/f": rss([("New phone ships", "https://v.test/1", hrs(2), "&lt;p&gt;It &lt;b&gt;ships&lt;/b&gt; today.&lt;/p&gt;"), ("Old story", "https://v.test/2", hrs(80), "")]),
                 "https://t.test/f": rss([("Funding round &amp; more", "https://t.test/3", hrs(1), "x")])}
        return (200, pages[url]) if url in pages else (404, "")

    def test_newest_first_48h_cutoff_and_dead_feed(self):
        items, status = tw.candidates(self.FEEDS, NOW, 48, self.fetch)
        self.assertEqual([i["title"] for i in items], ["Funding round & more", "New phone ships"])
        self.assertEqual(items[1]["summary"], "It ships today.")
        self.assertTrue(status["v"]["ok"] and not status["x"]["ok"])
        self.assertEqual(status["v"]["items"], 1)  # the 80-hour-old one is dropped

    def test_feeds_yml_lists_tech_feeds_but_breaking_watch_ignores_them(self):
        feeds = tw.load_feeds()
        self.assertEqual({f["id"] for f in feeds}, {"verge", "techcrunch", "ars"})  # fastcompany-web is disabled by default
        cfg = ts.load_config(ROOT)
        import ditm_yaml
        y = ditm_yaml.load(os.path.join(ROOT, "feeds.yml"))
        self.assertNotIn("tech", {f["id"] for f in y["feeds"]})
        self.assertTrue(all(f["id"] not in {"verge", "techcrunch", "ars"} for f in y["feeds"]))


class PrepTech(unittest.TestCase):
    def test_labels(self):
        d = {"tech": {"origin": "wires", "items": [{"title": "A", "source_url": "https://a.test/1", "one_line": "x"}]}}
        bp.prep_tech(d)
        self.assertEqual(d["tech"]["badge"], "FALLBACK: TECH WIRES")
        self.assertIn("No Fast Company Daily issue", d["tech"]["originLabel"])
        self.assertEqual(d["tech"]["items"][0]["basis"], "FALLBACK: TECH WIRES")
        self.assertFalse(d["tech"]["items"][0]["isConfirm"])
        d = {"tech": {"origin": "fast-company-daily", "issue": {"date": "Nov 19"}, "items": [{"title": "B", "source_url": "https://b.test/1", "one_line": "y", "verified": False}]}}
        bp.prep_tech(d)
        self.assertEqual(d["tech"]["badge"], "FAST COMPANY DAILY · Nov 19")
        self.assertTrue(d["tech"]["items"][0]["isConfirm"])  # unverified -> CONFIRM

    def test_missing_link_and_empty_and_cap(self):
        d = {"tech": {"origin": "wires", "items": [{"title": "no link", "one_line": "z"}] + [{"title": f"i{i}", "source_url": "https://a.test/%d" % i, "one_line": "z"} for i in range(8)]}}
        bp.prep_tech(d)
        self.assertIn("CONFIRM BEFORE AIR", d["tech"]["items"][0]["confirm"])
        self.assertEqual(len(d["tech"]["items"]), 5)
        d = {}
        bp.prep_tech(d)
        self.assertEqual(d["tech"]["items"], [])
        self.assertEqual(d["tech"]["badge"], "NO TECH ITEMS")


class Rendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = os.path.join(ROOT, "packet", "data", "packet-2026-11-19.json")
        cls.data = json.load(open(src))
        bp.OPTS["fetch_trends"] = False
        bp.prepare(cls.data, os.path.join(ROOT, "obs-data.json"), False)

    def test_studio_has_tech_section_collapsed_with_items_and_links(self):
        h = bp.studio_html(self.data)
        self.assertIn('id="tech"', h)
        self.assertNotIn('id="tech" open', h)
        self.assertIn("What's Happening in Tech", h)
        for it in self.data["tech"]["items"]:
            self.assertIn(it["source_url"], h)
        self.assertIn("On-air angle", h)
        self.assertIn('href="#tech"', h)  # nav link

    def test_txt_and_email_carry_the_section(self):
        t = bp.txt(self.data)
        self.assertIn("WHAT'S HAPPENING IN TECH", t)
        self.assertIn("FALLBACK: TECH WIRES", t)
        e = bp.email_html(self.data)
        self.assertIn("What's Happening in Tech", e)
        self.assertIn("FALLBACK: TECH WIRES", e)

    def test_rundown_block_j_has_tech_subsegment_and_segue(self):
        j = next(r for r in self.data["rundown"] if r["letter"] == "J")
        self.assertTrue(any("TECH SUB-SEGMENT" in x for x in j["talkingPoints"]))
        self.assertTrue(any("tech" in x.lower() for x in j["transitions"]))
        self.assertEqual([r["letter"] for r in self.data["rundown"]], list("ABCDEFGHIJKL"))
        self.assertEqual(sum(r["minutes"] for r in self.data["rundown"]), 60)


if __name__ == "__main__":
    unittest.main()
