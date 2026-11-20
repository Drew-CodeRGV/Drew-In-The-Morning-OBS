import copy, datetime, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "packet"))
import obituaries as ob  # noqa: E402
import build_packet as bp  # noqa: E402

D = datetime.date
# All names below are FAKE. The structure mirrors what Legacy embeds in the page (self.__next_f.push payload).


def person(pid, name, posted, died="2026-11-10", bio="", age=None, fh=None, monitor=True, url_slug=None):
    affs = []
    if monitor:
        affs.append({"site_name": "themonitor", "publisher_name": "The Monitor", "url": f"https://www.legacy.com/us/obituaries/themonitor/name/{url_slug or name.lower().replace(' ', '-')}-obituary?id={pid}", "id": 1, "order": 1})
    if fh:
        affs.append({"site_name": "legacypro", "publisher_name": fh, "url": "https://fh.example/o", "id": 2, "order": 2})
    return {"id": str(pid), "full_name": name, "death_date": died, "age": age, "bio": bio, "person_id": pid,
            "sortable_obituaries_date_posted_from": posted + "T00:00:00", "obituaries": [{"date_posted_from": posted, "affiliates": affs}]}


def page(people, n=1, total=3):
    payload = ('7:["$","div",null,{"initialData":{"results":' + json.dumps(people) + ',"total_hits":10000,"page":%d,"page_size":50,"total_pages":%d,"has_next":true}}}]' % (n, total))
    return '<html><body><script>self.__next_f.push([1,' + json.dumps(payload) + '])</script></body></html>'


P1 = [
    person(1, "Jane Q. Sample", "2026-11-19", died="2026-11-17", bio="Pharr - Jane Q. Sample , 83, died Tuesday, November 17, 2026, at home of cancer. Fake Funeral Home of Elsa is in charge of arrangements.", fh="Fake Funeral Home - Elsa"),
    person(2, "Juan Ejemplo", "2026-11-18", bio="EDINBURG- Juan Ejemplo, 71, passed away on November 14, 2026.", fh=None),
    person(3, "Maria Muestra", "2026-11-13", died="2026-11-11", bio="Maria Muestra 73, died Friday, November 11, 2026. Example Mortuary & Cremation Service of Mission, Tx. is in charge of arrangements."),
    person(4, "Baby Ejemplo", "2026-11-12", bio="Edinburg - Baby Ejemplo , 0, died Thursday, November 12, 2026."),
    person(5, "Not Monitor", "2026-11-18", monitor=False, fh="Other Funeral Home"),
    person(6, "Old Person", "2026-11-01", bio="Mission - Old Person , 90, died on October 30."),
]
P2 = [  # overlap with page 1 (Legacy pages overlap) + an older page-2 tail
    person(2, "Juan Ejemplo", "2026-11-18", bio="EDINBURG- Juan Ejemplo, 71, passed away on November 14, 2026."),
    person(7, "Rosa Vieja", "2026-11-06", bio="Mission - Rosa Vieja, 88, died November 5.", fh="Sample Funeral Home - Mission"),
    person(8, "Eva Muestra Garcia", "2026-11-09", died="2026-11-02", bio="McAllen - Eva Muestra Garcia, a beloved mother", fh="Kreidler Funeral Home, Inc. -"),
    person(9, "Muestra Garcia", "2026-11-07", died="2026-11-02", bio="Eva Muestra Garcia, a beloved mother"),
]
P3 = [person(10, "Way Older", "2026-10-20")]
PAGES = {1: page(P1, 1), 2: page(P2, 2), 3: page(P3, 3)}


def fetcher(calls=None):
    def f(url):
        n = int(url.split("page=")[1]) if "page=" in url else 1
        if calls is not None:
            calls.append(n)
        return (200, PAGES[n]) if n in PAGES else (404, "")
    return f


class Parse(unittest.TestCase):
    def test_parse_page_and_paging(self):
        arr, paging = ob.parse_page(PAGES[1])
        self.assertEqual(len(arr), 6)
        self.assertEqual(paging, {"page": 1, "page_size": 50, "total_pages": 3})

    def test_blocked_or_changed_page_raises(self):
        with self.assertRaises(ob.LegacyError):
            ob.parse_page("<html>Just a moment... challenge</html>")

    def test_normalize_fields_only_what_is_listed(self):
        arr, _ = ob.parse_page(PAGES[1])
        r = {x["name"]: x for x in (ob.normalize(p) for p in arr) if x}
        j = r["Jane Q. Sample"]
        self.assertEqual((j["age"], j["city"], j["died"], j["published"], j["funeralHome"]), (83, "Pharr", "2026-11-17", "2026-11-19", "Fake Funeral Home - Elsa"))
        self.assertTrue(j["url"].startswith("https://www.legacy.com/us/obituaries/themonitor/name/"))
        self.assertEqual(r["Juan Ejemplo"]["city"], "Edinburg")                       # "EDINBURG- " dateline, title-cased
        self.assertEqual(r["Maria Muestra"]["age"], 73)                              # "Name 73, died"
        self.assertEqual(r["Maria Muestra"]["funeralHome"], "Example Mortuary & Cremation Service of Mission, TX")
        self.assertIsNone(r["Baby Ejemplo"]["age"])                                  # an age of 0 is left blank, never guessed
        self.assertNotIn("Not Monitor", r)                                           # no Monitor notice -> not ours

    def test_no_cause_of_death_or_notice_text_is_kept(self):
        arr, _ = ob.parse_page(PAGES[1])
        blob = json.dumps([ob.normalize(p) for p in arr]).lower()
        self.assertNotIn("cancer", blob); self.assertNotIn("bio", blob); self.assertNotIn("at home", blob)


