"""Unit tests for tools/fetch_awards.py: parsing, lane matching, dedup, selection and output shape.
All API traffic is replayed from tests/fixtures (recorded USAspending responses)."""
import json

import pytest

import fetch_awards as fa
import validate_awards as va
from conftest import load_fixture, make_award

END = "2026-10-07"


# ---------------------------------------------------------------- parsing

def test_normalize_usa_contract_row_from_recording():
    row = load_fixture("usaspending_contracts_page1.json")["results"][1]  # UNITED SEMICONDUCTORS, LLC
    a = fa.normalize_usa(row)
    assert a == {
        "key": "CONT_AWD_80JSC026C0007_8000_-NONE-_-NONE-",
        "id": "80JSC026C0007",
        "date": "2026-07-29",  # Base Obligation Date wins over Start Date (2026-07-30)
        "agency": "National Aeronautics and Space Administration",
        "sub_agency": "National Aeronautics and Space Administration",
        "recipient_name": "UNITED SEMICONDUCTORS, LLC",
        "amount": 3760000.0,
        "description_full": "UNITED SEMICONDUCTOR INSPA PHASE 2",
        "source_url": "https://www.usaspending.gov/award/CONT_AWD_80JSC026C0007_8000_-NONE-_-NONE-",
        "naics": "541715",
        "psc": row["PSC"]["code"],
        "award_type": row["Contract Award Type"],
        "origin": "usaspending",
    }


def test_normalize_usa_grant_row_strips_and_has_no_naics():
    row = load_fixture("usaspending_grants_page1.json")["results"][1]  # DEFE0032588, multi-line description
    a = fa.normalize_usa(row)
    assert a["id"] == "DEFE0032588"
    assert a["naics"] == "" and a["psc"] == ""
    assert a["description_full"] == row["Description"].strip()
    assert a["source_url"].startswith("https://www.usaspending.gov/award/ASST_")
    assert len(a["date"]) == 10


def test_normalize_usa_falls_back_and_leaves_missing_blank():
    a = fa.normalize_usa({"Award ID": " ABC123 ", "Start Date": "2026-08-05T00:00:00", "Award Amount": None})
    assert a["id"] == "ABC123"
    assert a["date"] == "2026-08-05"          # Start Date used when there is no Base Obligation Date
    assert a["amount"] is None                # missing amount is never invented
    assert a["key"] == "USA:ABC123"
    assert a["source_url"] == ""              # no generated id -> no link (row is rejected later)
    assert a["recipient_name"] == "" and a["agency"] == ""


def test_normalize_usa_url_quotes_internal_id():
    a = fa.normalize_usa({"Award ID": "X", "generated_internal_id": "CONT_AWD_A B/1", "Award Amount": 5})
    assert a["source_url"] == "https://www.usaspending.gov/award/CONT_AWD_A%20B/1"
    assert a["amount"] == 5.0 and isinstance(a["amount"], float)


@pytest.mark.parametrize("value,expected", [
    ({"code": " 334413 ", "description": "x"}, "334413"), ({"code": None}, ""), ("221113", "221113"), (None, ""), (12, ""),
])
def test_code_of(value, expected):
    assert fa.code_of(value) == expected


@pytest.mark.parametrize("value,expected", [
    ("2026-08-03", "2026-08-03"), ("08/03/2026", "2026-08-03"), ("2026-08-03T10:00:00Z", "2026-08-03"), ("", ""), ("soon", ""),
])
def test_sam_date(value, expected):
    assert fa.sam_date(value) == expected


# ---------------------------------------------------------------- HTTP paging (mocked)

def test_usa_query_follows_pages_until_has_next_false(monkeypatch):
    pages = {1: load_fixture("usaspending_contracts_page1.json"), 2: load_fixture("usaspending_contracts_page2.json")}
    bodies = []

    def fake(url, payload=None, **k):
        bodies.append(payload)
        return pages[payload["page"]]
    monkeypatch.setattr(fa, "http_json", fake)
    stats = {"requests": 0, "truncated": []}
    rows = fa.usa_query({"f": 1}, fa.CONTRACT_FIELDS, 10, stats, "lbl")
    assert len(rows) == 6 + 5
    assert [b["page"] for b in bodies] == [1, 2]
    assert all(b["subawards"] is False and b["limit"] == 100 for b in bodies)
    assert stats == {"requests": 2, "truncated": []}


