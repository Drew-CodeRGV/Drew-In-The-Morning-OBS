#!/usr/bin/env python3
"""On-air hooks and energy scores: no invented facts, energy sort, badges."""
import os, re, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packet"))
import build_packet as bp  # noqa: E402


def story(**kw):
    it = {"title": kw.pop("title", "A story"), "url": kw.pop("url", "https://example.com/s")}
    it.update(kw)
    return it


class HookDerivation(unittest.TestCase):
    def test_packet_hook_is_used_and_clipped(self):
        hook = "McAllen opens a new downtown park with a Saturday ribbon cutting and live music all afternoon plus fireworks"
        it = story(title="City opens a park", tldr="The city opened a park Saturday.", hook=hook)
        out = bp.story_hook(it)
        self.assertTrue(out.startswith("McAllen opens a new downtown park"))
        self.assertLessEqual(len(out), 120)
        self.assertEqual(out, hook[:len(out)] if len(hook) <= 120 else out)

    def test_derived_hook_tokens_come_from_source_fields(self):
        it = story(
            title="Edinburg Cares food drive delivers 1,000 turkeys and 1,000 food baskets to local families",
            tldr="The City of Edinburg delivered 1,000 turkeys and 1,000 food baskets through its annual Edinburg Cares food drive.",
            _desk="rgv",
            valley=True,
        )
        hook = bp.derive_story_hook(it)
        self.assertTrue(hook)
        self.assertLessEqual(len(hook), 120)
        self.assertTrue(bp.hook_is_factual(hook, it), hook)
        self.assertIn("1,000", hook)
        self.assertIn("turkeys", hook.lower())

    def test_derived_hook_does_not_invent_numbers(self):
        it = story(title="Council approves a downtown plan", tldr="The council approved a downtown plan Tuesday.")
        hook = bp.derive_story_hook(it)
        self.assertTrue(bp.hook_is_factual(hook, it), hook)
        self.assertNotRegex(hook, r"\d")

    def test_chisme_hook_keeps_rumor_label(self):
        it = story(title="People are talking about a new downtown mural", badge="RUMOR · CONFIRM BEFORE AIR", _desk="chisme")
        hook = bp.story_hook(it)
        self.assertTrue(hook.startswith("RUMOR · CONFIRM BEFORE AIR"), hook)
        self.assertTrue(bp.hook_is_factual(hook, it), hook)

    def test_tragedy_hook_is_respectful_not_hype(self):
        it = story(
            title="Mission police investigate a deadly head-on crash at 3 Mile Line Road and Maria Street",
            tldr="Mission police are investigating a deadly head-on crash.",
            _desk="rgv",
        )
        hook = bp.derive_story_hook(it)
        self.assertTrue(hook.startswith("Developing:") or hook.startswith("Big one:"), hook)
        self.assertTrue(bp.hook_is_factual(hook, it), hook)
        for banned in ("shocking", "unbelievable", "must-see", "you won't believe", "horrific"):
            self.assertNotIn(banned, hook.lower())
        self.assertLessEqual(bp.story_energy(it), 2)

    def test_kids_are_not_named_in_the_hook(self):
        it = story(
            title="A 5th-grade student named Maya Lopez wins a science fair scholarship",
            tldr="Fifth-grade student Maya Lopez won a science fair scholarship at her school.",
            _desk="rgv",
        )
        # Force the family/kids path even if the classifier changes.
        it["kids"] = True
        hook = bp.story_hook(it)
        self.assertNotIn("Maya", hook)
        self.assertNotIn("Lopez", hook)
        self.assertTrue(bp.hook_is_factual(hook, it) or "Maya" not in hook, hook)

    def test_death_star_law_is_not_treated_as_a_fatality(self):
        it = story(title="Texas Supreme Court leaves the 'Death Star' law limiting city ordinances intact")
        self.assertFalse(bp.is_tragedy_story(it))
        hook = bp.story_hook(it)
        self.assertFalse(hook.startswith("Developing:"), hook)


