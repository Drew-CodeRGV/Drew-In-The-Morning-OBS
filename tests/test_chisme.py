import datetime, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "tests", "fixtures"))
import chisme as ch  # noqa: E402
import chisme_sample as fx  # noqa: E402

NOW = datetime.datetime(2026, 11, 19, 12, 0, tzinfo=datetime.timezone.utc)
HEAD = ["Hidalgo County confirms its first New World screwworm case (a calf); quarantine zone covers parts of 4 counties"]


class Safety(unittest.TestCase):
    def v(self, title, text="", **k):
        return ch.safety_verdict(dict(title=title, text=text, **k))

    def test_clean_post_is_kept(self):
        self.assertTrue(self.v("Why is the line at the new Whataburger around the block?")[0])
        self.assertTrue(self.v("Anybody know what the lights over Edinburg were last night?")[0])

    def test_minors_dropped(self):
        for t in ("Teen arrested after fight", "A 15-year-old was seen at the mall", "kids at the splash pad were wild", "Student suspended at McAllen High"):
            self.assertFalse(self.v(t)[0], t)

    def test_doxxing_dropped(self):
        self.assertFalse(self.v("Call him at 956-555-0123")[0])
        self.assertFalse(self.v("lives at 1204 Pecan Street")[0])
        self.assertFalse(self.v("email me@example.com about it")[0])
        self.assertFalse(self.v("license plate ABC-1234 cut me off")[0])

    def test_private_person_accusation_dropped(self):
        self.assertFalse(self.v("Maria Gonzalez was caught cheating on her husband")[0])
        self.assertFalse(self.v("Carlos Treviño arrested for dui")[0])

    def test_sexual_health_money_dropped(self):
        self.assertFalse(self.v("leaked nudes going around")[0])
        self.assertFalse(self.v("my neighbor has cancer and she told everyone")[0])
        self.assertFalse(self.v("the owner is in debt and about to be evicted")[0])

    def test_redact(self):
        self.assertIn("[phone removed]", ch.redact("text 956-555-0123 now"))
        self.assertNotIn("@", ch.redact("me@example.com"))


class Build(unittest.TestCase):
    def setUp(self):
        self.b = ch.build(fx.rows(NOW), HEAD, NOW)

    def test_counts_and_bounds(self):
        n = len(self.b["items"])
        self.assertTrue(4 <= n <= 10, n)
        self.assertLessEqual(n, ch.MAX_ITEMS)

    def test_window_72h(self):
        self.assertTrue(all(i["ageHours"] <= 73 for i in self.b["items"]))
        self.assertGreaterEqual(self.b["dropped"]["stale"], 1)

    def test_unsafe_and_duplicates_dropped(self):
        titles = " ".join(i["title"] for i in self.b["items"])
        for bad in ("Teen arrested", "Maria Gonzalez", "Pecan Street", "evicted", "screwworm"):
            self.assertNotIn(bad, titles)
        self.assertEqual(self.b["dropped"]["unsafe"], 4)
        self.assertEqual(self.b["dropped"]["dup-headline"], 1)
        self.assertNotIn("address removed", titles)

    def test_ranked_by_engagement(self):
        e = [i["engagement"] for i in self.b["items"] if i["engagement"] is not None]
        self.assertEqual(e, sorted(e, reverse=True))

    def test_reddit_score_is_upvotes_plus_comments(self):
        top = next(i for i in self.b["items"] if i["platform"] == "Reddit" and i["source"] == "r/McAllen")
        self.assertEqual(top["engagement"], 412 + 133)

    def test_rumor_badge_unless_confirmed(self):
        for i in self.b["items"]:
            if i["confirmedBy"]:
                self.assertEqual(i["badge"], "")
            else:
                self.assertEqual(i["badge"], ch.RUMOR_BADGE)
        self.assertTrue(any(i["confirmedBy"] for i in self.b["items"]))

    def test_no_invented_riff_or_tldr(self):
        pan = next(i for i in self.b["items"] if "pan dulce" in i["title"])
        self.assertTrue(pan["riff"])        # supplied by the capture
        sunrise = next(i for i in self.b["items"] if "sunrise" in i["title"])
        self.assertEqual(sunrise["riff"], "")   # none supplied, none made up
        self.assertEqual(sunrise["tldr"], "")

    def test_no_private_names_in_output(self):
        blob = json.dumps(self.b)
        self.assertNotIn("956-555", blob)

    def test_confirmed_needs_outlet_and_url(self):
        r = fx.rows(NOW)[0] | {"confirmedBy": {"outlet": "KRGV"}}
        it = ch.normalize(r, NOW)
        self.assertIsNone(it["confirmedBy"])

    def test_empty_is_fine(self):
        b = ch.build([], HEAD, NOW)
        self.assertEqual(b["items"], [])