def test_usa_query_marks_truncated_at_page_cap(monkeypatch):
    page = load_fixture("usaspending_contracts_page1.json")  # hasNext: true, forever
    monkeypatch.setattr(fa, "http_json", lambda url, payload=None, **k: page)
    stats = {"requests": 0, "truncated": []}
    rows = fa.usa_query({}, fa.CONTRACT_FIELDS, 3, stats, "nuclear: keywords x contracts")
    assert len(rows) == 18 and stats["requests"] == 3
    assert stats["truncated"] == ["nuclear: keywords x contracts"]


def test_usa_query_stops_on_empty_results(monkeypatch):
    monkeypatch.setattr(fa, "http_json", lambda url, payload=None, **k: {"results": [], "page_metadata": {"hasNext": True}})
    stats = {"requests": 0, "truncated": []}
    assert fa.usa_query({}, [], 5, stats, "x") == [] and stats["requests"] == 1


def test_fetch_usaspending_builds_three_queries_per_lane(monkeypatch, lanes):
    seen = []

    def fake(url, payload=None, **k):
        seen.append(payload)
        return {"results": [], "page_metadata": {"hasNext": False}}
    monkeypatch.setattr(fa, "http_json", fake)
    stats = {"requests": 0, "per_query": {}, "truncated": []}
    fa.fetch_usaspending(lanes, "2026-07-09", END, 250000, 2, stats)
    assert len(seen) == 3 * len(lanes)
    first = seen[0]["filters"]
    assert first["time_period"] == [{"start_date": "2026-07-09", "end_date": END, "date_type": "new_awards_only"}]
    assert first["recipient_scope"] == "domestic" and first["award_amounts"] == [{"lower_bound": 250000}]
    kinds = [(tuple(p["filters"]["award_type_codes"]), "naics_codes" in p["filters"]) for p in seen[:3]]
    assert kinds == [(tuple(fa.CONTRACTS), False), (tuple(fa.GRANTS), False), (tuple(fa.CONTRACTS), True)]
    assert seen[1]["fields"] == fa.GRANT_FIELDS and seen[0]["fields"] == fa.CONTRACT_FIELDS
    assert set(stats["per_query"]) == {f"{k}: {q}" for k in lanes for q in ("keywords x contracts", "keywords x grants", "NAICS x contracts")}


def test_fetch_sam_parses_and_filters(monkeypatch, lanes):
    rec = {"contractId": {"piid": "W911NF26C0001", "subtier": {"code": "2100"}},
           "awardDetails": {"totalContractDollars": {"totalActionObligation": "1200000.50"},
                            "dates": {"dateSigned": "08/14/2026"},
                            "awardeeData": {"awardeeHeader": {"awardeeName": " ACME MAGNETICS INC "}},
                            "productOrServiceInformation": {"descriptionOfContractRequirement": "RARE EARTH PERMANENT MAGNET PILOT LINE"}},
           "coreData": {"productOrServiceInformation": {"principalNaics": [{"code": "331410"}], "productOrService": {"code": "AC12"}},
                        "federalOrganization": {"contractingInformation": {"contractingDepartment": {"name": "Department of Defense"},
                                                                           "contractingSubtier": {"name": "Department of the Army"}}},
                        "awardOrIDVType": {"name": "Definitive Contract"}}}
    small = json.loads(json.dumps(rec))
    small["contractId"]["piid"] = "SMALL1"
    small["awardDetails"]["totalContractDollars"]["totalActionObligation"] = "1000"
    urls = []

    def fake(url, payload=None, **k):
        urls.append(url)
        return {"awardSummary": [rec, small]}
    monkeypatch.setattr(fa, "http_json", fake)
    stats = {"per_query": {}, "sam_requests": 0, "sam_errors": []}
    out = fa.fetch_sam(lanes, "2026-07-09", END, 250000, "KEY", 1, stats)
    assert stats["sam_requests"] == 1 and len(urls) == 1          # request budget respected
    assert "dateSigned=[07/09/2026,10/07/2026]" in urls[0]
    assert [a["id"] for a in out] == ["W911NF26C0001"]              # under min amount dropped
    a = out[0]
    assert a["key"] == "CONT_AWD_W911NF26C0001_2100_-NONE-_-NONE-"
    assert a["date"] == "2026-08-14" and a["amount"] == 1200000.5 and a["naics"] == "331410"
    assert a["recipient_name"] == "ACME MAGNETICS INC" and a["origin"] == "sam.gov"
    assert a["amount_display_suffix"] == "obligated (SAM.gov)"


