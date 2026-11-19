import datetime, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import breaking_watch as bw  # noqa: E402
import trend_score as ts  # noqa: E402

UTC = ts.UTC
CFG = ts.load_config(ROOT)
T0 = datetime.datetime(2026, 11, 18, 12, 0, tzinfo=UTC)  # 6:00 AM CT
FEEDS = {"feeds": [
    {"id": "vc", "name": "ValleyCentral", "url": "https://vc.test/feed", "kind": "local"},
    {"id": "kr", "name": "KRGV", "url": "https://kr.test/feed", "kind": "local"},
    {"id": "dead", "name": "Dead", "url": "https://dead.test/feed", "kind": "local", "optional": True},
]}


def rss(items):
    out = '<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
    for title, link, when in items:
        out += f"<item><title>{title}</title><link>{link}</link><pubDate>{when.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate></item>"
    return out + "</channel></rss>"


def make_fetch(pages, calls=None):
    def fetch(url, timeout=20, retries=1):
        if calls is not None:
            calls.append(url)
        if url in pages:
            return 200, pages[url]
        return 404, ""
    return fetch


class Parse(unittest.TestCase):
    def test_fixture(self):
        with open(os.path.join(ROOT, "tests", "fixtures", "rss_sample.xml")) as f:
            items = bw.parse_feed(f.read(), {"id": "x", "name": "VC", "kind": "local"})
        self.assertEqual(len(items), 1)  # no-link and javascript: links dropped
        self.assertEqual(items[0]["title"], "Fire at McAllen warehouse forces evacuation & closes road")
        self.assertEqual(items[0]["text"], "Firefighters")

    def test_bad_xml(self):
        with self.assertRaises(ValueError):
            bw.parse_feed("<html>nope", {"id": "x"})


class Cycle(unittest.TestCase):
    def cycle(self, pages, state, now, **kw):
        return bw.run(FEEDS, CFG, state, now, fetch=make_fetch(pages), **kw)

    def test_bootstrap_then_new_alert_then_quiet(self):
        state = {}
        old = [("Weslaco library adds Saturday hours", "https://vc.test/a", T0 - datetime.timedelta(hours=2))]
        r1 = self.cycle({"https://vc.test/feed": rss(old)}, state, T0)
        self.assertEqual(r1["alerts"], [])  # first run: bootstrap, nothing alerts
        self.assertTrue(r1["breaking"]["bootstrap"])
        t1 = T0 + datetime.timedelta(minutes=15)
        fire = ("Shooting reported near McAllen high school, police on scene", "https://kr.test/fire", t1 - datetime.timedelta(minutes=5))
        r2 = self.cycle({"https://vc.test/feed": rss(old), "https://kr.test/feed": rss([fire])}, state, t1)
        self.assertEqual(len(r2["alerts"]), 1)
        self.assertIn("geo+urgent", r2["alerts"][0]["reasons"][0])
        for al in r2["alerts"]:  # main() marks delivered ones
            for rec in state["items"]:
                if rec["id"] == al["id"]:
                    rec["alerted"] = True
        t2 = t1 + datetime.timedelta(minutes=15)
        r3 = self.cycle({"https://vc.test/feed": rss(old), "https://kr.test/feed": rss([fire])}, state, t2)
        self.assertEqual(r3["alerts"], [])
        self.assertEqual(r3["breaking"]["counts"]["alert"], 1)
        self.assertEqual(r3["breaking"]["items"][0]["level"], "alert")

    def test_same_story_from_second_outlet_does_not_realert(self):
        state = {}
        self.cycle({"https://vc.test/feed": rss([("Quiet item for bootstrap", "https://vc.test/q", T0)])}, state, T0)
        t1 = T0 + datetime.timedelta(minutes=15)
        a = ("Fire forces evacuation of McAllen apartment complex", "https://vc.test/f1", t1)
        r = self.cycle({"https://vc.test/feed": rss([a])}, state, t1)
        self.assertEqual(len(r["alerts"]), 1)
        for rec in state["items"]:
            rec["alerted"] = True
        t2 = t1 + datetime.timedelta(minutes=15)
        b = ("McAllen apartment complex evacuated after fire", "https://kr.test/f2", t2)
        r2 = self.cycle({"https://vc.test/feed": rss([a]), "https://kr.test/feed": rss([b])}, state, t2)
        self.assertEqual(r2["alerts"], [])

    def test_late_item_is_recorded_not_alerted(self):
        state = {}
        self.cycle({"https://vc.test/feed": rss([("Quiet", "https://vc.test/q", T0)])}, state, T0)
        t1 = T0 + datetime.timedelta(minutes=15)
        late = ("Shooting in McAllen from yesterday", "https://vc.test/late", t1 - datetime.timedelta(hours=10))
        r = self.cycle({"https://vc.test/feed": rss([late])}, state, t1)
        self.assertEqual(r["alerts"], [])

    def test_feed_backoff(self):
        state = {}
        for i in range(bw.BACKOFF_FAILS):
            r = self.cycle({}, state, T0 + datetime.timedelta(minutes=15 * i))
        self.assertFalse(r["status"]["dead"]["ok"])
        calls = []
        bw.run(FEEDS, CFG, state, T0 + datetime.timedelta(minutes=15 * 7), fetch=make_fetch({}, calls))
        self.assertNotIn("https://dead.test/feed", calls)
        calls = []
        bw.run(FEEDS, CFG, state, T0 + datetime.timedelta(hours=8), fetch=make_fetch({}, calls))
        self.assertIn("https://dead.test/feed", calls)


