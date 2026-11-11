#!/usr/bin/env python3
"""FedForge data-quality gate for data/awards.json (Python 3 stdlib only).

    python3 tools/pipeline/validate_awards.py data/awards.json
    python3 tools/pipeline/validate_awards.py data/awards.json --previous /tmp/previous.json \
        --meta data/meta.json --js js/awards-data.js --report-md /tmp/gate.md

tools/fetch_awards.py runs the same checks in-process BEFORE it writes anything; the nightly workflow runs this
CLI again on the written files (against main's copy as --previous) so a bad pull can never reach the data PR.

Errors (exit 1, nothing gets published):
  * schema: top-level keys/types, count == len(awards), valid window, no unknown keys anywhere (so no invented
    fields such as growth %, returns or price targets can slip in)
  * required fields per row: id, date, amount, source_url, sector, public
  * amounts: real numbers, > 0, >= the run's min_amount, <= quality.max_award_amount
  * dates: real YYYY-MM-DD dates, not after the window end, not in the future
  * no duplicate award ids
  * tickers: only ones already human-verified in the repo's data (never guessed or padded); public == has ticker
  * row-count change vs the previous snapshot within quality.max_count_drop_pct / max_count_rise_pct
    (changes of <= quality.count_change_slack rows always pass), and no lane that had rows going to zero
  * --meta / --js: data/meta.json primes_count and js/awards-data.js agree with the awards file
Warnings (reported, still published): blank recipient/agency/description (left blank, never filled in),
dates before the window start, score present but missing.

Exit codes: 0 pass, 1 gate failed, 2 a file could not be read or parsed.
"""
import argparse
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LANES_FILE = os.path.join(ROOT, "tools", "pipeline", "lanes.json")

DEFAULT_QUALITY = {
    "max_count_drop_pct": 50,
    "max_count_rise_pct": 100,
    "count_change_slack": 10,
    "lane_vanish_min_previous": 5,
    "max_award_amount": 50_000_000_000,
    "max_description_chars": 200,
}
TOP_KEYS_REQUIRED = {"generated_at", "source", "window", "count", "awards"}
TOP_KEYS_ALLOWED = TOP_KEYS_REQUIRED | {"queries", "note", "pipeline"}
ROW_KEYS_REQUIRED = {"id", "date", "agency", "recipient_name", "amount", "description", "source_url", "sector", "public"}
ROW_KEYS_ALLOWED = ROW_KEYS_REQUIRED | {"ticker", "score", "amount_display"}
SOURCE_URL_RX = re.compile(r"^https://www\.usaspending\.gov/award/[^\s/]+$")
TICKER_RX = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
JS_PREFIX = "window.FEDFORGE_AWARDS="


class GateResult:
    def __init__(self):
        self.errors, self.warnings, self.stats = [], [], {}

    @property
    def ok(self):
        return not self.errors

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def as_dict(self):
        return {"ok": self.ok, "errors": list(self.errors), "warnings": list(self.warnings), "stats": dict(self.stats)}

    def render_md(self, max_items=40):
        st = self.stats
        head = "PASSED" if self.ok else f"FAILED ({len(self.errors)} error(s)), nothing published"
        L = [f"#### Data-quality gate: {head}", ""]
        if "count" in st:
            prev = st.get("previous_count")
            L.append(f"Rows: {st['count']}" + (f" (previous snapshot {prev}, change {st['count_change']:+d})" if prev is not None else "")
                     + f". Warnings: {len(self.warnings)}.")
        for title, items in (("Errors", self.errors), ("Warnings (published, flagged for review)", self.warnings)):
            if items:
                L += ["", f"**{title}**", ""]
                L += [f"- {m}" for m in items[:max_items]]
                if len(items) > max_items:
                    L.append(f"- ... and {len(items) - max_items} more")
        return "\n".join(L) + "\n"

    def annotate(self):
        """Loud GitHub Actions annotations (no-op outside Actions)."""
        if os.environ.get("GITHUB_ACTIONS") != "true":
            return
        for m in self.errors:
            print(f"::error title=Data-quality gate::{m}")
        for m in self.warnings[:20]:
            print(f"::warning title=Data-quality gate::{m}")


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def parse_iso(v):
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def _rows_by_lane(rows):
    out = {}
    for r in rows:
        if isinstance(r, dict):
            out[r.get("sector")] = out.get(r.get("sector"), 0) + 1
    return out


