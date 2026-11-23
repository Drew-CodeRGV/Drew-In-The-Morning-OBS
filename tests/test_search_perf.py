#!/usr/bin/env python3
"""Search must stay indexed + debounced so typing does not freeze the board."""
import os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SearchPerfSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = open(os.path.join(ROOT, "packet", "build_packet.py")).read()

    def test_applySearch_function_and_placeholder_stay(self):
        self.assertIn("function applySearch", self.src)
        self.assertIn("{SEARCH_JS}", self.src)

    def test_input_is_debounced_not_applied_on_every_keystroke(self):
        self.assertIn("qel.addEventListener('input',schedule)", self.src)
        self.assertNotIn("addEventListener('input',applySearch)", self.src)
        self.assertIn(",120)", self.src)
        self.assertIn("requestAnimationFrame", self.src)

    def test_index_uses_data_q_not_live_textContent(self):
        self.assertIn("el._qhay", self.src)
        self.assertIn("getAttribute('data-q')", self.src)
        # applySearch itself must not walk textContent of every card
        m = re.search(r"function applySearch\b.*?function\s+\w+", self.src, re.S)
        self.assertTrue(m, "applySearch not found")
        body = m.group(0)
        self.assertNotIn("el.textContent", body)
        # match-count uses cnt.textContent only; cards must not be scored via live textContent
        self.assertNotRegex(body, r"c\.el\.textContent|el\.textContent")

    def test_search_does_not_persist_forced_opens(self):
        self.assertIn("window.ditmSearchOpening", self.src)
        self.assertIn("if(window.ditmSearchOpening)return;", self.src)
        self.assertIn("snapshotOpen", self.src)
        self.assertIn("restoreOpen", self.src)

    def test_parked_aired_expired_are_skipped_unless_open(self):
        self.assertIn("isParkedSec", self.src)
        self.assertIn("aired", self.src[self.src.find("isParkedSec"):self.src.find("isParkedSec") + 400])
        self.assertIn("expired", self.src[self.src.find("isParkedSec"):self.src.find("isParkedSec") + 400])

    def test_content_visibility_and_lazy_thumb(self):
        self.assertIn("content-visibility:auto", self.src)
        self.assertIn("contain-intrinsic-size", self.src)
        self.assertIn('loading="lazy"', self.src)

    def test_tldr_uses_intersection_observer(self):
        i = self.src.find("TLDR_JS =")
        self.assertGreater(i, 0)
        tldr = self.src[i:i+4000]
        self.assertIn("IntersectionObserver", tldr)
        self.assertIn("function paint", tldr)