class Collect(unittest.TestCase):
    def test_window_overlap_dedupe_and_stop(self):
        calls = []
        res = ob.collect(15, today=D(2026, 11, 19), fetcher=fetcher(calls))
        names = [r["name"] for r in res["items"]]
        self.assertEqual(calls, [1, 2, 3])                      # stops after the page whose newest notice is outside the window
        self.assertEqual(len(names), len(set(names)))
        self.assertNotIn("Old Person", names); self.assertNotIn("Way Older", names)
        self.assertEqual(res["items"][0]["name"], "Jane Q. Sample")   # newest first
        self.assertEqual(res["window"], {"from": "2026-11-05", "to": "2026-11-19", "days": 15})

    def test_seven_day_window(self):
        res = ob.collect(7, today=D(2026, 11, 19), fetcher=fetcher())
        self.assertEqual({r["name"] for r in res["items"]}, {"Jane Q. Sample", "Juan Ejemplo", "Maria Muestra"})
        self.assertEqual(res["window"]["from"], "2026-11-13")

    def test_duplicate_person_records_merge(self):
        res = ob.collect(15, today=D(2026, 11, 19), fetcher=fetcher())
        self.assertEqual(res["mergedDuplicates"], 1)             # "Muestra Garcia" is inside "Eva Muestra Garcia", same death date
        self.assertEqual(sum(1 for r in res["items"] if "Garcia" in r["name"]), 1)
        self.assertEqual(next(r for r in res["items"] if "Garcia" in r["name"])["funeralHome"], "Kreidler Funeral Home, Inc.")

    def test_blocked_first_page_is_an_error_not_an_empty_list(self):
        with self.assertRaises(ob.LegacyError):
            ob.collect(7, today=D(2026, 11, 19), fetcher=lambda u: (403, ""))

    def test_text_output(self):
        res = ob.collect(7, today=D(2026, 11, 19), fetcher=fetcher())
        t = ob.to_text(res)
        self.assertIn("Jane Q. Sample, 83 · Pharr", t); self.assertIn("https://www.legacy.com/us/obituaries/themonitor/", t)


class Grouping(unittest.TestCase):
    def setUp(self):
        self.res = ob.collect(15, today=D(2026, 11, 19), fetcher=fetcher())

    def test_week_groups_newest_first_and_clipped_to_window(self):
        g = ob.week_groups(self.res["items"], "2026-11-19", "2026-11-05")
        self.assertEqual([x["label"] for x in g], ["Nov 13\u201319", "Nov 6\u201312"])
        self.assertEqual(g[0]["items"][0]["name"], "Jane Q. Sample")
        self.assertEqual([r["published"] for r in g[0]["items"]], sorted((r["published"] for r in g[0]["items"]), reverse=True))

    def test_read_script_is_gentle_names_ages_towns_only(self):
        s = ob.read_script(self.res["items"], "2026-11-19")
        self.assertTrue(s.startswith("We want to take a moment to remember some of our neighbors"))
        self.assertIn("Jane Q. Sample, 83, of Pharr", s)
        self.assertNotIn("Old Person", s); self.assertNotIn("Rosa Vieja", s)    # only the newest 7 days
        for bad in ("cancer", "died", "death", "passed", "cause"):
            self.assertNotIn(bad, s.lower())
        self.assertEqual(ob.read_script([], "2026-11-19"), "")


