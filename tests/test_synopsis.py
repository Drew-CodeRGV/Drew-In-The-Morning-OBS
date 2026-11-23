#!/usr/bin/env python3
"""Studio cards show the full headline and keep the real synopsis up to 400 characters."""
import json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "packet"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_packet as bp
import chisme


class SynopsisHelpers(unittest.TestCase):
    def test_keeps_full_text_under_the_limit(self):
        tldr = (
            "The City of Edinburg delivered 1,000 turkeys and 1,000 food baskets through its annual "
            "Edinburg Cares food drive, with city employees, teachers and volunteers handling distribution "
            "ahead of Thanksgiving."
        )
        it = {"title": "Edinburg Cares food drive delivers 1,000 turkeys and 1,000 food baskets to local families", "tldr": tldr}
        self.assertEqual(bp.story_synopsis(it), tldr)
        self.assertLessEqual(len(bp.story_synopsis(it)), bp.SYNOPSIS_LIMIT)

    def test_prefers_the_longest_real_field(self):
        long_sum = " ".join(["Second sentence with more of the article."] * 8)  # well over 400
        it = {
            "title": "A long unfolding story about the Valley",
            "short": "A short teaser line",
            "one_line": "Nov 23: a one-line blurb that is shorter than the summary.",
            "summary": long_sum,
        }
        out = bp.story_synopsis(it)
        self.assertTrue(out.startswith("Second sentence"))
        self.assertLessEqual(len(out), bp.SYNOPSIS_LIMIT)
        self.assertIn(out.rstrip("…"), long_sum)
        # the original text is preserved up to the cap, not rewritten
        self.assertTrue(long_sum.startswith(out.rstrip("…")))

    def test_empty_when_only_a_headline_exists(self):
        title = "Commentary: Debating tablets in the classroom"
        self.assertEqual(bp.story_synopsis({"title": title}), "")
        self.assertEqual(bp.story_synopsis({"title": title, "short": "Debating tablets"}), "")
        self.assertEqual(bp.story_synopsis({"title": title, "tldr": title}), "")

    def test_does_not_invent_or_use_confirm_as_synopsis(self):
        it = {"title": "Meta Muse can shop Walmart", "confirm": "Headline only read; CONFIRM BEFORE AIR"}
        self.assertEqual(bp.story_synopsis(it), "")

    def test_trim_breaks_at_a_sentence(self):
        s1 = "First sentence stays intact because it is short enough."
        s2 = "Second sentence also fits inside the cap if we keep the total under four hundred characters."
        s3 = "Third sentence is the last one we will keep when everything still fits."
        s4 = "Fourth sentence should be dropped once we already have three."
        text = " ".join([s1, s2, s3, s4])
        # bump so 3 sentences exceed?  If 3 fit, 4th drops. Make 3 already near 400.
        pad = "Word " * 40  # 200 chars-ish
        s2 = "Second sentence adds detail " + pad + "and still ends here."
        text = " ".join([s1, s2, s3, s4])
        out = bp.trim_synopsis(text, 400)
        self.assertNotIn("Fourth sentence", out)
        self.assertLessEqual(len(out), 400)
        self.assertTrue(out.startswith(s1))

    def test_enrich_uses_fetched_description_only_when_longer(self):
        it = {"title": "Ukraine drones at Benghazi", "summary": "A short summary.", "url": "https://example.com/story"}
        def fake(url):
            self.assertEqual(url, "https://example.com/story")
            return "Ukraine said naval drones launched from a mothership hit two Russian vessels at Benghazi, sinking the Merkury. Zelenskyy released drone video of the strike."
        n = bp.enrich_synopses([it], fetch=fake, min_len=250)
        self.assertEqual(n, 1)
        self.assertIn("Merkury", bp.story_synopsis(it))

    def test_enrich_skips_when_already_long_enough(self):
        tldr = "A. " + ("Real article sentence with useful detail. " * 12)
        it = {"title": "Already long enough", "tldr": tldr, "url": "https://example.com/x"}
        called = []
        n = bp.enrich_synopses([it], fetch=lambda u: called.append(u) or "IGNORED", min_len=250)
        self.assertEqual(n, 0)
        self.assertEqual(called, [])

    def test_meta_content_reads_og_description(self):
        html = '''<html><head><meta property="og:description" content="The city delivered 1,000 turkeys ahead of Thanksgiving."></head></html>'''
        self.assertEqual(bp._meta_content(html, ("og:description",)), "The city delivered 1,000 turkeys ahead of Thanksgiving.")
        html2 = '''<meta content="From the content-first tag." property="og:description">'''
        self.assertEqual(bp._meta_content(html2, ("og:description",)), "From the content-first tag.")

    def test_fetch_rejects_non_https(self):
        self.assertEqual(bp.fetch_story_description("http://example.com/x"), "")
        self.assertEqual(bp.fetch_story_description("javascript:alert(1)"), "")