def validate(doc, previous=None, lanes=None, quality=None, verified_tickers=None, allow_count_change=False,
             today=None, meta=None, js_doc=None):
    """Run every check on an awards document. Never raises on bad data; returns a GateResult.

    previous: the last published awards document (dict) or None. lanes: allowed sector keys (None = skip).
    verified_tickers: set of tickers already human-verified in the repo (None = skip that check).
    meta / js_doc: parsed data/meta.json and the object baked into js/awards-data.js, if they should be cross-checked."""
    q = dict(DEFAULT_QUALITY)
    q.update({k: v for k, v in (quality or {}).items() if not k.startswith("_")})
    today = today or datetime.now(timezone.utc).date()
    res = GateResult()

    if not isinstance(doc, dict):
        res.error("awards file is not a JSON object")
        return res
    missing = TOP_KEYS_REQUIRED - doc.keys()
    if missing:
        res.error(f"missing top-level key(s): {', '.join(sorted(missing))}")
    unknown = doc.keys() - TOP_KEYS_ALLOWED
    if unknown:
        res.error(f"unknown top-level key(s) (not in the published schema): {', '.join(sorted(unknown))}")
    rows = doc.get("awards")
    if not isinstance(rows, list):
        res.error("'awards' is not a list")
        return res
    res.stats["count"] = len(rows)
    if doc.get("count") != len(rows):
        res.error(f"count field says {doc.get('count')!r} but the file has {len(rows)} award rows")

    win = doc.get("window") if isinstance(doc.get("window"), dict) else {}
    w_start, w_end = parse_iso(win.get("start")), parse_iso(win.get("end"))
    if not w_start or not w_end:
        res.error(f"window start/end are not valid YYYY-MM-DD dates: {win.get('start')!r} .. {win.get('end')!r}")
    elif w_start > w_end:
        res.error(f"window start {w_start} is after window end {w_end}")
    if w_end and w_end > today + timedelta(days=1):
        res.error(f"window end {w_end} is in the future (today is {today})")
    if "generated_at" in doc and not parse_iso(str(doc.get("generated_at"))[:10]):
        res.error(f"generated_at is not a valid date: {doc.get('generated_at')!r}")

    pipe = doc.get("pipeline") if isinstance(doc.get("pipeline"), dict) else {}
    min_amount = pipe.get("min_amount") if is_number(pipe.get("min_amount")) else None
    threshold = pipe.get("score_threshold") if is_number(pipe.get("score_threshold")) else None
    lane_set = set(lanes) if lanes is not None else None

    seen = {}
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            res.error(f"row {i}: not a JSON object")
            continue
        rid = r.get("id")
        tag = f"row {i} ({rid})" if rid else f"row {i}"
        miss = ROW_KEYS_REQUIRED - r.keys()
        if miss:
            res.error(f"{tag}: missing field(s) {', '.join(sorted(miss))}")
        extra = r.keys() - ROW_KEYS_ALLOWED
        if extra:
            res.error(f"{tag}: unknown field(s) {', '.join(sorted(extra))} (the pipeline never adds derived numbers)")

        if not isinstance(rid, str) or not rid.strip():
            res.error(f"{tag}: id is blank")
        elif rid in seen:
            res.error(f"duplicate award id {rid} (rows {seen[rid]} and {i})")
        else:
            seen[rid] = i

        amt = r.get("amount")
        if not is_number(amt):
            res.error(f"{tag}: amount {amt!r} is not a number")
        elif amt <= 0:
            res.error(f"{tag}: amount {amt} is not positive")
        else:
            if amt > q["max_award_amount"]:
                res.error(f"{tag}: amount ${amt:,.0f} exceeds the sanity cap ${q['max_award_amount']:,.0f}")
            if min_amount is not None and amt < min_amount:
                res.error(f"{tag}: amount ${amt:,.0f} is below this run's min_amount ${min_amount:,.0f}")

        d = parse_iso(r.get("date"))
        if not d:
            res.error(f"{tag}: date {r.get('date')!r} is not a valid YYYY-MM-DD date")
        else:
            if d > today + timedelta(days=1):
                res.error(f"{tag}: date {d} is in the future")
            if w_end and d > w_end:
                res.error(f"{tag}: date {d} is after the window end {w_end}")
            if w_start and d < w_start:
                res.warn(f"{tag}: date {d} is before the window start {w_start} (USAspending base obligation date)")

        url = r.get("source_url")
        if not isinstance(url, str) or not SOURCE_URL_RX.match(url):
            res.error(f"{tag}: source_url {url!r} is not a USAspending award link")

        if lane_set is not None and r.get("sector") not in lane_set:
            res.error(f"{tag}: sector {r.get('sector')!r} is not a configured lane ({', '.join(sorted(lane_set))})")
        elif not isinstance(r.get("sector"), str) or not r.get("sector"):
            res.error(f"{tag}: sector is blank")

        for f in ("recipient_name", "agency", "description"):
            v = r.get(f)
            if f in r and not isinstance(v, str):
                res.error(f"{tag}: {f} must be a string, got {type(v).__name__}")
            elif f in r and not v.strip():
                res.warn(f"{tag}: {f} is blank in the source data (left blank, not filled in)")
        desc = r.get("description")
        if isinstance(desc, str) and len(desc) > q["max_description_chars"]:
            res.error(f"{tag}: description is {len(desc)} chars (max {q['max_description_chars']})")

        pub, tick = r.get("public"), r.get("ticker")
        if not isinstance(pub, bool):
            res.error(f"{tag}: public must be true/false, got {pub!r}")
        elif pub != bool(tick):
            res.error(f"{tag}: public={pub} but ticker={tick!r} (public must mean exactly 'has a verified ticker')")
        if tick is not None:
            if not isinstance(tick, str) or not TICKER_RX.match(tick):
                res.error(f"{tag}: ticker {tick!r} is not a valid symbol")
            elif verified_tickers is not None and tick not in verified_tickers:
                res.error(f"{tag}: ticker {tick} is not one of the human-verified tickers in the repo (never guess tickers)")

        if "score" in r:
            sc = r.get("score")
            if not is_number(sc) or not 0 <= sc <= 100:
                res.error(f"{tag}: score {sc!r} is not a number in 0-100")
            elif threshold is not None and sc < threshold:
                res.error(f"{tag}: score {sc} is below the run's threshold {threshold}")
        if "amount_display" in r and not isinstance(r.get("amount_display"), str):
            res.error(f"{tag}: amount_display must be a string")

    # row-count change vs the previous snapshot
    prev_rows = previous.get("awards") if isinstance(previous, dict) else None
    if isinstance(prev_rows, list):
        n_prev, n = len(prev_rows), len(rows)
        res.stats.update(previous_count=n_prev, count_change=n - n_prev)
        problems = []
        if abs(n - n_prev) > q["count_change_slack"]:
            if n < n_prev and n_prev and (n_prev - n) * 100.0 / n_prev > q["max_count_drop_pct"]:
                problems.append(f"row count fell {n_prev} -> {n} ({(n_prev - n) * 100.0 / n_prev:.0f}% drop, "
                                f"limit {q['max_count_drop_pct']}%)")
            # (a rise from an empty snapshot is a recovery, not a suspicious jump, so it is not checked)
            if n > n_prev and n_prev and (n - n_prev) * 100.0 / n_prev > q["max_count_rise_pct"]:
                problems.append(f"row count rose {n_prev} -> {n} ({(n - n_prev) * 100.0 / n_prev:.0f}% rise, "
                                f"limit {q['max_count_rise_pct']}%)")
        prev_lanes, new_lanes = _rows_by_lane(prev_rows), _rows_by_lane(rows)
        for lane, k in sorted((k, v) for k, v in prev_lanes.items() if isinstance(k, str)):
            if k >= q["lane_vanish_min_previous"] and new_lanes.get(lane, 0) == 0 and (lane_set is None or lane in lane_set):
                problems.append(f"lane {lane} had {k} rows in the previous snapshot and has 0 now")
        for p in problems:
            if allow_count_change:
                res.warn(p + " (allowed by --allow-count-change)")
            else:
                res.error(p + " (looks like a broken/partial pull; re-run with --allow-count-change if intended)")
    elif previous is not None:
        res.warn("previous snapshot has no 'awards' list; row-count check skipped")

    if meta is not None:
        if "primes_count" in meta and meta.get("primes_count") != len(rows):
            res.error(f"data/meta.json primes_count={meta.get('primes_count')!r} disagrees with {len(rows)} award rows")
        pw = meta.get("primes_window")
        if isinstance(pw, dict) and (pw.get("start") != win.get("start") or pw.get("end") != win.get("end")):
            res.error(f"data/meta.json primes_window {pw} disagrees with the awards window {win.get('start')}..{win.get('end')}")
    if js_doc is not None and js_doc != doc:
        res.error("js/awards-data.js does not contain the same data as data/awards.json")
    return res