class Packet(unittest.TestCase):
    def packet(self, obits=True):
        d = json.load(open(os.path.join(ROOT, "packet", "data", "packet-2026-11-23.json")))
        d["obituaries"] = ob.collect(15, today=D(2026, 11, 19), fetcher=fetcher()) if obits else None
        if not obits:
            d.pop("obituaries")
        return bp.prepare(d, os.path.join(ROOT, "obs-data.json"), False)

    def test_prep_groups_script_and_picks(self):
        d = self.packet()
        o = d["obituaries"]
        self.assertEqual(o["count"], len(o["items"]))
        self.assertEqual([g["label"] for g in o["groups"]], ["Nov 13\u201319", "Nov 6\u201312"])
        self.assertTrue(o["script"]); self.assertTrue(set(o["pickUrls"]) <= {r["url"] for r in o["items"]})
        self.assertEqual(o["windowLabel"], "Nov 5\u201319")

    def test_missing_block_is_empty_not_invented(self):
        o = self.packet(False)["obituaries"]
        self.assertEqual((o["count"], o["script"], o["groups"]), (0, "", []))

    def test_bad_urls_are_dropped(self):
        d = {"obituaries": {"items": [{"name": "X Y", "url": "http://evil.example/x", "published": "2026-11-18"}, {"name": "Z", "url": "https://www.legacy.com/a", "published": "bad"}]}}
        d["obituaries"]["items"][1]["published"] = "2026-11-18"
        bp.prep_obituaries(d)
        self.assertEqual([r["name"] for r in d["obituaries"]["items"]], ["Z"])

    def test_sources_hold_every_notice_but_link_check_skips_them(self):
        d = self.packet()
        urls = [u["url"] for u in bp.all_urls(d) if u["section"] == "Remembering Our Neighbors"]
        self.assertIn(ob.SOURCE_URL, urls)
        self.assertTrue(all(r["url"] in urls for r in d["obituaries"]["items"]))

    def test_block_l_gets_the_read_and_block_structure_is_unchanged(self):
        obs = json.load(open(os.path.join(ROOT, "obs-data.json")))
        letters = [s["letter"] for s in obs["segments"]]
        self.assertEqual(letters, list("ABCDEFGHIJKL"))
        self.assertEqual(sum(s["durationMinutes"] for s in obs["segments"]), 60)
        L = next(s for s in obs["segments"] if s["letter"] == "L")
        self.assertEqual(L["chyrons"][0]["id"], "l1")                       # Companion maps chyrons[0] and headlines[0]: unchanged
        self.assertEqual(L["headlines"][-1], "Remembering our neighbors: obituaries from The Monitor")
        self.assertTrue(any(c["primary"] == "Remembering Our Neighbors" for c in L["chyrons"][1:]))
        self.assertTrue(all(len(c["primary"]) <= 60 and len(c["secondary"]) <= 60 for c in L["chyrons"]))
        tp = " ".join(L["talkingPoints"])
        self.assertIn("REMEMBERING OUR NEIGHBORS", tp); self.assertIn("NEVER mention how anyone died", tp)

    def test_renderers_include_section_and_stay_collapsed(self):
        d = json.load(open(os.path.join(ROOT, "packet", "data", "packet-2026-11-23.json")))
        d["obituaries"] = ob.collect(15, today=D(2026, 11, 19), fetcher=fetcher())
        d = bp.prepare(d, os.path.join(ROOT, "obs-data.json"), False)
        L = next(r for r in d["rundown"] if r["letter"] == "L")
        self.assertTrue(any(x.startswith("READ ALOUD, SLOWLY") for x in L["talkingPoints"]))
        studio = bp.studio_html(d)
        self.assertIn('id="obits"', studio)
        self.assertNotIn('<details class="sec blk" id="blk-L" open', studio)  # collapsed (no `open`)
        self.assertIn("Jane Q. Sample", studio); self.assertIn("Nov 13\u201319", studio)
        self.assertNotIn("cancer", studio.lower())
        email = bp.email_html(d, True)
        self.assertIn("Remembering Our Neighbors", email)
        newest = d["obituaries"]["groups"][0]["items"]; older = [r for g in d["obituaries"]["groups"][1:] for r in g["items"]]
        for r in newest:
            self.assertIn(r["url"], email)           # email and txt list only the newest 7 days ...
        t = bp.txt(d)
        self.assertIn("REMEMBERING OUR NEIGHBORS", t)
        for r in newest:
            self.assertIn(r["url"], t)
        if older:
            self.assertIn("Plus %d from the week before" % len(older), t)   # ... and say how many more the studio page has
            self.assertNotIn(older[0]["url"], t)
        # studio: newest week as compact cards, the week before behind one full-width button
        self.assertEqual(studio.count('class="ob"'), len(newest) + len(older))
        self.assertIn('id="obmore"', studio) if older else None
        self.assertIn("Show the previous week (%d)" % len(older), studio) if older else None
        self.assertIn("%d this week \u00b7 %d in 2 weeks" % (len(newest), len(newest) + len(older)), studio) if older else None
        self.assertNotIn("died of", studio.lower())
        card = studio[studio.index('class="ob"'):studio.index('class="ob"') + 400]
        self.assertNotIn("tldr", card); self.assertNotIn('class="ang"', card)
        pr = bp.print_html(d)
        self.assertIn("Obituaries: %d on studio page" % d["obituaries"]["count"], pr)


if __name__ == "__main__":
    unittest.main()
