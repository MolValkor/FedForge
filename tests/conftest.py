"""Shared fixtures. Tests run offline: any socket connection attempt fails the test."""
import json
import os
import socket
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO, "tests", "fixtures")
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "tools", "pipeline"))

import fetch_awards  # noqa: E402


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def guard(*a, **k):
        raise RuntimeError("tests must not use the network; mock fetch_awards.http_json instead")
    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "create_connection", guard)
    monkeypatch.setattr(fetch_awards.time, "sleep", lambda s: None)


def load_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def lanes_cfg():
    with open(fetch_awards.LANES_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def lanes(lanes_cfg):
    return fetch_awards.compile_lanes(lanes_cfg)


@pytest.fixture
def scoring(lanes_cfg):
    return lanes_cfg["scoring"]


def make_award(**kw):
    """A normalized award (the shape normalize_usa returns) with sensible defaults."""
    a = {"key": "ASST_NON_X1_089", "id": "X1", "date": "2026-08-01", "agency": "Department of Energy",
         "sub_agency": "Department of Energy", "recipient_name": "EXAMPLE UNIVERSITY", "amount": 1_000_000.0,
         "description_full": "ADVANCED REACTOR FUEL QUALIFICATION", "source_url": "https://www.usaspending.gov/award/ASST_NON_X1_089",
         "naics": "", "psc": "", "award_type": "", "origin": "usaspending"}
    a.update(kw)
    return a


def make_row(**kw):
    """A published site row (the shape data/awards.json holds)."""
    r = {"id": "X1", "date": "2026-08-01", "agency": "Department of Energy", "recipient_name": "EXAMPLE UNIVERSITY",
         "amount": 1_000_000.0, "description": "ADVANCED REACTOR FUEL QUALIFICATION",
         "source_url": "https://www.usaspending.gov/award/ASST_NON_X1_089", "sector": "nuclear", "public": False, "score": 60}
    r.update(kw)
    return r


def make_doc(rows, start="2026-07-09", end="2026-10-07", **kw):
    d = {"generated_at": end, "source": fetch_awards.USA_URL,
         "window": {"start": start, "end": end, "date_type": "new_awards_only", "recipient_scope": "domestic"},
         "queries": ["test"], "note": "test", "count": len(rows),
         "pipeline": {"version": 1, "score_threshold": 45, "per_lane_cap": 25, "min_amount": 250000.0,
                      "candidates": len(rows), "sam_gov": "skipped"},
         "awards": rows}
    d.update(kw)
    return d