def test_fetch_sam_errors_are_soft_and_redact_key(monkeypatch, lanes):
    def boom(url, payload=None, **k):
        raise RuntimeError(f"HTTP 403: bad key SECRETKEY in {url}")
    monkeypatch.setattr(fa, "http_json", boom)
    stats = {"per_query": {}, "sam_requests": 0, "sam_errors": []}
    assert fa.fetch_sam(lanes, "2026-07-09", END, 250000, "SECRETKEY", 3, stats) == []
    assert stats["sam_errors"] and all("SECRETKEY" not in e for e in stats["sam_errors"])
    assert "check the SAM_API_KEY secret" in stats["sam_errors"][0]


# ---------------------------------------------------------------- lane matching

def _best(lanes, scoring, **kw):
    return fa.classify(make_award(**kw), lanes, scoring)


def test_recorded_semiconductor_grant_goes_to_chips(lanes, scoring):
    row = load_fixture("usaspending_grants_page1.json")["results"][4]  # NSF FAST ENGINE ... SEMICONDUCTORS
    s, lane, why = fa.classify(fa.normalize_usa(row), lanes, scoring)
    assert lane == "chips" and s >= scoring["threshold"]
    assert any(w.startswith("terms:") and "SEMICONDUCTOR" in w for w in why)


def test_recorded_rare_earth_grant_goes_to_magnets(lanes, scoring):
    row = load_fixture("usaspending_grants_page1.json")["results"][1]  # CARBON ORE, RARE EARTH ... CRITICAL MINERAL
    s, lane, why = fa.classify(fa.normalize_usa(row), lanes, scoring)
    assert lane == "magnets" and s >= scoring["core_score"] and "lead" in why


def test_recorded_nuclear_research_grants_are_passing_mentions(lanes, scoring):
    # "...CONSOLIDATED INNOVATIVE NUCLEAR RESEARCH AWARD": only the weak term NUCLEAR, plus DOE agency and amount.
    # The lane is right but the score stays under the threshold, so these are not published as nuclear primes.
    for row in load_fixture("usaspending_nuclear_grants.json")["results"]:
        s, lane, why = fa.classify(fa.normalize_usa(row), lanes, scoring)
        assert lane == "nuclear" and "agency" in why and "weak:NUCLEAR" in why
        assert not any(w.startswith("terms:") for w in why)
        assert s < scoring["threshold"]


def test_strong_nuclear_award_qualifies(lanes, scoring):
    s, lane, why = _best(lanes, scoring, description_full="HALEU TRANSPORTATION PACKAGE FOR ADVANCED REACTOR FUEL")
    assert lane == "nuclear" and s >= scoring["core_score"] and "lead" in why and "agency" in why


def test_lab_equipment_penalty_applies(lanes, scoring):
    row = load_fixture("usaspending_contracts_page1.json")["results"][0]  # CAMECA, NAICS 334516
    s, why = fa.score_lane(fa.normalize_usa(row), lanes["chips"], scoring)
    assert "lab-equipment-penalty" in why


@pytest.mark.parametrize("desc,lane", [
    ("NUCLEAR MAGNETIC RESONANCE SPECTROMETER FOR PROTEIN STUDIES", "nuclear"),
    ("MITOCHONDRIAL FISSION IN AGING NEURONS", "nuclear"),
    ("NUCLEAR MEDICINE IMAGING SUITE", "nuclear"),
    ("WOOD CHIPS FOR TRAIL MAINTENANCE", "chips"),
    ("MRI MAGNETIC RESONANCE SCANNER SERVICE", "magnets"),
])
def test_masks_block_look_alikes(lanes, scoring, desc, lane):
    s, why = fa.score_lane(make_award(description_full=desc, naics="", agency="Other"), lanes[lane], scoring)
    assert s == 0, (desc, why)


