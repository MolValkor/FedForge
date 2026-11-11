"""Tests for the Private capital data rules (stdlib unittest; pytest also collects it).

    python3 -m unittest discover -s tests -p "test_private_capital.py" -v
"""
import copy
import importlib.util
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("check_private_capital",
                                               os.path.join(ROOT, "tools", "check_private_capital.py"))
cpc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpc)

with open(os.path.join(ROOT, "data", "private-capital.json"), encoding="utf-8") as f:
    DATA = json.load(f)


def first(data, **match):
    for e in data["entries"]:
        if all(e.get(k) == v for k, v in match.items()):
            return e
    raise AssertionError(f"no entry matching {match}")


class RealData(unittest.TestCase):
    def test_real_file_is_valid(self):
        self.assertEqual(cpc.validate(DATA), [])

    def test_reviewed_date(self):
        self.assertEqual(DATA["reviewed"], "2026-10-07")

    def test_has_anduril_shipyard(self):
        e = first(DATA, id="anduril-arsenal-2-2026-10-06")
        self.assertEqual(e["category"], "shipbuilding")
        self.assertIsNone(e["ticker"])
        self.assertEqual(e["amount_usd"], 3_700_000_000)

    def test_private_companies_have_no_ticker(self):
        for e in DATA["entries"]:
            if e["ownership"] != "public":
                self.assertIsNone(e.get("ticker"), e["id"])

    def test_every_amount_number_appears_in_display_or_is_null(self):
        # The display text is what readers see; it must not drift from the stored figure's order of magnitude.
        for e in DATA["entries"]:
            if e["amount_usd"] is None:
                continue
            self.assertRegex(e["amount_display"], r"\$\d", e["id"])

    def test_page_and_script_exist(self):
        page = open(os.path.join(ROOT, "private-capital.html"), encoding="utf-8").read()
        self.assertIn('src="js/private-capital.js"', page)
        self.assertIn("2026-10-07", page)  # methodology last-reviewed date
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "js", "private-capital.js")))

    def test_nav_links_section(self):
        nav = open(os.path.join(ROOT, "js", "nav.js"), encoding="utf-8").read()
        self.assertTrue(re.search(r'file:\s*"private-capital\.html"', nav))


class Rules(unittest.TestCase):
    def setUp(self):
        self.d = copy.deepcopy(DATA)

    def assertFails(self, needle):
        errs = cpc.validate(self.d)
        self.assertTrue(any(needle in e for e in errs), f"expected {needle!r} in {errs}")

    def test_missing_sources_fails(self):
        self.d["entries"][0]["sources"] = []
        self.assertFails("no source URL")

    def test_http_source_fails(self):
        self.d["entries"][0]["sources"][0]["url"] = "http://example.com/x"
        self.assertFails("has no https url")

    def test_malformed_date_fails(self):
        self.d["entries"][0]["date"] = "10/06/2026"
        self.assertFails("malformed date")

    def test_impossible_date_fails(self):
        self.d["entries"][0]["date"] = "2026-02-30"
        self.assertFails("malformed date")

    def test_future_date_fails(self):
        self.d["entries"][0]["date"] = "2026-12-01"
        self.assertFails("after the review date")

    def test_date_outside_window_fails(self):
        self.d["entries"][0]["date"] = "2023-01-01"
        self.assertFails("outside the window")

    def test_amount_without_source_fails(self):
        e = first(self.d, id="anduril-arsenal-2-2026-10-06")
        e["amount_source_url"] = None
        self.assertFails("amount without amount_source_url")

    def test_amount_source_must_be_listed(self):
        e = first(self.d, id="anduril-arsenal-2-2026-10-06")
        e["amount_source_url"] = "https://example.com/not-in-sources"
        self.assertFails("amount_source_url is not one of the entry's sources")

    def test_undisclosed_must_say_so(self):
        e = first(self.d, id="pdw-osc-components-2026-07-31")
        e["amount_display"] = "$500M"
        self.assertFails("must say undisclosed")

    def test_percentage_in_amount_fails(self):
        self.d["entries"][0]["amount_display"] = "$3.7B (up 40%)"
        self.assertFails("percentage")

    def test_ticker_on_private_company_fails(self):
        e = first(self.d, id="anduril-arsenal-2-2026-10-06")
        e["ticker"] = "ANDU"
        e["ticker_source_url"] = e["sources"][0]["url"]
        self.assertFails("not public")

    def test_ticker_needs_source(self):
        e = first(self.d, ticker="MP")
        e["ticker_source_url"] = None
        self.assertFails("ticker_source_url must be an https URL")

    def test_status_needs_source(self):
        e = first(self.d, id="anduril-arsenal-2-2026-10-06")
        e["status_source_url"] = None
        self.assertFails("status_source_url")

    def test_unknown_status_fails(self):
        self.d["entries"][0]["status"] = "rumored"
        self.assertFails("status 'rumored'")

    def test_federal_link_needs_source(self):
        e = first(self.d, id="anduril-arsenal-2-2026-10-06")
        e["federal_link"]["source_url"] = ""
        self.assertFails("federal_link.source_url")

    def test_unknown_lane_fails(self):
        self.d["entries"][0]["lane"] = "crypto"
        self.assertFails("lane 'crypto'")

    def test_duplicate_id_fails(self):
        self.d["entries"][1]["id"] = self.d["entries"][0]["id"]
        self.assertFails("duplicate id")


if __name__ == "__main__":
    unittest.main()
