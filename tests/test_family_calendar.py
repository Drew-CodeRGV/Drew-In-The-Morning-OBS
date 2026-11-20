import copy, datetime, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "packet"))
import family_calendar as fc  # noqa: E402
import build_packet as bp  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")
with open(os.path.join(FIX, "family-sample.ics"), "rb") as _f:
    ICS = _f.read()
CFG = fc.load_config(os.path.join(FIX, "family-calendar.test.yml"))
D = datetime.date


def run(mode="daily", today=D(2026, 11, 19), cfg=CFG):
    return fc.build(ICS, mode, today, cfg)


def labels(res, k="up_to"):
    return [g["label"] for g in res[k]]


class Classify(unittest.TestCase):
    def test_excluded_categories(self):
        for t in ["Riley dentist", "Alex haircut", "Electric bill", "Pick up Alex", "Gym", "Reservation: Fake Grill", "Pat's retirement party",
                  "Alex's birthday party", "Meeting with client", "Riley laser", "Check on Riley's glasses", "Unemployment call", "Support group", "Drop off Alex"]:
            self.assertFalse(fc.classify(t, CFG)["keep"], t)

    def test_unsure_defaults_to_excluded(self):
        c = fc.classify("Zorp", CFG)
        self.assertEqual((c["keep"], c["reason"]), (False, "unsure"))

    def test_included_with_generic_labels(self):
        self.assertEqual(fc.classify("Alex chess club", CFG)["label"], "chess club")
        self.assertEqual(fc.classify("Riley's hip hop", CFG)["label"], "hip hop class")
        self.assertEqual(fc.classify("Riley's school pic nic", CFG)["label"], "a school picnic")  # "pic" must not trip the photo exclusion
        self.assertEqual(fc.classify("Region Clinic & Concert", CFG)["label"], "the region clinic and concert")  # "clinic" is not medical here
        self.assertEqual(fc.classify("Springfield Fall Festival", CFG)["label"], "the Springfield Fall Festival")

    def test_unknown_word_or_possessive_in_festival_title_goes_generic(self):
        self.assertEqual(fc.classify("Chuck's Fall Festival", CFG)["label"], "a school or community event")
        self.assertEqual(fc.classify("Zorp Fall Festival", CFG)["label"], "a school or community event")

    def test_kid_names_flag(self):
        on = dict(CFG, NAME_KIDS_ON_AIR=True)
        self.assertEqual(fc.classify("Alex chess club", on)["label"], "Alex's chess club")
        self.assertEqual(fc.classify("Alex chess club", CFG)["label"], "chess club")
        roled = dict(CFG, kids=[{"name": "Alex", "role": "our son"}, {"name": "Riley", "role": ""}])
        self.assertEqual(fc.classify("Alex chess club", roled)["label"], "our son's chess club")

    def test_env_override_flips_names(self):
        os.environ["DITM_NAME_KIDS_ON_AIR"] = "true"
        try:
            self.assertTrue(fc.load_config(os.path.join(FIX, "family-calendar.test.yml"))["NAME_KIDS_ON_AIR"])
        finally:
            del os.environ["DITM_NAME_KIDS_ON_AIR"]
        self.assertFalse(fc.load_config(os.path.join(FIX, "family-calendar.test.yml"))["NAME_KIDS_ON_AIR"])

    def test_repo_config_defaults_to_not_naming_kids(self):
        self.assertFalse(fc.load_config()["NAME_KIDS_ON_AIR"])