def test_naics_agency_amount_alone_never_qualify(lanes, scoring):
    a = make_award(description_full="JANITORIAL SERVICES FOR BUILDING 7", naics="221113",
                   agency="Department of Energy", amount=500_000_000.0)
    assert fa.score_lane(a, lanes["nuclear"], scoring)[0] == 0
    assert _best(lanes, scoring, description_full="JANITORIAL SERVICES", naics="221113")[1] is None


def test_lead_bonus_only_when_term_in_lead(lanes, scoring):
    lead = make_award(description_full="HALEU DECONVERSION PILOT")
    late = make_award(description_full="X" * 200 + " HALEU DECONVERSION PILOT")
    s1, w1 = fa.score_lane(lead, lanes["nuclear"], scoring)
    s2, w2 = fa.score_lane(late, lanes["nuclear"], scoring)
    assert "lead" in w1 and "lead" not in w2 and s1 - s2 == scoring["lead_bonus"]


def test_score_is_clamped_to_100(lanes, scoring):
    a = make_award(description_full="SMALL MODULAR REACTOR HALEU NUCLEAR FUEL TRISO URANIUM ENRICHMENT NUCLEAR",
                   naics="221113", amount=2e9)
    s, _ = fa.score_lane(a, lanes["nuclear"], scoring)
    assert 0 <= s <= 100


def test_classify_picks_best_lane(lanes, scoring):
    s, lane, _ = _best(lanes, scoring, description_full="NDFEB PERMANENT MAGNET MANUFACTURING FROM RARE EARTH OXIDE",
                       agency="Department of Defense")
    assert lane == "magnets"


# ---------------------------------------------------------------- dedup + selection

def test_dedupe_on_generated_internal_id_first_wins():
    a1 = make_award(key="K1", id="A", recipient_name="FIRST")
    a2 = make_award(key="K1", id="A", recipient_name="SECOND")
    a3 = make_award(key="K2", id="B")
    out = fa.dedupe([a1, a2, a3])
    assert [x["recipient_name"] for x in out[:1]] == ["FIRST"] and [x["key"] for x in out] == ["K1", "K2"]


def test_dedupe_drops_sam_copy_of_usaspending_contract():
    usa = make_award(key="CONT_AWD_P1_2100_-NONE-_-NONE-", id="P1")
    sam_same_key = make_award(key="CONT_AWD_P1_2100_-NONE-_-NONE-", id="P1", origin="sam.gov")
    sam_same_piid = make_award(key="SAM:P1", id="P1", origin="sam.gov")
    sam_new = make_award(key="SAM:P2", id="P2", origin="sam.gov")
    out = fa.dedupe([usa, sam_same_key, sam_same_piid, sam_new])
    assert [(x["id"], x["origin"]) for x in out] == [("P1", "usaspending"), ("P2", "sam.gov")]


def test_dedupe_keeps_distinct_usaspending_awards_sharing_display_id():
    # two different awards (different internal ids) can share an Award ID; dedupe keeps both, select collapses
    out = fa.dedupe([make_award(key="K1", id="A"), make_award(key="K2", id="A")])
    assert len(out) == 2


def test_recorded_overlapping_queries_dedupe(lanes):
    c = load_fixture("usaspending_contracts_page1.json")["results"]
    raw = [fa.normalize_usa(r) for r in c + c + c]  # same rows found by three lane queries
    assert len(fa.dedupe(raw)) == len(c)


def test_select_rejects_incomplete_and_irrelevant(lanes, scoring):
    rows = [make_award(key="1", id="NOAMT", amount=None), make_award(key="2", id="NOURL", source_url=""),
            make_award(key="3", id="NODATE", date=""), make_award(key="4", id="OFFTOPIC", description_full="JANITORIAL"),
            make_award(key="5", id="GOOD")]
    out, rejected, fate, stats = fa.select_awards(rows, lanes, scoring, 25)
    assert [a["id"] for a in out] == ["GOOD"] and rejected == 4
    assert fate["NOAMT"] == fate["NOURL"] == fate["NODATE"] == "returned without id/date/amount/source"
    assert fate["OFFTOPIC"].startswith("below relevance threshold")
    assert stats["nuclear"]["kept"] == 1 and stats["chips"]["kept"] == 0


