#!/usr/bin/env python3
"""Rolling 7-day news window: merge, dedupe, stale drop-off, stable remove ids."""
import datetime, json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packet"))
import build_packet as bp  # noqa: E402

D = datetime.date
TODAY = D(2026, 11, 21)


def item(title, url="", published="", **extra):
    it = {"title": title, "url": url, "short": title}
    if published:
        it["published"] = published
    it.update(extra)
    return it


def write_packet(folder, day, **lists):
    data = {"meta": {"date": day.isoformat()}, "headlines": {"rgv": lists.get("rgv") or [], "texas": lists.get("texas") or []},
            "nationalDesk": lists.get("national") or [], "trending": lists.get("trending") or [],
            "tech": {"items": lists.get("tech") or []}, "chisme": {"items": lists.get("chisme") or []}}
    os.makedirs(os.path.join(folder, "packet", "data"), exist_ok=True)
    path = os.path.join(folder, "packet", "data", f"packet-{day.isoformat()}.json")
    json.dump(data, open(path, "w"))
    return data


class RemoveIds(unittest.TestCase):
    def test_same_url_is_stable_across_days_and_tracking_params(self):
        a = item("Hello World", "https://www.KRGV.com/news/foo/?utm_source=x&fbclid=1")
        b = item("Hello World", "https://krgv.com/news/foo")
        self.assertEqual(bp.story_remove_id(a), bp.story_remove_id(b))
        self.assertTrue(bp.story_remove_id(a).startswith("r-"))
        self.assertRegex(bp.story_remove_id(a), r"^r-[0-9a-f]{16}$")

    def test_headline_only_is_stable_when_url_is_missing(self):
        a = item("  Voters  Approve  Plan ")
        b = item("voters approve plan")
        self.assertEqual(bp.story_remove_id(a), bp.story_remove_id(b))
        self.assertNotEqual(bp.story_remove_id(a), bp.story_remove_id(item("A different headline")))

    def test_url_wins_over_headline(self):
        a = item("One title", "https://example.com/story")
        b = item("A rewritten headline", "https://example.com/story")
        self.assertEqual(bp.story_remove_id(a), bp.story_remove_id(b))


class WeekMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_dedupe_keeps_the_newest_copy(self):
        older = write_packet(self.tmp, D(2026, 11, 19), rgv=[
            item("Food truck park", "https://krgv.com/park", "2026-11-19T08:00:00-06:00", source="Tue"),
        ])
        today = write_packet(self.tmp, TODAY, rgv=[
            item("Food truck park — update", "https://krgv.com/park", "2026-11-21T09:00:00-06:00", source="Sat"),
            item("Only on Saturday", "https://krgv.com/sat", "2026-11-21T10:00:00-06:00"),
        ])
        # also an in-between day
        write_packet(self.tmp, D(2026, 11, 20), rgv=[
            item("Food truck park mid", "https://krgv.com/park", "2026-11-20T12:00:00-06:00", source="Fri"),
        ])
        w = bp.merge_week_news(today, self.tmp, TODAY)
        parks = [i for i in w["rgv"] if "krgv.com/park" in (i.get("url") or "")]
        self.assertEqual(len(parks), 1, parks)
        self.assertEqual(parks[0]["source"], "Sat")
        self.assertEqual(parks[0]["_date_tag"], "Nov 21")
        titles = [i["title"] for i in w["rgv"]]
        self.assertIn("Only on Saturday", titles)
        self.assertEqual(len(w["rgv"]), 2)

    def test_stale_stories_older_than_seven_days_drop_off(self):
        today = write_packet(self.tmp, TODAY, rgv=[
            item("Fresh", "https://krgv.com/fresh", "2026-11-21T08:00:00-06:00"),
        ])
        write_packet(self.tmp, D(2026, 11, 15), rgv=[
            item("Edge of window", "https://krgv.com/edge", "2026-11-15T08:00:00-06:00"),
        ])
        write_packet(self.tmp, D(2026, 11, 14), rgv=[
            item("Too old packet", "https://krgv.com/old-pkt", "2026-11-14T08:00:00-06:00"),
        ])
        # a story that landed in today's packet but was published 8 days ago
        today["headlines"]["rgv"].append(item("Stale pub", "https://krgv.com/stale", "2026-11-13T12:00:00-06:00"))
        w = bp.merge_week_news(today, self.tmp, TODAY)
        urls = [i["url"] for i in w["rgv"]]
        self.assertIn("https://krgv.com/fresh", urls)
        self.assertIn("https://krgv.com/edge", urls)
        self.assertNotIn("https://krgv.com/old-pkt", urls)
        self.assertNotIn("https://krgv.com/stale", urls)
        self.assertNotIn(D(2026, 11, 14), w["found"])
        self.assertEqual(w["window"], (D(2026, 11, 15), TODAY))

    def test_confirm_labels_are_carried_unchanged(self):
        today = write_packet(self.tmp, TODAY, rgv=[
            item("Needs a check", "https://krgv.com/c", "2026-11-21T08:00:00-06:00", confirm="CONFIRM BEFORE AIR"),
        ])
        w = bp.merge_week_news(today, self.tmp, TODAY)
        self.assertEqual(w["rgv"][0]["confirm"], "CONFIRM BEFORE AIR")

    def test_real_repo_packets_for_nov_21(self):
        path = os.path.join(ROOT, "packet", "data", "packet-2026-11-21.json")
        if not os.path.exists(path):
            self.skipTest("today packet missing")
        d = json.load(open(path))
        w = bp.merge_week_news(d, ROOT, TODAY)
        self.assertEqual(w["window"], (D(2026, 11, 15), TODAY))
        self.assertIn(TODAY, w["found"])
        self.assertIn(D(2026, 11, 20), w["found"])
        self.assertIn(D(2026, 11, 19), w["found"])
        # no structured packets in the repo for Nov 15–18
        for day in (D(2026, 11, 15), D(2026, 11, 16), D(2026, 11, 17), D(2026, 11, 18)):
            self.assertIn(day, w["missing"])
        # more than today's RGV alone, and nothing invented (every item has a title)
        self.assertGreater(len(w["rgv"]), len(d["headlines"]["rgv"]))
        for desk in ("rgv", "texas", "national", "trending", "tech", "chisme"):
            for it in w[desk]:
                self.assertTrue(it.get("title"))
                self.assertTrue(it.get("_rmid", "").startswith("r-"))
                self.assertTrue(it.get("_date_tag"))


class StudioRemoveControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = open(os.path.join(ROOT, "packet", "build_packet.py")).read()

    def test_remove_button_and_more_menu_are_in_the_template(self):
        self.assertIn('aria-label="Remove story"', self.src)
        self.assertIn('class="rmx"', self.src)
        self.assertIn("ditm-removed-v1", self.src)
        self.assertIn("Removed \\u00B7", self.src)
        self.assertIn("id=\"rm-show\"", self.src)
        self.assertIn("id=\"rm-restore\"", self.src)
        self.assertIn("Restore all", self.src)
        self.assertIn("min-width:44px", self.src[self.src.find(".rmx{"):self.src.find(".rmx{")+180])

    def test_chyron_page_does_not_register_remove_commands(self):
        # linked dashboards may publish remove/restore; the on-air chyron must ignore them
        self.assertIn("remove:1,restore:1", self.src)
        for name in ("docs/chyron.html", "companion/chyron.template.html"):
            path = os.path.join(ROOT, name)
            if not os.path.exists(path):
                continue
            text = open(path).read()
            self.assertNotRegex(text, r"CMDS=\{[^}]*\bremove\b")
            self.assertIn("!Object.prototype.hasOwnProperty.call(CMDS,c.cmd))return false", text)


if __name__ == "__main__":
    unittest.main()
