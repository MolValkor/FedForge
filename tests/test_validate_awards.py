"""Tests for the data-quality gate tools/pipeline/validate_awards.py."""
import copy
import json
import math
import os
from datetime import date

import pytest

import validate_awards as va
from conftest import REPO, make_doc, make_row

TODAY = date(2026, 10, 7)
LANES = ["nuclear", "magnets", "chips"]


def good_doc(n=3):
    rows = [make_row(id=f"A{i}", source_url=f"https://www.usaspending.gov/award/ASST_NON_A{i}_089",
                     sector=LANES[i % 3], amount=1_000_000.0 + i) for i in range(n)]
    return make_doc(rows)


def check(doc, **kw):
    kw.setdefault("lanes", LANES)
    kw.setdefault("today", TODAY)
    return va.validate(doc, **kw)


def test_good_doc_passes():
    res = check(good_doc(), verified_tickers=set())
    assert res.ok and res.errors == [] and res.warnings == []
    assert "PASSED" in res.render_md()


def test_committed_awards_file_passes_against_itself():
    path = os.path.join(REPO, "data", "awards.json")
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    meta = json.load(open(os.path.join(REPO, "data", "meta.json"), encoding="utf-8"))
    tickers = va.repo_verified_tickers([os.path.join(REPO, "data", n) for n in ("curated.json", "public-primes.json", "awards.json")])
    res = check(doc, previous=doc, verified_tickers=tickers, meta=meta, js_doc=va.load_js(os.path.join(REPO, "js", "awards-data.js")))
    assert res.ok, res.errors


# --- one mutation per check; each must fail the gate -------------------------------------------------------

def _mut(fn):
    d = good_doc()
    fn(d)
    return d


ERROR_CASES = {
    "missing amount": (lambda d: d["awards"][0].pop("amount"), "missing field(s) amount"),
    "missing id": (lambda d: d["awards"][0].pop("id"), "id is blank"),
    "blank id": (lambda d: d["awards"][0].update(id="  "), "id is blank"),
    "invented growth field": (lambda d: d["awards"][0].update(growth_pct=12.5), "unknown field(s) growth_pct"),
    "invented top-level field": (lambda d: d.update(projected_growth="+40%"), "projected_growth"),
    "missing awards key": (lambda d: d.pop("window"), "missing top-level key(s): window"),
    "negative amount": (lambda d: d["awards"][0].update(amount=-5.0), "is not positive"),
    "zero amount": (lambda d: d["awards"][0].update(amount=0), "is not positive"),
    "string amount": (lambda d: d["awards"][0].update(amount="1,000,000"), "is not a number"),
    "bool amount": (lambda d: d["awards"][0].update(amount=True), "is not a number"),
    "nan amount": (lambda d: d["awards"][0].update(amount=math.nan), "is not a number"),
    "null amount": (lambda d: d["awards"][0].update(amount=None), "is not a number"),
    "insane amount": (lambda d: d["awards"][0].update(amount=7.5e12), "exceeds the sanity cap"),
    "below min amount": (lambda d: d["awards"][0].update(amount=1000.0), "below this run's min_amount"),
    "impossible date": (lambda d: d["awards"][0].update(date="2026-02-30"), "not a valid YYYY-MM-DD"),
    "us date format": (lambda d: d["awards"][0].update(date="08/01/2026"), "not a valid YYYY-MM-DD"),
    "blank date": (lambda d: d["awards"][0].update(date=""), "not a valid YYYY-MM-DD"),
    "date after window": (lambda d: d["awards"][0].update(date="2026-10-08"), "after the window end"),
    "future date": (lambda d: d["awards"][0].update(date="2027-01-01"), "is in the future"),
    "duplicate id": (lambda d: d["awards"][1].update(id="A0"), "duplicate award id A0"),
    "count mismatch": (lambda d: d.update(count=99), "count field says 99"),
    "bad window": (lambda d: d["window"].update(start="2026-13-01"), "window start/end are not valid"),
    "inverted window": (lambda d: d["window"].update(start="2026-11-01"), "is after window end"),
    "future window": (lambda d: d["window"].update(end="2027-01-01"), "window end 2027-01-01 is in the future"),
    "non-usaspending link": (lambda d: d["awards"][0].update(source_url="https://example.com/x"), "not a USAspending award link"),
    "unknown sector": (lambda d: d["awards"][0].update(sector="fusion"), "is not a configured lane"),
    "public without ticker": (lambda d: d["awards"][0].update(public=True), "public must mean exactly"),
    "ticker without public": (lambda d: d["awards"][0].update(ticker="LEU"), "public must mean exactly"),
    "public not bool": (lambda d: d["awards"][0].update(public="yes"), "public must be true/false"),
    "padded ticker": (lambda d: d["awards"][0].update(ticker="NUKE", public=True), "not one of the human-verified tickers"),
    "malformed ticker": (lambda d: d["awards"][0].update(ticker="leu!", public=True), "not a valid symbol"),
    "score out of range": (lambda d: d["awards"][0].update(score=140), "not a number in 0-100"),
    "score below threshold": (lambda d: d["awards"][0].update(score=20), "below the run's threshold 45"),
    "description too long": (lambda d: d["awards"][0].update(description="x" * 201), "max 200"),
    "recipient not string": (lambda d: d["awards"][0].update(recipient_name=None), "recipient_name must be a string"),
    "row not object": (lambda d: d["awards"].append("oops") or d.update(count=4), "not a JSON object"),
}