class Build(unittest.TestCase):
    def test_daily_window_recurrence_and_collapse(self):
        r = run()  # Nov 13-19
        self.assertEqual(r["up_to_meta"]["window"], "Nov 13\u201319, 2026")
        got = {g["label"]: g for g in r["up_to"]}
        self.assertEqual(got["chess club"]["count"], 2)      # Tue + Wed collapse to one line
        self.assertEqual(got["hip hop class"]["count"], 1)   # RRULE expanded from a start date weeks earlier
        self.assertIn("the Springfield Fall Festival", got)
        self.assertIn("a school picnic", got)
        self.assertNotIn("the region clinic and concert", got)   # Nov 20 is after today
        self.assertEqual(r["up_to_coming"], [])               # daily mode has no coming-up list
        self.assertEqual(len([g for g in r["up_to"] if g["label"] == "chess club"]), 1)

    def test_monday_window_and_coming_up(self):
        r = run("monday", D(2026, 11, 23))
        self.assertEqual(r["up_to_meta"]["window"], "Nov 16\u201322, 2026")
        self.assertEqual(r["up_to_meta"]["comingWindow"], "Nov 23\u201329, 2026")
        self.assertIn("the region clinic and concert", labels(r))
        self.assertIn("a trip", labels(r))                     # all-day multi-day event starting Sat Nov 21
        self.assertIn("chess club", labels(r, "up_to_coming"))
        self.assertNotIn("the Springfield Fall Festival", labels(r))

    def test_cancelled_and_excluded_counts(self):
        r = run("monday", D(2026, 11, 23))
        self.assertNotIn("tennis camp", " ".join(labels(r)))
        self.assertEqual(r["up_to_meta"]["excludedCount"], 12)   # dentist, haircut, bill, pickup, 4 gym, reservation, retirement party, client meeting, "Zorp" (unsure)
        self.assertIn("left off the air", r["up_to_meta"]["internal"])

    def test_no_names_or_titles_leak_into_output(self):
        for mode, day in (("daily", D(2026, 11, 19)), ("monday", D(2026, 11, 23))):
            blob = json.dumps(run(mode, day)).lower()
            for bad in ("alex", "riley", "chuck", "pat's", "dentist", "haircut", "retirement", "reservation", "client", "bill", "gym", "zorp", "fake grill"):
                self.assertNotIn(bad, blob, bad)

    def test_named_when_flag_on(self):
        blob = json.dumps(run(cfg=dict(CFG, NAME_KIDS_ON_AIR=True)))
        self.assertIn("Alex's chess club", blob)
        self.assertNotIn("Chuck", blob)   # adults are never named

    def test_script_shape(self):
        r = run("monday", D(2026, 11, 23))
        s = r["up_to_script"]
        self.assertIn("Test house", s); self.assertIn("Coming up this week", s); self.assertIn("chess club twice", s)
        self.assertLessEqual(len(s.split()), 100)
        self.assertGreaterEqual(len(s.split()), 25)
        self.assertNotIn("CONFIRM", s)

    def test_quiet_week(self):
        r = run("daily", D(2026, 3, 2))
        self.assertEqual((r["up_to"], r["up_to_coming"], r["up_to_meta"]["status"]), ([], [], "none"))
        self.assertTrue(r["up_to_script"].startswith("Quiet week on the family calendar"))
        self.assertIn("Jess", r["up_to_script"])


class Secrets(unittest.TestCase):
    def test_no_private_feed_url_in_repo(self):
        bad = ("icloud.com/published", "caldav.icloud.com", "webcal://")
        token = ""   # the private feed's own token, read from the box file when it exists (never written here)
        if os.path.exists(fc.URL_FILE):
            with open(fc.URL_FILE) as fh:
                token = fh.read().strip().rstrip("/").split("/")[-1]
            token = token if len(token) > 20 else ""
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", "raw", "out")]
            for f in files:
                if not f.endswith((".py", ".md", ".yml", ".yaml", ".json", ".txt", ".js", ".html", ".ics")) or f == "test_family_calendar.py":
                    continue
                with open(os.path.join(base, f), errors="ignore") as fh:
                    txt = fh.read()
                for b in bad:
                    if b in txt and not (f.endswith(".md") or f == "family_calendar.py"):
                        self.fail(f"{b} found in {os.path.join(base, f)}")
                if token:
                    self.assertNotIn(token, txt, f)

    def test_fetch_error_never_contains_url(self):
        os.environ["DITM_FAMILY_ICS_URL"] = "https://127.0.0.1:9/secret-token-path.ics"
        try:
            with self.assertRaises(fc.CalendarError) as cm:
                fc.fetch_ics(timeout=2)
            self.assertNotIn("secret-token-path", str(cm.exception))
        finally:
            del os.environ["DITM_FAMILY_ICS_URL"]


def minimal_packet_data():
    d = json.load(open(os.path.join(ROOT, "packet", "data", "packet-2026-11-23.json")))
    d["up_to"], d["up_to_coming"] = [], []
    d.pop("up_to_script", None); d.pop("up_to_meta", None)
    return d


class PacketBlockB(unittest.TestCase):
    def test_prep_and_renderers_use_family_items_only(self):
        d = minimal_packet_data()
        r = run("monday", D(2026, 11, 23))
        d.update({k: copy.deepcopy(r[k]) for k in ("up_to", "up_to_coming", "up_to_script", "up_to_meta")})
        bp.prep_up_to(d)
        self.assertEqual(d["up_to_meta"]["status"], "found")
        self.assertIn("coming up", d["up_to_meta"]["banner"])
        lines = bp.upto_lines(d)
        self.assertTrue(any(x.startswith("chess club") for x in lines)); self.assertTrue(any(x.startswith("COMING UP") for x in lines))

    def test_empty_week_script_in_packet(self):
        d = minimal_packet_data(); bp.prep_up_to(d)
        self.assertTrue(d["up_to_script"].startswith("Quiet week on the family calendar"))
        self.assertEqual(d["up_to_meta"]["banner"], "Quiet week on the family calendar")

    def test_packet_data_files_have_no_gmail_block_b(self):
        for f in ("packet-2026-11-19.json", "packet-2026-11-23.json"):
            d = json.load(open(os.path.join(ROOT, "packet", "data", f)))
            blob = json.dumps({k: d[k] for k in ("up_to", "up_to_coming", "up_to_script", "up_to_meta")}).lower()
            for bad in ("proposal", "conference", "gmail", "rescon", "safre", "iaem"):
                self.assertNotIn(bad, blob, (f, bad))
            for e in d["up_to"] + d["up_to_coming"]:
                self.assertEqual(set(e), {"date", "label", "category", "count"})


if __name__ == "__main__":
    unittest.main()