def test_select_caps_lane_core_first_then_amount(lanes, scoring):
    rows = [
        make_award(key="c1", id="CORE_SMALL", amount=300_000.0, description_full="ADVANCED REACTOR HALEU FUEL"),
        make_award(key="c2", id="CORE_BIG", amount=9_000_000.0, description_full="SMALL MODULAR REACTOR LICENSING"),
        make_award(key="p1", id="PASSING_HUGE", amount=900_000_000.0, agency="Other",
                   description_full="UNIVERSITY STUDY OF MANY TOPICS " + "Y" * 160 + " NUCLEAR ENERGY"),
    ]
    out, _, fate, stats = fa.select_awards(rows, lanes, scoring, 2)
    ids = {a["id"] for a in out}
    assert ids == {"CORE_BIG", "CORE_SMALL"}
    assert "below the top 2 by amount in nuclear" in fate["PASSING_HUGE"]
    assert stats["nuclear"] == {"label": "Nuclear / SMRs", "qualified": 3, "kept": 2, "amount_kept": 9_300_000.0}


def test_select_sorts_newest_first_and_collapses_duplicate_ids(lanes, scoring):
    rows = [make_award(key="k1", id="SAME", date="2026-08-01", description_full="NUCLEAR TRAINING"),  # weak only
            make_award(key="k2", id="SAME", date="2026-08-02", description_full="ADVANCED REACTOR HALEU FUEL"),
            make_award(key="k3", id="NEW", date="2026-09-30", description_full="SMALL MODULAR REACTOR")]
    out, *_ = fa.select_awards(rows, lanes, scoring, 25)
    assert [a["id"] for a in out] == ["NEW", "SAME"]
    assert [a["key"] for a in out if a["id"] == "SAME"] == ["k2"]  # the higher-scoring copy survives


# ---------------------------------------------------------------- tickers + output shape

def _tmp_root(tmp_path, awards=None, curated=None):
    (tmp_path / "data").mkdir()
    (tmp_path / "js").mkdir()
    if awards is not None:
        (tmp_path / "data" / "awards.json").write_text(json.dumps(awards))
    if curated is not None:
        (tmp_path / "data" / "curated.json").write_text(json.dumps(curated))
    return tmp_path


def test_verified_tickers_exact_only(tmp_path):
    root = _tmp_root(tmp_path, curated={"awards": [
        {"id": "89243226FNE400212", "recipient_name": "American Centrifuge Operating, LLC", "ticker": "LEU"},
        {"id": "NOPE", "recipient_name": "UNLISTED CO"}]})
    by_id, by_name = fa.verified_tickers(str(root))
    assert by_id == {"89243226FNE400212": "LEU"}
    assert by_name == {"AMERICAN CENTRIFUGE OPERATING LLC": "LEU"}


def test_to_site_rows_shape_and_ticker_rules():
    base = dict(score=70, sector="nuclear", why=[])
    rows = [make_award(id="89243226FNE400212", recipient_name="SOMEONE ELSE", **base),
            make_award(id="Z2", recipient_name="american centrifuge operating, llc", **base),
            make_award(id="Z3", recipient_name="AMERICAN CENTRIFUGE HOLDINGS", **base),  # similar name: no ticker
            make_award(id="Z4", amount_display_suffix="obligated (SAM.gov)", amount=1_234_567.0, **base),
            make_award(id="Z5", description_full="W" * 450, **base)]
    out = fa.to_site_rows(rows, {"89243226FNE400212": "LEU"}, {"AMERICAN CENTRIFUGE OPERATING LLC": "LEU"})
    assert [r.get("ticker") for r in out] == ["LEU", "LEU", None, None, None]
    assert [r["public"] for r in out] == [True, True, False, False, False]
    assert list(out[2]) == ["id", "date", "agency", "recipient_name", "amount", "description", "source_url", "sector", "public", "score"]
    assert out[3]["amount_display"] == "$1.2M obligated (SAM.gov)"
    assert len(out[4]["description"]) == fa.DESC_MAX and out[4]["description"].endswith("...")