@pytest.mark.parametrize("name", sorted(ERROR_CASES))
def test_gate_rejects(name):
    fn, needle = ERROR_CASES[name]
    res = check(_mut(fn), verified_tickers={"LEU"})
    assert not res.ok
    assert any(needle in e for e in res.errors), (name, res.errors)
    assert "FAILED" in res.render_md()


def test_awards_not_a_list_and_doc_not_object():
    assert not check(make_doc([], awards={"a": 1})).ok
    assert check([1, 2]).errors == ["awards file is not a JSON object"]


def test_verified_ticker_passes():
    d = _mut(lambda d: d["awards"][0].update(ticker="LEU", public=True))
    assert check(d, verified_tickers={"LEU"}).ok


def test_ticker_check_skipped_when_no_verified_set():
    d = _mut(lambda d: d["awards"][0].update(ticker="LEU", public=True))
    assert check(d, verified_tickers=None).ok


# --- missing data is flagged, not filled in ----------------------------------------------------------------

@pytest.mark.parametrize("field", ["recipient_name", "agency", "description"])
def test_blank_text_is_a_warning_not_an_error(field):
    res = check(_mut(lambda d: d["awards"][0].update({field: ""})))
    assert res.ok and any(f"{field} is blank" in w for w in res.warnings)


def test_date_before_window_start_is_flagged_only():
    res = check(_mut(lambda d: d["awards"][0].update(date="2026-07-01")))
    assert res.ok and any("before the window start" in w for w in res.warnings)


def test_score_is_optional_and_old_files_without_pipeline_block_pass():
    d = good_doc()
    del d["pipeline"]
    for r in d["awards"]:
        del r["score"]
    d["awards"][0]["amount"] = 125_505.0  # older hand pulls used a lower floor; no min_amount recorded -> not checked
    assert check(d).ok


def test_gate_never_mutates_input():
    d = good_doc()
    before = copy.deepcopy(d)
    check(d, previous=good_doc(1))
    assert d == before


# --- row-count change vs the previous snapshot -----------------------------------------------------------------

def _rows(n, lane_cycle=LANES):
    return make_doc([make_row(id=f"P{i}", sector=lane_cycle[i % len(lane_cycle)]) for i in range(n)])


@pytest.mark.parametrize("prev,new,ok", [
    (46, 75, True),     # the real first pipeline run: +63% is inside the 100% rise limit
    (46, 46, True),
    (100, 51, True),    # 49% drop
    (100, 49, False),   # 51% drop
    (40, 81, False),    # 103% rise
    (5, 15, True),      # +200% but only 10 rows: inside the slack
    (12, 0, False),     # everything vanished
    (0, 30, True),      # recovering from an empty snapshot is not suspicious
])
def test_row_count_limits(prev, new, ok):
    res = check(_rows(new), previous=_rows(prev))
    assert res.ok is ok, res.errors
    assert res.stats["previous_count"] == prev and res.stats["count_change"] == new - prev