class ChismeCap(unittest.TestCase):
    def test_tldr_from_post_text_keeps_up_to_400(self):
        body = ("People in the comments are talking about a county vote on a data-center tax break. " * 8)
        self.assertGreater(len(body), 400)
        out = chisme.tldr_of({"text": body})
        self.assertLessEqual(len(out), 401)  # 400 plus possible ellipsis
        self.assertTrue(body.startswith(out.rstrip("…")))
        self.assertGreater(len(out.rstrip("…")), 220)


class StudioCards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(ROOT, "packet", "data", "packet-2026-11-23.json")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        obs = os.path.join(ROOT, "obs-data.json")
        data = bp.prepare(data, obs if os.path.exists(obs) else None, False)
        # never hit the network in unit tests
        bp.OPTS["enrich_synopses"] = False
        cls.studio = bp.studio_html(data)
        cls.data = data
        # a known long title from today's packet
        cls.sample_title = "Edinburg Cares food drive delivers 1,000 turkeys and 1,000 food baskets to local families"
        cls.sample_tldr = (
            "The City of Edinburg delivered 1,000 turkeys and 1,000 food baskets through its annual "
            "Edinburg Cares food drive, with city employees, teachers and volunteers handling distribution "
            "ahead of Thanksgiving."
        )

    def test_titles_are_not_clamped_and_appear_in_full(self):
        self.assertNotRegex(self.studio, r"\.sec \.item\.trn \.tx>b\.hd[^{]*-webkit-line-clamp:2")
        self.assertNotRegex(self.studio, r"\.sec \.sortbox \.tldr[^{]*-webkit-line-clamp:2")
        self.assertIn("-webkit-line-clamp:12", self.studio)
        self.assertIn("tldr-open", self.studio)
        self.assertIn(self.sample_title, self.studio)
        # the headline is not truncated with an ellipsis in the card title
        self.assertNotIn(self.sample_title[:40] + "…", self.studio)

    def test_synopsis_keeps_full_available_text(self):
        self.assertIn(self.sample_tldr, self.studio)
        # a national summary also survives into the page
        nat = (self.data.get("nationalDesk") or [None])[0]
        if nat and nat.get("summary"):
            self.assertIn(bp.esc(bp.story_synopsis(nat)), self.studio)

    def test_chyron_caps_are_unchanged(self):
        with open(os.path.join(ROOT, "companion", "chyron.template.html"), encoding="utf-8") as fh:
            chy = fh.read()
        self.assertIn("ctext(c.headline,100)", chy)
        self.assertIn("ctext(c.line,118)", chy)
        self.assertIn("ctext(c.kicker,44)", chy)
        with open(os.path.join(ROOT, "packet", "build_packet.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("def chy_trim(t, n):", src)
        self.assertIn("chy_trim(title, 100)", src)
        self.assertTrue(bp.CHY_ITEMS)
        for v in bp.CHY_ITEMS.values():
            self.assertLessEqual(len(v["headline"]), 101, v)
            self.assertLessEqual(len(v["line"]), 119, v)
            self.assertLessEqual(len(v.get("kicker") or ""), 45, v)

    def test_expand_control_and_remove_still_present(self):
        self.assertIn("tldr-exp", self.studio)
        self.assertIn("ditmTldr", self.studio)
        self.assertIn("aria-label=\"Remove story\"", self.studio)
        self.assertIn("ditm-fs-v14", self.studio)
        self.assertIn("id=\"ssstop\"", self.studio)


if __name__ == "__main__":
    unittest.main()