class EnergyAndBadges(unittest.TestCase):
    def test_packet_energy_field_wins(self):
        it = story(title="A mild zoning update", energy=5, _desk="rgv")
        self.assertEqual(bp.story_energy(it), 5)
        it2 = story(title="A mild zoning update", energy="2", _desk="rgv")
        self.assertEqual(bp.story_energy(it2), 2)

    def test_feel_good_local_with_numbers_is_high_energy(self):
        it = story(
            title="Edinburg Cares food drive delivers 1,000 turkeys and 1,000 food baskets to local families",
            tldr="The City of Edinburg delivered 1,000 turkeys and 1,000 food baskets ahead of Thanksgiving.",
            _desk="rgv",
            valley=True,
        )
        self.assertGreaterEqual(bp.story_energy(it), 4)
        label, kind = bp.energy_badge(it)
        self.assertEqual(kind, "feel")
        self.assertIn("FEEL-GOOD", label)

    def test_obits_are_neutral(self):
        it = story(title="Neighbors remember a longtime teacher", _desk="obituaries", obit=True)
        self.assertEqual(bp.story_energy(it), 2)
        self.assertEqual(bp.energy_badge(it), ("", ""))

    def test_turkey_the_country_is_not_a_food_win(self):
        it = story(title="COP31 climate talks in Turkey end with no deal", tldr="The UN climate summit in Antalya closed without a final pact.", _desk="trending")
        label, kind = bp.energy_badge(it)
        self.assertNotEqual(kind, "feel", (label, bp.story_energy(it)))
        self.assertLess(bp.story_energy(it), 5)

    def test_high_energy_sorts_first_with_newest_tiebreaker(self):
        low = story(title="Quiet council preview", _desk="rgv", energy=2)
        low["_when"] = 200
        high_old = story(title="Edinburg Cares food drive delivers 1,000 turkeys", tldr="1,000 turkeys delivered.", _desk="rgv", energy=5)
        high_old["_when"] = 50
        high_new = story(title="Edinburg Cares food drive delivers 2,000 turkeys", tldr="2,000 turkeys delivered.", _desk="rgv", energy=5)
        high_new["_when"] = 100
        out = bp.sort_stories_by_energy([low, high_old, high_new])
        self.assertEqual([i["title"] for i in out], [high_new["title"], high_old["title"], low["title"]])

    def test_badges_map(self):
        self.assertEqual(bp.energy_badge(story(title="Routine item", energy=3, _desk="texas")), ("", ""))
        self.assertEqual(bp.energy_badge(story(title="A big data-center vote", energy=4, _desk="rgv"))[1], "big")
        self.assertEqual(bp.energy_badge(story(title="A huge SpaceX launch window", energy=5, _desk="rgv"))[1], "hot")

    def test_lead_prefers_high_energy_local_feel_good(self):
        mild = story(title="Council takes testimony", energy=3, _desk="texas")
        mild["_when"] = 300
        mild["_packet_date"] = "2026-11-23"
        lead = story(
            title="Edinburg Cares food drive delivers 1,000 turkeys and 1,000 food baskets to local families",
            tldr="The City of Edinburg delivered 1,000 turkeys and 1,000 food baskets.",
            _desk="rgv",
            valley=True,
            energy=5,
        )
        lead["_when"] = 200
        lead["_packet_date"] = "2026-11-23"
        rumor = story(title="People are talking about a thing", energy=5, _desk="chisme", badge="RUMOR · CONFIRM BEFORE AIR")
        rumor["_when"] = 400
        rumor["_packet_date"] = "2026-11-23"
        picked = bp.pick_lead_story([mild, lead, rumor], "2026-11-23")
        self.assertEqual(picked["title"], lead["title"])


class StudioHookMarkup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import datetime, json, tempfile, subprocess
        cls.tmp = tempfile.mkdtemp()
        subprocess.run(
            [sys.executable, os.path.join(ROOT, "tests", "make_ui_fixture.py"), cls.tmp],
            check=True, capture_output=True,
        )
        cls.studio = open(os.path.join(cls.tmp, "out", "DITM-briefing-2026-11-19-studio.html")).read()
        cls.src = open(os.path.join(ROOT, "packet", "build_packet.py")).read()

    def test_cards_have_hooks_and_energy(self):
        self.assertIn('class="hook"', self.studio)
        self.assertIn('data-en="', self.studio)
        self.assertIn("Lead with this", self.studio)
        self.assertIn('id="lead"', self.studio)
        self.assertTrue(re.search(r"ebadge eb-(hot|big|feel)", self.studio))
        self.assertIn("function applySearch", self.src)
        self.assertIn("ditm-aired-v1", self.src)
        self.assertIn("||'energy'", self.src)

    def test_hooks_in_catalog_and_recap(self):
        self.assertIn("hookOrTitle", self.studio)
        m = re.search(r'id="ditm-stories">(.*?)</script>', self.studio, re.S)
        self.assertTrue(m)
        import json
        cat = json.loads(m.group(1))
        self.assertTrue(any(s.get("hook") for s in cat))
        self.assertTrue(any(s.get("energy") for s in cat))

    def test_no_secrets(self):
        self.assertNotRegex(self.studio, r"ditm-ros-[0-9a-f]{6,}")
        self.assertNotIn("p40-caldav", self.studio)


if __name__ == "__main__":
    unittest.main()