def test_vanished_lane_fails_even_when_total_is_fine():
    prev = _rows(30)                                  # 10 per lane
    new = _rows(30, lane_cycle=["nuclear", "magnets"])  # chips went to zero
    res = check(new, previous=prev)
    assert not res.ok and any("lane chips had 10 rows" in e for e in res.errors)


def test_allow_count_change_downgrades_only_count_problems():
    res = check(_rows(10), previous=_rows(100), allow_count_change=True)
    assert res.ok and any("allowed by --allow-count-change" in w for w in res.warnings)
    bad = _rows(10)
    bad["awards"][0]["amount"] = -1
    assert not check(bad, previous=_rows(100), allow_count_change=True).ok


def test_custom_quality_limits_from_lanes_json():
    res = check(_rows(80), previous=_rows(100), quality={"max_count_drop_pct": 10, "count_change_slack": 0, "_doc": "x"})
    assert not res.ok


def test_previous_without_awards_list_warns():
    res = check(good_doc(), previous={"nope": 1})
    assert res.ok and any("row-count check skipped" in w for w in res.warnings)


# --- cross-file consistency -----------------------------------------------------------------------------------

def test_meta_and_js_must_agree():
    d = good_doc()
    assert check(d, meta={"primes_count": 3, "primes_window": {"start": "2026-07-09", "end": "2026-10-07"}}, js_doc=d).ok
    assert any("primes_count=4" in e for e in check(d, meta={"primes_count": 4}).errors)
    assert any("primes_window" in e for e in check(d, meta={"primes_window": {"start": "x", "end": "y"}}).errors)
    other = copy.deepcopy(d)
    other["awards"][0]["amount"] = 2.0
    assert any("js/awards-data.js" in e for e in check(d, js_doc=other).errors)


# --- CLI ---------------------------------------------------------------------------------------------------------

def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj))
    return str(p)


def test_cli_pass_fail_and_unreadable(tmp_path, capsys, monkeypatch):
    good = _write(tmp_path, "good.json", good_doc())
    report = tmp_path / "summary.md"
    assert va.main([good, "--previous", good, "--report-md", str(report)]) == 0
    assert "PASSED" in report.read_text()

    bad = _write(tmp_path, "bad.json", _mut(lambda d: d["awards"][0].update(amount=-1)))
    assert va.main([bad, "--previous", good, "--report-md", str(report)]) == 1
    assert "FAILED" in report.read_text()  # appended, not overwritten
    assert "data-quality gate FAILED" in capsys.readouterr().err

    assert va.main([str(tmp_path / "missing.json")]) == 2
    (tmp_path / "broken.json").write_text("{not json")
    assert va.main([str(tmp_path / "broken.json")]) == 2


def test_cli_count_override(tmp_path):
    prev = _write(tmp_path, "prev.json", _rows(100))
    new = _write(tmp_path, "new.json", _rows(10))
    assert va.main([new, "--previous", prev]) == 1
    assert va.main([new, "--previous", prev, "--allow-count-change"]) == 0


def test_cli_checks_js_and_meta(tmp_path):
    d = good_doc()
    good = _write(tmp_path, "a.json", d)
    js = tmp_path / "a.js"
    js.write_text("window.FEDFORGE_AWARDS=" + json.dumps(d, separators=(",", ":")) + ";\n")
    meta = _write(tmp_path, "meta.json", {"primes_count": 3})
    assert va.main([good, "--previous", good, "--js", str(js), "--meta", meta]) == 0
    js.write_text("var x = 1;")
    assert va.main([good, "--js", str(js)]) == 2


def test_cli_without_previous_warns_but_passes(tmp_path, capsys):
    good = _write(tmp_path, "a.json", good_doc())
    assert va.main([good]) == 0
    assert "row-count and verified-ticker checks skipped" in capsys.readouterr().out


def test_github_annotations(monkeypatch, capsys):
    res = check(_mut(lambda d: d["awards"][0].update(amount=-1)))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    res.annotate()
    assert capsys.readouterr().out == ""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    res.annotate()
    assert "::error title=Data-quality gate::" in capsys.readouterr().out
