#!/usr/bin/env python3
"""Validate data/private-capital.json, the Private capital section (stdlib only).

    python3 tools/check_private_capital.py            # exit 1 on any problem
    python3 tools/check_private_capital.py FILE.json  # check another file (used by the tests)

Every rule here exists so a number, date or ticker on the page can be traced to a source:
- each entry has the required fields, a unique id, and at least one https source
- dates are real YYYY-MM-DD dates inside the review window and not after the review date
- an amount (amount_usd) is only allowed with an https amount_source_url that is also listed in sources;
  with no amount, the display text must say it is undisclosed / not stated
- no percentages in amount text (no growth rates or projections)
- every *_source_url (status, federal link, ticker, listing, public partners) is one of the entry's sources
- tickers only for public companies, each with a ticker_source_url; private companies carry none
- status, category, lane and beneficiaries come from fixed lists
"""
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "data", "private-capital.json")

REQUIRED = ("id", "company", "ownership", "project", "what", "location", "category", "lane", "date",
            "amount_display", "beneficiaries", "beneficiary_detail", "sources")
OWNERSHIP = {"private", "public", "subsidiary", "joint-venture"}
STATUS = {"announced", "under construction", "operating"}
LANES = {"nuclear", "magnets", "chips", "other"}  # the site's existing sector keys
DATE_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TICKER_RX = re.compile(r"^[A-Z][A-Z.]{0,5}$")
UNDISCLOSED_RX = re.compile(r"\b(undisclosed|not stated|not disclosed)\b", re.I)


def parse_date(s):
    if not isinstance(s, str) or not DATE_RX.match(s):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def is_https(u):
    return isinstance(u, str) and u.startswith("https://") and len(u) > len("https://x.y")


def validate(data):
    """Return a list of problems (empty list = valid)."""
    errs = []
    if not isinstance(data, dict):
        return ["top level must be an object"]
    reviewed = parse_date(data.get("reviewed"))
    if reviewed is None:
        errs.append(f"reviewed: malformed date {data.get('reviewed')!r} (want YYYY-MM-DD)")
    window = data.get("window") or {}
    w_start, w_end = parse_date(window.get("start")), parse_date(window.get("end"))
    if w_start is None or w_end is None:
        errs.append("window: start/end must be YYYY-MM-DD dates")
    categories = data.get("categories") or {}
    beneficiaries = data.get("beneficiaries") or {}
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        return errs + ["entries: must be a non-empty list"]

    seen = set()
    for i, e in enumerate(entries):
        tag = f"entries[{i}] {e.get('id', '?') if isinstance(e, dict) else '?'}"
        if not isinstance(e, dict):
            errs.append(f"{tag}: not an object")
            continue
        for k in REQUIRED:
            v = e.get(k)
            if v is None or v == "" or v == []:
                errs.append(f"{tag}: missing {k}")
        if e.get("id") in seen:
            errs.append(f"{tag}: duplicate id")
        seen.add(e.get("id"))

        # sources
        sources = e.get("sources") or []
        urls = set()
        for j, s in enumerate(sources):
            u = (s or {}).get("url")
            if not is_https(u):
                errs.append(f"{tag}: sources[{j}] has no https url")
            elif not (s or {}).get("label"):
                errs.append(f"{tag}: sources[{j}] has no label")
            else:
                urls.add(u)
        if not urls:
            errs.append(f"{tag}: no source URL")

        def traced(field, url):
            if not is_https(url):
                errs.append(f"{tag}: {field} must be an https URL")
            elif url not in urls:
                errs.append(f"{tag}: {field} is not one of the entry's sources")

        # date
        d = parse_date(e.get("date"))
        if d is None:
            errs.append(f"{tag}: malformed date {e.get('date')!r} (want YYYY-MM-DD)")
        else:
            if reviewed and d > reviewed:
                errs.append(f"{tag}: date {d} is after the review date {reviewed}")
            if w_start and w_end and not (w_start <= d <= w_end):
                errs.append(f"{tag}: date {d} is outside the window {w_start}..{w_end}")

        # amount
        amt = e.get("amount_usd")
        disp = str(e.get("amount_display") or "")
        if "%" in disp:
            errs.append(f"{tag}: amount_display contains a percentage")
        if amt is not None:
            if isinstance(amt, bool) or not isinstance(amt, (int, float)) or amt <= 0:
                errs.append(f"{tag}: amount_usd must be a positive number or null")
            if not e.get("amount_source_url"):
                errs.append(f"{tag}: amount without amount_source_url")
            else:
                traced("amount_source_url", e.get("amount_source_url"))
        else:
            if e.get("amount_source_url"):
                traced("amount_source_url", e.get("amount_source_url"))
            if not UNDISCLOSED_RX.search(disp):
                errs.append(f"{tag}: no amount_usd, so amount_display must say undisclosed / not stated")

        # status
        st = e.get("status")
        if st is not None:
            if st not in STATUS:
                errs.append(f"{tag}: status {st!r} not in {sorted(STATUS)}")
            traced("status_source_url", e.get("status_source_url"))

        # federal link
        fl = e.get("federal_link")
        if fl is not None:
            if not isinstance(fl, dict) or not fl.get("text"):
                errs.append(f"{tag}: federal_link needs text")
            else:
                traced("federal_link.source_url", fl.get("source_url"))

        # ownership / tickers
        own = e.get("ownership")
        if own not in OWNERSHIP:
            errs.append(f"{tag}: ownership {own!r} not in {sorted(OWNERSHIP)}")
        tk = e.get("ticker")
        if tk is not None:
            if own != "public":
                errs.append(f"{tag}: ticker {tk!r} on a company that is not public ({own})")
            if not isinstance(tk, str) or not TICKER_RX.match(tk):
                errs.append(f"{tag}: malformed ticker {tk!r}")
            traced("ticker_source_url", e.get("ticker_source_url"))
        elif own == "public":
            errs.append(f"{tag}: public company without a ticker")
        if e.get("listing_source_url"):
            traced("listing_source_url", e.get("listing_source_url"))
        for k, p in enumerate(e.get("public_partners") or []):
            if not p.get("name") or not isinstance(p.get("ticker"), str) or not TICKER_RX.match(p.get("ticker", "")):
                errs.append(f"{tag}: public_partners[{k}] needs a name and a ticker")
            traced(f"public_partners[{k}].source_url", p.get("source_url"))

        # fixed vocabularies
        if e.get("category") not in categories:
            errs.append(f"{tag}: category {e.get('category')!r} not in categories")
        if e.get("lane") not in LANES:
            errs.append(f"{tag}: lane {e.get('lane')!r} not in {sorted(LANES)}")
        for b in e.get("beneficiaries") or []:
            if b not in beneficiaries:
                errs.append(f"{tag}: beneficiary {b!r} not in beneficiaries")
    return errs


def main(argv):
    path = argv[1] if len(argv) > 1 else DEFAULT
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    errs = validate(data)
    n = len(data.get("entries") or []) if isinstance(data, dict) else 0
    if errs:
        print(f"{os.path.basename(path)}: {len(errs)} problem(s) in {n} entries")
        for e in errs:
            print("  -", e)
        return 1
    print(f"{os.path.basename(path)}: {n} entries OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