@pytest.mark.parametrize("n,s", [(None, "n/a"), (950, "$950"), (25_000, "$25K"), (3_824_575, "$3.8M"), (1.5e9, "$1.50B")])
def test_fmt_money(n, s):
    assert fa.fmt_money(n) == s


def test_short_desc_collapses_whitespace():
    assert fa.short_desc("A\n\n B   C ") == "A B C"


def test_diff_vs_old_ignores_score_only_changes():
    old = {"awards": [{"id": "A", "x": 1, "score": 50}, {"id": "GONE", "recipient_name": "R", "date": "2026-07-01"}]}
    new = [{"id": "A", "x": 1, "score": 99}, {"id": "B", "x": 2}]
    added, dropped, changed = fa.diff_vs_old(old, new, {"GONE": "below relevance threshold"}, "s", "e")
    assert [a["id"] for a in added] == ["B"] and dropped == [{"id": "GONE", "recipient_name": "R", "date": "2026-07-01", "reason": "below relevance threshold"}]
    assert changed is True
    assert fa.diff_vs_old({"awards": [{"id": "A", "score": 1}]}, [{"id": "A", "score": 2}], {}, "s", "e")[2] is False


# ---------------------------------------------------------------- end to end (main) with replayed API

def _replay(monkeypatch):
    contracts = [load_fixture("usaspending_contracts_page1.json")["results"],
                 load_fixture("usaspending_contracts_page2.json")["results"]]
    grants = load_fixture("usaspending_grants_page1.json")["results"] + load_fixture("usaspending_nuclear_grants.json")["results"]
    calls = []

    def fake(url, payload=None, **k):
        assert url == fa.USA_URL
        calls.append(payload)
        f = payload["filters"]
        if "naics_codes" in f:
            return {"results": [], "page_metadata": {"hasNext": False}}
        if f["award_type_codes"] == fa.GRANTS:
            return {"results": grants, "page_metadata": {"hasNext": False}}
        page = payload["page"]
        return {"results": contracts[page - 1], "page_metadata": {"hasNext": page == 1}}
    monkeypatch.setattr(fa, "http_json", fake)
    return calls


def _run(monkeypatch, tmp_path, *argv, previous=None):
    root = _tmp_root(tmp_path, awards=previous, curated={"awards": []})
    (root / "data" / "meta.json").write_text(json.dumps({"flagship_count": 14}))
    monkeypatch.setattr(fa, "ROOT", str(root))
    monkeypatch.delenv("SAM_API_KEY", raising=False)
    gh_out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    code = fa.main(["--end", END, "--report-json", str(tmp_path / "rep.json"), "--report-md", str(tmp_path / "rep.md"), *argv])
    return code, root, gh_out


def test_main_end_to_end_writes_valid_site_files(monkeypatch, tmp_path, capsys):
    calls = _replay(monkeypatch)
    code, root, gh_out = _run(monkeypatch, tmp_path)
    assert code == 0
    assert len(calls) == 3 * 4 - 3 + 3  # 3 lanes x (contracts p1+p2, grants, naics)
    doc = json.loads((root / "data" / "awards.json").read_text())
    assert set(doc) == {"generated_at", "source", "window", "queries", "note", "count", "pipeline", "awards"}
    assert doc["count"] == len(doc["awards"]) > 0
    assert doc["window"] == {"start": "2026-07-09", "end": END, "date_type": "new_awards_only", "recipient_scope": "domestic"}
    assert doc["pipeline"]["min_amount"] == 250000
    ids = [a["id"] for a in doc["awards"]]
    assert len(ids) == len(set(ids))
    assert {"DEFE0032588", "2532464"} <= set(ids)
    assert not any(i.startswith("DENE") for i in ids)  # weak-only nuclear mentions are scored out
    assert not any(a.get("ticker") for a in doc["awards"])  # no verified tickers in this tmp repo -> none attached
    dates = [a["date"] for a in doc["awards"]]
    assert dates == sorted(dates, reverse=True)
    js = (root / "js" / "awards-data.js").read_text()
    assert js.startswith("window.FEDFORGE_AWARDS=") and js.rstrip().endswith(";")
    assert va.load_js(str(root / "js" / "awards-data.js")) == doc
    meta = json.loads((root / "data" / "meta.json").read_text())
    assert meta["flagship_count"] == 14 and meta["primes_count"] == doc["count"]
    assert meta["primes_window"] == {"start": "2026-07-09", "end": END}
    assert va.validate(doc, meta=meta, js_doc=doc, lanes=["nuclear", "magnets", "chips"]).ok
    out = gh_out.read_text()
    assert "changed=true" in out and f"count={doc['count']}" in out
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["quality_gate"]["ok"] is True and rep["total_kept"] == doc["count"]
    assert "Data-quality gate: PASSED" in (tmp_path / "rep.md").read_text()