class Alerts(unittest.TestCase):
    A = [{"id": "1", "title": "Shooting near McAllen school @everyone", "url": "https://x.test/a", "source": "KRGV", "score": 40, "label": "Trending",
          "uncovered": False, "reasons": ["geo+urgent: McAllen, shooting"], "always": False, "why": "Score 40", "sources": [{"name": "KRGV", "url": "https://x.test/a"}]}]

    def test_ntfy_only_when_topic_set(self):
        calls = []
        post = lambda url, body, h, timeout=15: (calls.append((url, body, h)) or (200, "ok"))
        self.assertEqual(bw.send_ntfy([dict(self.A[0])], env={}, post=post), 0)
        self.assertEqual(calls, [])
        n = bw.send_ntfy([dict(self.A[0])], env={"NTFY_TOPIC": "secret-topic", "NTFY_TOKEN": "tk"}, post=post)
        self.assertEqual(n, 1)
        url, body, h = calls[0]
        self.assertEqual(url, "https://ntfy.sh")
        self.assertEqual(body["topic"], "secret-topic")
        self.assertEqual(h["Authorization"], "Bearer tk")
        self.assertIn("CONFIRM BEFORE AIR", body["message"])

    def test_ntfy_cap_and_summary(self):
        calls = []
        post = lambda url, body, h, timeout=15: (calls.append(body) or (200, "ok"))
        many = [dict(self.A[0], id=str(i)) for i in range(8)]
        bw.send_ntfy(many, env={"NTFY_TOPIC": "t"}, post=post)
        self.assertEqual(len(calls), bw.NTFY_PER_RUN + 1)
        self.assertIn("+3 more", calls[-1]["message"])

    def test_issues_gated_capped_and_sanitized(self):
        calls = []
        def post(url, body, h, timeout=15):
            calls.append((url, body, h))
            return 201, "{}"
        st = {}
        self.assertEqual(bw.open_issues([dict(self.A[0])], st, env={"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}, post=post), 0)  # off by default
        env = {"BREAKING_ISSUES": "true", "GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}
        many = [dict(self.A[0], id=str(i), score=50 - i, label="Hot") for i in range(9)]
        n = bw.open_issues(many, st, env=env, post=post, today="2026-11-18")
        self.assertEqual(n, bw.ISSUES_PER_RUN)
        url, body, h = calls[0]
        self.assertEqual(url, "https://api.github.com/repos/o/r/issues")
        self.assertEqual(body["labels"], ["breaking"])
        self.assertNotIn("@everyone", body["title"] + body["body"])
        self.assertIn("CONFIRM BEFORE AIR", body["body"])

    def test_issue_label_422_retries_without_label(self):
        seq = []
        def post(url, body, h, timeout=15):
            seq.append("labels" in body)
            return (422, "bad label") if "labels" in body else (201, "{}")
        n = bw.open_issues([dict(self.A[0], label="Hot")], {}, env={"BREAKING_ISSUES": "1", "GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}, post=post)
        self.assertEqual((n, seq), (1, [True, False]))

    def test_daily_issue_cap(self):
        post = lambda url, body, h, timeout=15: (201, "{}")
        st = {"issues": {"date": "2026-11-18", "n": bw.ISSUES_PER_DAY}}
        n = bw.open_issues([dict(self.A[0], label="Hot")], st, env={"BREAKING_ISSUES": "1", "GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}, post=post, today="2026-11-18")
        self.assertEqual(n, 0)


class Window(unittest.TestCase):
    def test_in_window(self):
        self.assertTrue(bw.in_window(datetime.datetime(2026, 11, 18, 12, 30, tzinfo=UTC), "05:00-11:00"))   # 6:30 CST
        self.assertFalse(bw.in_window(datetime.datetime(2026, 11, 18, 18, 0, tzinfo=UTC), "05:00-11:00"))   # 12:00 CST
        self.assertTrue(bw.in_window(datetime.datetime(2026, 7, 1, 10, 15, tzinfo=UTC), "05:00-11:00"))     # 5:15 CDT


if __name__ == "__main__":
    unittest.main()
