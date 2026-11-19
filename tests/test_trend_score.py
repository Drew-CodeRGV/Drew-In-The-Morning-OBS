import datetime, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import trend_score as ts  # noqa: E402

UTC = ts.UTC
NOW = datetime.datetime(2026, 11, 18, 15, 0, tzinfo=UTC)
CFG = ts.load_config(ROOT)


def story(title, url, outlet, hours_old=1, kind=None, **kw):
    d = dict(title=title, url=url, outlet=outlet, published=(NOW - datetime.timedelta(hours=hours_old)).isoformat(), **kw)
    if kind:
        d["kind"] = kind
    return d


class Canon(unittest.TestCase):
    def test_url(self):
        a = ts.canon_url("https://www.KRGV.com/news/a-story/?utm_source=fb&fbclid=1#top")
        b = ts.canon_url("http://m.krgv.com/news/a-story")
        self.assertEqual(a, b)
        self.assertNotEqual(a, ts.canon_url("https://krgv.com/news/other"))

    def test_title_suffix(self):
        self.assertEqual(ts.strip_outlet_suffix("Cameron County rejects tax break - KRGV", "KRGV"), "Cameron County rejects tax break")
        self.assertEqual(ts.strip_outlet_suffix("A long clause - and more words here about it"), "A long clause - and more words here about it")


class Clustering(unittest.TestCase):
    def test_merges_same_story(self):
        items = [
            story("Cameron County commissioners reject SpaceX data center tax break request - KRGV", "https://news.google.com/rss/articles/AAA", "KRGV", domain="krgv.com", kind="local"),
            story("Cameron County rejects SpaceX tax break for data center", "https://www.valleycentral.com/x", "ValleyCentral"),
            story("SpaceX data center: Cameron County says no to tax break", "https://myrgv.com/y", "MyRGV"),
        ]
        cl = ts.analyze(items, None, NOW, CFG)
        self.assertEqual(len(cl), 1)
        self.assertEqual(len(cl[0]["sources"]), 3)
        self.assertEqual(cl[0]["rep"]["domain"], "valleycentral.com")  # direct link preferred over the aggregator link

    def test_keeps_different_events_apart(self):
        items = [
            story("New World screwworm case reported in Hidalgo County", "https://a.com/1", "A"),
            story("Another New World screwworm case detected in Starr County", "https://b.com/2", "B"),
            story("Brownsville police arrest man after 2 robberies", "https://c.com/3", "C"),
            story("Brownsville police arrest man after 3 robberies", "https://d.com/4", "D"),
        ]
        self.assertEqual(len(ts.analyze(items, None, NOW, CFG)), 4)

    def test_same_url_merges_when_titles_overlap(self):
        items = [story("Council approves new Pharr bridge toll plan", "https://a.com/p?utm_x=1", "A"), story("Pharr bridge toll plan approved by council", "https://www.a.com/p/", "A")]
        self.assertEqual(len(ts.analyze(items, None, NOW, CFG)), 1)

    def test_digest_page_url_does_not_collapse_different_stories(self):
        u = "https://texianpartisan.com/news/daily-briefing/tuesday/"
        items = [story("Texas Supreme Court petition over HD 93 special election result", u, "Texian Partisan"),
                 story("PUC takes up Aqua Texas rate increase Thursday", u, "Texian Partisan")]
        self.assertEqual(len(ts.analyze(items, None, NOW, CFG)), 2)