def test_main_dry_run_writes_nothing(monkeypatch, tmp_path):
    _replay(monkeypatch)
    code, root, _ = _run(monkeypatch, tmp_path, "--dry-run")
    assert code == 0
    assert not (root / "data" / "awards.json").exists() and not (root / "js" / "awards-data.js").exists()
    assert json.loads((root / "data" / "meta.json").read_text()) == {"flagship_count": 14}


def test_main_api_down_exits_2_and_writes_nothing(monkeypatch, tmp_path):
    def down(url, payload=None, **k):
        raise RuntimeError("HTTP 503")
    monkeypatch.setattr(fa, "http_json", down)
    code, root, gh_out = _run(monkeypatch, tmp_path)
    assert code == 2 and not (root / "data" / "awards.json").exists() and not gh_out.exists()


def _big_previous(n):
    rows = [{"id": f"OLD{i}", "date": "2026-08-01", "agency": "Department of Energy", "recipient_name": "R",
             "amount": 1e6, "description": "d", "source_url": f"https://www.usaspending.gov/award/ASST_NON_OLD{i}_089",
             "sector": "nuclear", "public": False} for i in range(n)]
    return {"generated_at": "2026-10-06", "source": fa.USA_URL, "window": {"start": "2026-07-08", "end": "2026-10-06"},
            "count": n, "awards": rows}


def test_main_gate_failure_exits_3_and_leaves_files_untouched(monkeypatch, tmp_path, capsys):
    _replay(monkeypatch)
    prev = _big_previous(200)  # today's pull is a fraction of yesterday's -> looks like a partial outage
    code, root, gh_out = _run(monkeypatch, tmp_path, previous=prev)
    assert code == 3
    assert json.loads((root / "data" / "awards.json").read_text()) == prev
    assert not (root / "js" / "awards-data.js").exists()
    assert json.loads((root / "data" / "meta.json").read_text()) == {"flagship_count": 14}
    assert not gh_out.exists()  # the workflow never sees changed=true
    err = capsys.readouterr().err
    assert "data-quality gate FAILED" in err and "row count fell 200 ->" in err
    assert "FAILED" in (tmp_path / "rep.md").read_text()


def test_main_allow_count_change_overrides_only_the_count_check(monkeypatch, tmp_path):
    _replay(monkeypatch)
    code, root, _ = _run(monkeypatch, tmp_path, "--allow-count-change", previous=_big_previous(200))
    assert code == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert any("allowed by --allow-count-change" in w for w in rep["quality_gate"]["warnings"])


def test_main_gate_blocks_bad_amount_from_api(monkeypatch, tmp_path):
    _replay(monkeypatch)
    real = fa.http_json

    def poisoned(url, payload=None, **k):
        d = json.loads(json.dumps(real(url, payload)))
        for r in d["results"]:
            if r.get("Award ID") == "DEFE0032588":
                r["Award Amount"] = 7.5e12  # a $7.5 trillion grant: unit error upstream
        return d
    monkeypatch.setattr(fa, "http_json", poisoned)
    code, root, _ = _run(monkeypatch, tmp_path)
    assert code == 3 and not (root / "data" / "awards.json").exists()