class Fetchers(unittest.TestCase):
    def test_reddit_json_parsed_and_blocked_reported(self):
        kid = {"data": {"title": "Sample", "ups": 5, "num_comments": 2, "permalink": "/r/RGV/comments/x/", "created_utc": NOW.timestamp(), "subreddit": "RGV", "selftext": "hi", "stickied": False, "over_18": False}}
        ok = json.dumps({"data": {"children": [kid]}})
        rows, st = ch.fetch_reddit(get=lambda u, **k: (200, ok), subs=["RGV"], pause=0)
        self.assertEqual(rows[0]["upvotes"], 5); self.assertTrue(st["r/RGV"]["ok"])
        rows, st = ch.fetch_reddit(get=lambda u, **k: (403, ""), subs=["RGV"], pause=0)
        self.assertEqual(rows, []); self.assertFalse(st["r/RGV"]["ok"]); self.assertIn("403", st["r/RGV"]["note"])

    def test_reddit_rss_fallback(self):
        rss = '<feed><entry><title>Hi &amp; bye</title><link href="https://www.reddit.com/r/RGV/comments/y/"/><updated>2026-11-19T10:00:00+00:00</updated></entry></feed>'
        def get(u, **k):
            return (200, rss) if u.endswith(".rss") else (403, "")
        rows, st = ch.fetch_reddit(get=get, subs=["RGV"], pause=0)
        self.assertEqual(rows[0]["title"], "Hi & bye"); self.assertIsNone(ch.engagement(rows[0]))

    def test_facebook_and_instagram_public_skip_honestly(self):
        rows, st = ch.fetch_facebook_public(get=lambda u, **k: (200, "<html>login</html>"))
        self.assertEqual(rows, []); self.assertTrue(all(not v["ok"] for v in st.values()))
        rows, st = ch.fetch_instagram_public(get=lambda u, **k: (404, ""))
        self.assertEqual(rows, []); self.assertFalse(st["instagram"]["ok"])

    def test_collect_offline_with_capture(self):
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "cap.json"); json.dump(fx.rows(NOW), (f := open(p, "w"))); f.close()
        b = ch.collect(p, HEAD, network=False, now=NOW)
        self.assertTrue(b["items"]); self.assertTrue(any(v["ok"] for v in b["sources"].values()))


class Studio(unittest.TestCase):
    def build(self, with_items):
        sys.path.insert(0, os.path.join(ROOT, "packet"))
        import build_packet as bp
        d = json.load(open(os.path.join(ROOT, "packet", "data", "packet-2026-11-19.json")))
        d.pop("chisme", None)
        if with_items:
            d["chisme"] = ch.build(fx.rows(NOW), HEAD, NOW)
        d = bp.prepare(d, os.path.join(ROOT, "obs-data.json"), False)
        return bp.studio_html(d), bp.txt(d), bp.email_html(d, True)

    def test_sections_and_cards(self):
        h, t, e = self.build(True)
        import re
        ids = re.findall(r'<details class="sec(?: blk)?" id="([^"]+)"', h)
        self.assertNotIn("rundown", ids)
        self.assertEqual([i[4:] for i in ids if i.startswith("blk-")], list("ABCDEFGHIJKL"))
        self.assertEqual(ids.index("chisme"), ids.index("headlines") + 1)
        self.assertIn("what the Valley is buzzing about", h)
        self.assertGreaterEqual(h.count("RUMOR · CONFIRM BEFORE AIR"), 4)
        self.assertIn("CONFIRMED · KRGV", h)
        self.assertIn("CHISME", t); self.assertIn("Chisme", e)

    def test_empty_state_never_invents(self):
        h, t, e = self.build(False)
        self.assertIn("No chisme loaded today", h)
        self.assertIn("nothing passed the safety filter", t)


if __name__ == "__main__":
    unittest.main()