class Scoring(unittest.TestCase):
    def test_outlets_and_recency(self):
        one = ts.analyze([story("Something happened in town today", "https://a.com/1", "A", 1)], None, NOW, CFG)[0]
        old = ts.analyze([story("Something happened in town today", "https://a.com/1", "A", 36)], None, NOW, CFG)[0]
        self.assertGreater(one["score"], old["score"])
        self.assertAlmostEqual(old["parts"]["recency"], 20 * 0.5 ** 3, places=1)
        self.assertEqual(one["parts"]["outlets"], 6)

    def test_labels(self):
        big = [story("Massive storm hits Texas coast overnight, thousands lose power", f"https://o{i}.com/s", f"O{i}", 1) for i in range(5)]
        c = ts.analyze(big, {"TX": [], "US": []}, NOW, CFG)[0]
        self.assertEqual(c["label"], "Hot")
        self.assertEqual(c["parts"]["outlets"], 30)
        weak = ts.analyze([story("Quiet meeting scheduled", "https://z.com/1", "Z", 40)], None, NOW, CFG)[0]
        self.assertEqual(weak["label"], "Active")

    def test_trends_match_news_item_and_term(self):
        xml = open(os.path.join(ROOT, "tests", "fixtures", "trends_tx.xml")).read()
        tx = ts.parse_trends_rss(xml, "TX")
        self.assertEqual(len(tx), 2)
        self.assertEqual(tx[0]["traffic"], 500)
        trends = {"TX": tx, "US": []}
        c1 = ts.analyze([story("Ella Langley wins big at the CMA Awards", "https://v.com/a", "V")], trends, NOW, CFG)[0]
        self.assertEqual(c1["trend"]["region"], "TX")
        self.assertEqual(c1["parts"]["trends"], 20)
        c2 = ts.analyze([story("Council meets on parking", "https://v.com/b", "V")], trends, NOW, CFG)[0]
        self.assertIsNone(c2["trend"])
        us = ts.analyze([story("Ella Langley wins big at the CMA Awards", "https://v.com/a", "V")], {"TX": [], "US": tx}, NOW, CFG)[0]
        self.assertEqual(us["parts"]["trends"], 12)

    def test_x_and_chatter(self):
        base = ts.analyze([story("Local thing is happening now", "https://a.com/1", "A")], None, NOW, CFG)[0]["score"]
        x = ts.analyze([story("Local thing is happening now", "https://a.com/1", "A", x={"posts": 4, "engagement": 3000})], None, NOW, CFG)[0]
        self.assertGreater(x["score"], base)
        self.assertLessEqual(x["parts"]["x"], 20)
        ch = ts.analyze([story("Local thing is happening now", "https://a.com/1", "A", chatter={"posts": 3, "engagement": 80})], None, NOW, CFG)[0]
        self.assertGreater(ch["parts"]["chatter"], 0)
        self.assertLessEqual(ch["parts"]["chatter"], 10)


class Uncovered(unittest.TestCase):
    def reddit(self, title):
        return story(title, "https://www.reddit.com/r/RioGrandeValley/comments/1", "r/RioGrandeValley", 1, kind="community", valley=True, domain="reddit.com", chatter={"posts": 1, "engagement": 0})

    def test_flags_when_no_local_outlet(self):
        items = [self.reddit("Anyone know why Pharr International Bridge is shut down right now?"),
                 story("Texas Tribune: lawmakers eye new school finance plan", "https://texastribune.org/a", "Texas Tribune", kind="state")]
        cl = ts.analyze(items, None, NOW, CFG)
        flags = {c["rep"]["title"][:10]: c["uncovered"] for c in cl}
        self.assertTrue(flags["Anyone kno"])
        self.assertFalse(flags["Texas Trib"])

    def test_not_flagged_when_local_outlet_has_it(self):
        items = [self.reddit("Pharr International Bridge shut down, anyone know why?"),
                 story("Pharr International Bridge closed after crash, police say", "https://www.krgv.com/news/x", "KRGV", kind="local")]
        cl = ts.analyze(items, None, NOW, CFG)
        self.assertFalse(any(c["uncovered"] for c in cl))


class Keywords(unittest.TestCase):
    def test_ambiguous_geo(self):
        kw = CFG["keywords"]
        self.assertTrue(ts.match_keywords("Mission council votes on abatement", kw, True)["geo"])
        self.assertFalse(ts.match_keywords("Mission to Mars slips again", kw, False)["geo"])
        self.assertIn("McAllen", ts.match_keywords("Fire in McAllen", kw, False)["geo"])
        self.assertIn("evacuation", ts.match_keywords("Evacuation ordered", kw, False)["urgent"])


class PacketIntegration(unittest.TestCase):
    def test_score_packet_merges_and_sorts(self):
        data = {"headlines": {"rgv": [
                    {"title": "Cameron County commissioners reject SpaceX data center tax break", "url": "https://krgv.com/a", "source": "KRGV · Nov 17"},
                    {"title": "Weslaco library adds hours", "url": "https://myrgv.com/b", "source": "MyRGV · Nov 17"},
                    {"title": "Cameron County rejects SpaceX tax break for data center", "url": "https://valleycentral.com/c", "source": "ValleyCentral · Nov 17"}],
                    "texas": [{"title": "Texas Tribune: new school finance plan unveiled", "url": "https://texastribune.org/d", "source": "Texas Tribune · Nov 18"}]},
                "nationalDesk": [], "trending": []}
        s = ts.score_packet(data, None, NOW, CFG)
        self.assertEqual(s["merged"], 1)
        self.assertEqual(len(data["headlines"]["rgv"]), 2)
        top = data["headlines"]["rgv"][0]
        self.assertEqual(top["dupes"], 1)
        self.assertEqual(len(top["sources"]), 2)
        self.assertGreaterEqual(top["score"], data["headlines"]["rgv"][1]["score"])
        self.assertIn(top["label"], ("Hot", "Trending", "Active"))


if __name__ == "__main__":
    unittest.main()