# ---------------------------------------------------------------- CLI

def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_js(path):
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if not text.startswith(JS_PREFIX):
        raise ValueError(f"{path} does not start with {JS_PREFIX}")
    return json.loads(text[len(JS_PREFIX):].rstrip(";"))


def repo_verified_tickers(paths):
    out = set()
    for p in paths:
        if p and os.path.exists(p):
            for a in _load_json(p).get("awards", []):
                if a.get("ticker"):
                    out.add(a["ticker"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("awards", help="awards JSON to check (e.g. data/awards.json)")
    ap.add_argument("--previous", help="previous published snapshot for the row-count check (e.g. main's data/awards.json)")
    ap.add_argument("--meta", help="data/meta.json to cross-check primes_count / primes_window")
    ap.add_argument("--js", help="js/awards-data.js to cross-check against the JSON")
    ap.add_argument("--lanes", default=LANES_FILE, help="lanes.json (allowed sectors + 'quality' limits)")
    ap.add_argument("--allow-count-change", action="store_true", help="downgrade the row-count check to a warning")
    ap.add_argument("--report-md", help="append a Markdown summary here (e.g. $GITHUB_STEP_SUMMARY)")
    args = ap.parse_args(argv)

    try:
        doc = _load_json(args.awards)
        previous = _load_json(args.previous) if args.previous else None
        cfg = _load_json(args.lanes)
        meta = _load_json(args.meta) if args.meta else None
        js_doc = load_js(args.js) if args.js else None
    except (OSError, ValueError) as e:
        print(f"ERROR: could not read input: {e}", file=sys.stderr)
        return 2
    data_dir = os.path.join(ROOT, "data")
    tickers = None
    if args.previous:
        # verified = tickers a human already put in the repo: curated + public-primes + the last published snapshot
        tickers = repo_verified_tickers([os.path.join(data_dir, "curated.json"),
                                         os.path.join(data_dir, "public-primes.json"), args.previous])
    res = validate(doc, previous=previous, lanes=list(cfg.get("lanes", {})), quality=cfg.get("quality"),
                   verified_tickers=tickers, allow_count_change=args.allow_count_change, meta=meta, js_doc=js_doc)
    if tickers is None:
        res.warn("no --previous snapshot given: row-count and verified-ticker checks skipped")
    md = res.render_md()
    print(md)
    res.annotate()
    if args.report_md:
        with open(args.report_md, "a", encoding="utf-8") as f:
            f.write(md + "\n")
    if not res.ok:
        print(f"ERROR: data-quality gate FAILED ({len(res.errors)} error(s)). Do not publish this data.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
