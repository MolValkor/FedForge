#!/usr/bin/env python3
"""Fetch, filter, score and write FedForge "new primes" award data (stdlib only, no installs).

    python3 tools/fetch_awards.py                     # pull last 90 days, rewrite data/awards.json + js/awards-data.js + data/meta.json
    python3 tools/fetch_awards.py --dry-run           # pull and report, write nothing
    python3 tools/fetch_awards.py --days 120 --end 2026-10-07 --report-md /tmp/run.md

Sources
  * USAspending.gov  POST /api/v2/search/spending_by_award/  (public, no key). Always used.
  * SAM.gov Contract Awards API  GET /contract-awards/v1/search  (needs a free SAM.gov "Public API Key").
    Only used when the SAM_API_KEY environment variable is set. Adds contracts USAspending has not loaded yet.

Pipeline
  1. For each lane in tools/pipeline/lanes.json run: lane keywords x contracts (A-D), lane keywords x grants
     (02-05), lane NAICS x contracts. Window = new_awards_only, domestic recipients, prime awards only,
     Award Amount >= --min-amount. Every page is followed until the API says there is no next page.
  2. Dedupe on USAspending's generated_internal_id (one row per award, however many queries found it).
  3. Score every award against every lane (0-100) from the award's own description, recipient, NAICS,
     agency and amount. Keep it under its best lane if that score >= threshold; cap each lane at --per-lane.
  4. Attach a ticker ONLY when the award id or the exact recipient name already carries a verified ticker
     somewhere in data/*.json. No new tickers are ever guessed.
  5. Write the same shape the site already reads (data/awards.json, baked copy in js/awards-data.js) and
     stamp data/meta.json (last_usaspending_pull, primes_count, primes_window).

Every amount, date, recipient and description is copied from the API response. Nothing is estimated,
projected or invented; if the APIs return nothing, the file says so (count 0) rather than keeping stale rows.
Exit code is 0 on success, 2 if USAspending could not be reached (files are left untouched in that case).
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANES_FILE = os.path.join(ROOT, "tools", "pipeline", "lanes.json")
USA_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
SAM_URL = "https://api.sam.gov/contract-awards/v1/search"
UA = "FedForge-pipeline/1.0 (+https://thefedforge.com)"
CONTRACTS = ["A", "B", "C", "D"]
GRANTS = ["02", "03", "04", "05"]
BASE_FIELDS = ["Award ID", "Recipient Name", "Award Amount", "Description", "Start Date", "Base Obligation Date",
               "Awarding Agency", "Awarding Sub Agency", "generated_internal_id"]
CONTRACT_FIELDS = BASE_FIELDS + ["NAICS", "PSC", "Contract Award Type"]
GRANT_FIELDS = BASE_FIELDS + ["Award Type", "CFDA Number"]
DESC_MAX = 200  # matches the existing hand-built file: 197 chars + "..."


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- HTTP

def http_json(url, payload=None, tries=4, timeout=90):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:300].decode('utf-8', 'replace')}"
            if e.code in (400, 401, 403, 404, 422):
                break  # not retryable
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(last or "request failed")


# ---------------------------------------------------------------- USAspending

def usa_query(filters, fields, max_pages, stats, label):
    rows, page = [], 1
    while page <= max_pages:
        body = {"filters": filters, "fields": fields, "sort": "Award Amount", "order": "desc",
                "limit": 100, "page": page, "subawards": False}
        d = http_json(USA_URL, body)
        stats["requests"] += 1
        res = d.get("results") or []
        rows.extend(res)
        meta = d.get("page_metadata") or {}
        if not meta.get("hasNext") or not res:
            break
        page += 1
        time.sleep(0.3)  # be polite to a free public API
    else:
        stats["truncated"].append(label)
    return rows


def fetch_usaspending(lanes, start, end, min_amount, max_pages, stats):
    base = {"time_period": [{"start_date": start, "end_date": end, "date_type": "new_awards_only"}],
            "recipient_scope": "domestic", "award_amounts": [{"lower_bound": min_amount}]}
    raw = []
    for key, lane in lanes.items():
        jobs = [
            (f"{key}: keywords x contracts", dict(base, keywords=lane["query_keywords"], award_type_codes=CONTRACTS), CONTRACT_FIELDS),
            (f"{key}: keywords x grants", dict(base, keywords=lane["query_keywords"], award_type_codes=GRANTS), GRANT_FIELDS),
        ]
        if lane.get("naics"):
            jobs.append((f"{key}: NAICS x contracts", dict(base, naics_codes={"require": lane["naics"]}, award_type_codes=CONTRACTS), CONTRACT_FIELDS))
        for label, filters, fields in jobs:
            rows = usa_query(filters, fields, max_pages, stats, label)
            stats["per_query"][label] = len(rows)
            log(f"  {label}: {len(rows)} rows")
            for r in rows:
                raw.append(normalize_usa(r))
    return raw


def code_of(v):
    if isinstance(v, dict):
        return (v.get("code") or "").strip()
    return (v or "").strip() if isinstance(v, str) else ""


def normalize_usa(r):
    gid = r.get("generated_internal_id") or ""
    return {
        "key": gid or f"USA:{r.get('Award ID')}",
        "id": str(r.get("Award ID") or "").strip(),
        "date": (r.get("Base Obligation Date") or r.get("Start Date") or "")[:10],
        "agency": r.get("Awarding Agency") or "",
        "sub_agency": r.get("Awarding Sub Agency") or "",
        "recipient_name": (r.get("Recipient Name") or "").strip(),
        "amount": float(r["Award Amount"]) if r.get("Award Amount") is not None else None,
        "description_full": (r.get("Description") or "").strip(),
        "source_url": f"https://www.usaspending.gov/award/{urllib.parse.quote(gid)}" if gid else "",
        "naics": code_of(r.get("NAICS")),
        "psc": code_of(r.get("PSC")),
        "award_type": r.get("Contract Award Type") or r.get("Award Type") or "",
        "origin": "usaspending",
    }


# ---------------------------------------------------------------- SAM.gov (optional, key required)

def dig(d, *path):
    for p in path:
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def sam_date(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def fetch_sam(lanes, start, end, min_amount, key, max_requests, stats):
    """One request per lane (NAICS OR-list, base awards only). A personal SAM.gov key without a role is
    limited to 10 requests/day, so this stays tiny on purpose. Failures are logged and never stop the run."""
    out = []
    mmdd = lambda iso: datetime.strptime(iso, "%Y-%m-%d").strftime("%m/%d/%Y")
    for lane_key, lane in lanes.items():
        if not lane.get("naics") or stats["sam_requests"] >= max_requests:
            continue
        params = {"api_key": key, "limit": "100", "dateSigned": f"[{mmdd(start)},{mmdd(end)}]",
                  "naicsCode": "~".join(lane["naics"]), "modificationNumber": "0",
                  "includeSections": "contractId,coreData,awardDetails"}
        url = SAM_URL + "?" + urllib.parse.urlencode(params, safe="[],~/")
        try:
            d = http_json(url, tries=2)
            stats["sam_requests"] += 1
        except Exception as e:  # noqa: BLE001
            msg = str(e).replace(key, "***")
            if any(c in msg for c in ("HTTP 401", "HTTP 403", "HTTP 404")):
                msg += " (SAM.gov answers 403/404 for a missing, invalid or not-yet-activated key: check the SAM_API_KEY secret)"
            stats["sam_errors"].append(f"{lane_key}: {msg}")
            continue
        recs = d.get("awardSummary") or []
        stats["per_query"][f"{lane_key}: SAM.gov NAICS x base contracts"] = len(recs)
        for rec in recs:
            piid = dig(rec, "contractId", "piid") or ""
            sub = dig(rec, "contractId", "subtier", "code") or ""
            ref_piid = dig(rec, "contractId", "referencedIDVPiid") or "-NONE-"
            ref_sub = dig(rec, "contractId", "referencedIDVSubtier", "code") or "-NONE-"
            amt = dig(rec, "awardDetails", "totalContractDollars", "totalActionObligation")
            try:
                amt = float(amt) if amt not in (None, "") else None
            except ValueError:
                amt = None
            if not piid or amt is None or amt < min_amount:
                continue
            naics = dig(rec, "coreData", "productOrServiceInformation", "principalNaics") or []
            naics = naics[0].get("code", "") if isinstance(naics, list) and naics and isinstance(naics[0], dict) else ""
            gid = f"CONT_AWD_{piid}_{sub}_{ref_piid}_{ref_sub}" if sub else ""
            out.append({
                "key": gid or f"SAM:{piid}",
                "id": piid,
                "date": sam_date(dig(rec, "awardDetails", "dates", "dateSigned")),
                "agency": dig(rec, "coreData", "federalOrganization", "contractingInformation", "contractingDepartment", "name") or "",
                "sub_agency": dig(rec, "coreData", "federalOrganization", "contractingInformation", "contractingSubtier", "name") or "",
                "recipient_name": (dig(rec, "awardDetails", "awardeeData", "awardeeHeader", "awardeeName")
                                   or dig(rec, "awardDetails", "awardeeData", "awardeeHeader", "legalBusinessName") or "").strip(),
                "amount": amt,
                "amount_display_suffix": "obligated (SAM.gov)",
                "description_full": (dig(rec, "awardDetails", "productOrServiceInformation", "descriptionOfContractRequirement") or "").strip(),
                "source_url": f"https://www.usaspending.gov/award/{urllib.parse.quote(gid)}" if gid else "",
                "naics": naics,
                "psc": dig(rec, "coreData", "productOrServiceInformation", "productOrService", "code") or "",
                "award_type": dig(rec, "coreData", "awardOrIDVType", "name") or "",
                "origin": "sam.gov",
            })
    return out


# ---------------------------------------------------------------- scoring

def compile_lanes(cfg):
    out = {}
    for k, lane in cfg["lanes"].items():
        out[k] = dict(lane,
                      _strong=[re.compile(p, re.I) for p in lane.get("strong", [])],
                      _weak=[re.compile(p, re.I) for p in lane.get("weak", [])],
                      _mask=[re.compile(p, re.I) for p in lane.get("mask", [])])
    return out


def score_lane(a, lane, sc):
    text = f"{a['description_full']} {a['recipient_name']}"
    for m in lane["_mask"]:
        text = m.sub(" ", text)
    strong = sorted({m.group(0).upper() for rx in lane["_strong"] for m in [rx.search(text)] if m})
    weak = sorted({m.group(0).upper() for rx in lane["_weak"] for m in [rx.search(text)] if m} - set(strong))
    reasons, s = [], 0
    if strong:
        s += min(sc["strong_cap"], sc["first_strong"] + sc["extra_strong"] * (len(strong) - 1))
        reasons.append("terms:" + "|".join(strong))
        lead = a["description_full"][:sc.get("lead_chars", 150)]
        for m in lane["_mask"]:
            lead = m.sub(" ", lead)
        if any(rx.search(lead) for rx in lane["_strong"]):
            s += sc.get("lead_bonus", 0)
            reasons.append("lead")
    if weak:
        s += min(sc["weak_cap"], sc["weak_each"] * len(weak))
        reasons.append("weak:" + "|".join(weak))
    if a["naics"] and a["naics"] in lane.get("naics", []):
        s += sc["naics_match"]
        reasons.append("naics:" + a["naics"])
    if a["agency"] in lane.get("agencies", []):
        s += sc["agency_match"]
        reasons.append("agency")
    for floor, pts in sc["amount_tiers"]:
        if (a["amount"] or 0) >= floor:
            s += pts
            reasons.append(f"amount>={floor:,}")
            break
    if a["naics"] in sc.get("lab_equipment_naics", []):
        s -= sc["lab_equipment_penalty"]
        reasons.append("lab-equipment-penalty")
    if not strong and not weak:
        s = 0  # NAICS/agency/amount alone never qualify an award; the award text has to be about the lane
    return max(0, min(100, s)), reasons


def classify(a, lanes, sc):
    best = (0, None, [])
    for k, lane in lanes.items():
        s, why = score_lane(a, lane, sc)
        if s > best[0]:
            best = (s, k, why)
    return best


# ---------------------------------------------------------------- tickers (verified only)

def norm_name(s):
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]+", " ", (s or "").upper())).strip()


def verified_tickers():
    """Ticker sources: rows in data/*.json that already carry a ticker (human-verified). Exact matches only."""
    by_id, by_name = {}, {}
    for fn in ("awards.json", "public-primes.json", "curated.json"):
        p = os.path.join(ROOT, "data", fn)
        if not os.path.exists(p):
            continue
        for a in json.load(open(p, encoding="utf-8")).get("awards", []):
            t = a.get("ticker")
            if not t:
                continue
            if a.get("id"):
                by_id[str(a["id"])] = t
            if a.get("recipient_name"):
                by_name[norm_name(a["recipient_name"])] = t
    return by_id, by_name


# ---------------------------------------------------------------- output

def short_desc(s):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= DESC_MAX else s[:DESC_MAX - 3] + "..."


def fmt_money(n):
    if n is None:
        return "n/a"
    if n >= 1e9:
        return f"${n / 1e9:.2f}B"
    if n >= 1e6:
        return f"${n / 1e6:.1f}M"
    if n >= 1e3:
        return f"${n / 1e3:,.0f}K"
    return f"${n:,.0f}"


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--end", default=date.today().isoformat(), help="window end (YYYY-MM-DD), default today")
    ap.add_argument("--days", type=int, default=90, help="rolling window length in days (default 90)")
    ap.add_argument("--min-amount", type=float, default=250000, help="drop awards below this Award Amount (default 250000)")
    ap.add_argument("--per-lane", type=int, default=25, help="max awards kept per lane (default 25)")
    ap.add_argument("--max-pages", type=int, default=10, help="max 100-row pages per query (default 10)")
    ap.add_argument("--dry-run", action="store_true", help="fetch and report only, write no site files")
    ap.add_argument("--report-json", help="write a machine-readable run report here")
    ap.add_argument("--report-md", help="write a Markdown run summary here (used as the PR body)")
    args = ap.parse_args()

    cfg = json.load(open(LANES_FILE, encoding="utf-8"))
    lanes, sc = compile_lanes(cfg), cfg["scoring"]
    end = date.fromisoformat(args.end)
    start = end - timedelta(days=args.days)
    s_iso, e_iso = start.isoformat(), end.isoformat()
    stats = {"requests": 0, "per_query": {}, "truncated": [], "sam_requests": 0, "sam_errors": []}
    pulled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    log(f"USAspending window {s_iso} .. {e_iso} (new_awards_only, domestic, >= ${args.min_amount:,.0f})")
    try:
        raw = fetch_usaspending(lanes, s_iso, e_iso, args.min_amount, args.max_pages, stats)
    except Exception as e:  # noqa: BLE001
        log(f"ERROR: USAspending unreachable or rejected the query: {e}. No files written.")
        sys.exit(2)

    sam_key = os.environ.get("SAM_API_KEY", "").strip()
    sam_status = "skipped (SAM_API_KEY not set)"
    if sam_key:
        log("SAM.gov: SAM_API_KEY present, querying Contract Awards API")
        sam_rows = fetch_sam(lanes, s_iso, e_iso, args.min_amount, sam_key,
                             int(os.environ.get("SAM_MAX_REQUESTS", "3")), stats)
        sam_status = f"{stats['sam_requests']} request(s), {len(sam_rows)} row(s)" + (f", errors: {stats['sam_errors']}" if stats["sam_errors"] else "")
        raw.extend(sam_rows)

    # dedupe: USAspending rows first so they win over SAM.gov copies of the same contract
    seen, seen_ids, uniq = set(), set(), []
    for a in raw:
        if a["key"] in seen or (a["origin"] == "sam.gov" and a["id"] in seen_ids):
            continue
        seen.add(a["key"])
        seen_ids.add(a["id"])
        uniq.append(a)

    by_id, by_name = verified_tickers()
    kept, rejected, fate = {k: [] for k in lanes}, 0, {}
    for a in uniq:
        if not a["id"] or not a["date"] or a["amount"] is None or not a["source_url"]:
            rejected += 1
            fate[a["id"]] = "returned without id/date/amount/source"
            continue
        s, lane, why = classify(a, lanes, sc)
        if lane is None or s < sc["threshold"]:
            rejected += 1
            fate[a["id"]] = f"below relevance threshold (score {s} < {sc['threshold']})"
            continue
        a.update(score=s, sector=lane, why=why)
        kept[lane].append(a)

    final, lane_stats = [], {}
    for k, rows in kept.items():
        # Relevance decides IF an award is in. For the per-lane cut, "core" awards (score >= core_score:
        # the award is about the lane, not a passing mention) go first, largest dollars first ("follow the
        # money"); passing-mention awards only fill leftover slots. Ties fall back to score, then id.
        core = sc.get("core_score", 60)
        rows.sort(key=lambda a: (a["score"] < core, -(a["amount"] or 0), -a["score"], a["id"]))
        for a in rows[args.per_lane:]:
            fate[a["id"]] = f"qualified (score {a['score']}) but below the top {args.per_lane} by amount in {k}"
        lane_stats[k] = {"label": lanes[k]["label"], "qualified": len(rows), "kept": min(len(rows), args.per_lane),
                         "amount_kept": sum(a["amount"] for a in rows[:args.per_lane])}
        final.extend(rows[:args.per_lane])
    final.sort(key=lambda a: (a["date"], a["amount"] or 0, a["id"]), reverse=True)

    # collapse duplicate display ids (award.html?id= looks up by id); keep the higher score
    out_rows, ids = [], {}
    for a in final:
        if a["id"] in ids:
            if a["score"] > ids[a["id"]]["score"]:
                out_rows[out_rows.index(ids[a["id"]])] = a
                ids[a["id"]] = a
            continue
        ids[a["id"]] = a
        out_rows.append(a)

    awards = []
    for a in out_rows:
        t = by_id.get(a["id"]) or by_name.get(norm_name(a["recipient_name"]))
        row = {"id": a["id"], "date": a["date"], "agency": a["agency"], "recipient_name": a["recipient_name"],
               "amount": a["amount"], "description": short_desc(a["description_full"]), "source_url": a["source_url"],
               "sector": a["sector"], "public": bool(t)}
        if a.get("amount_display_suffix"):
            row["amount_display"] = f"{fmt_money(a['amount'])} {a['amount_display_suffix']}"
        if t:
            row["ticker"] = t
        row["score"] = a["score"]
        awards.append(row)

    old_path = os.path.join(ROOT, "data", "awards.json")
    old = json.load(open(old_path, encoding="utf-8")) if os.path.exists(old_path) else {"awards": []}
    old_ids = {x["id"]: x for x in old.get("awards", [])}
    new_ids = {x["id"] for x in awards}
    added = [x for x in awards if x["id"] not in old_ids]
    dropped = [{"id": i, "recipient_name": x.get("recipient_name"), "date": x.get("date"),
                "reason": fate.get(i, f"not a new award inside {s_iso}..{e_iso} (aged out of the rolling window or not matched by the lane queries)")}
               for i, x in old_ids.items() if i not in new_ids]
    strip = lambda rows: [{k: v for k, v in r.items() if k != "score"} for r in rows]
    changed = strip(old.get("awards", [])) != strip(awards)

    lane_list = ", ".join(f"{v['label']} ({k})" for k, v in lanes.items())
    doc = {
        "generated_at": e_iso,
        "source": USA_URL,
        "window": {"start": s_iso, "end": e_iso, "date_type": "new_awards_only", "recipient_scope": "domestic"},
        "queries": [
            "per lane: lane keywords x contracts A-D, lane keywords x grants 02-05, lane NAICS x contracts (tools/pipeline/lanes.json)",
            f"lanes: {lane_list}",
            f"Award Amount >= ${args.min_amount:,.0f}; prime awards only (subawards=false); every result page followed",
            "deduped on USAspending generated_internal_id; scored 0-100 from description/recipient terms, NAICS, agency and amount; "
            f"kept if score >= {sc['threshold']}, max {args.per_lane} per lane"
            + ("; plus SAM.gov Contract Awards API base contracts by lane NAICS" if sam_key else ""),
        ],
        "note": (f"Automated pull by tools/fetch_awards.py at {pulled_at}. date = base obligation (award) date. "
                 "Amounts are Award Amount exactly as returned by the API. Tickers are attached only when the award id or "
                 "exact recipient name already carries a human-verified ticker in this repo's data; no tickers are guessed. "
                 "The USAspending API does not send CORS headers, so this file is refreshed server-side (GitHub Actions) "
                 "and reaches the live site only after a human merges the data pull request."),
        "count": len(awards),
        "pipeline": {"version": 1, "score_threshold": sc["threshold"], "per_lane_cap": args.per_lane,
                     "candidates": len(uniq), "sam_gov": sam_status},
        "awards": awards,
    }

    report = {"pulled_at": pulled_at, "window": doc["window"], "requests": stats["requests"],
              "per_query": stats["per_query"], "truncated_queries": stats["truncated"], "raw_rows": len(raw),
              "unique_candidates": len(uniq), "rejected": rejected, "lanes": lane_stats, "total_kept": len(awards),
              "public_with_ticker": sum(1 for a in awards if a.get("ticker")), "sam_gov": sam_status,
              "changed": changed, "added": [a["id"] for a in added], "dropped": dropped}

    if args.report_json:
        write_text(args.report_json, json.dumps(report, indent=2) + "\n")
    md = render_md(report, awards, added, dropped, lanes)
    if args.report_md:
        write_text(args.report_md, md)
    print(md)

    if not args.dry_run:
        write_text(old_path, json.dumps(doc, separators=(",", ":")) + "\n")
        write_text(os.path.join(ROOT, "js", "awards-data.js"), "window.FEDFORGE_AWARDS=" + json.dumps(doc, separators=(",", ":")) + ";\n")
        meta_path = os.path.join(ROOT, "data", "meta.json")
        meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
        meta.update(last_usaspending_pull=pulled_at, primes_count=len(awards), primes_window={"start": s_iso, "end": e_iso})
        write_text(meta_path, json.dumps(meta, indent=2) + "\n")
        log("wrote data/awards.json, js/awards-data.js, data/meta.json")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"changed={'true' if changed else 'false'}\ncount={len(awards)}\nadded={len(added)}\ndropped={len(dropped)}\n")


def render_md(rep, awards, added, dropped, lanes):
    w = rep["window"]
    L = [f"### FedForge award pull: {w['start']} to {w['end']}", "",
         f"Pulled {rep['pulled_at']} from USAspending.gov ({rep['requests']} API requests). SAM.gov: {rep['sam_gov']}.", "",
         f"{rep['raw_rows']} raw rows, {rep['unique_candidates']} unique awards, {rep['total_kept']} kept "
         f"({rep['public_with_ticker']} with a verified ticker).", "",
         "| Lane | Qualified | Kept | Kept $ (Award Amount) |", "| --- | ---: | ---: | ---: |"]
    for k, v in rep["lanes"].items():
        L.append(f"| {v['label']} | {v['qualified']} | {v['kept']} | {fmt_money(v['amount_kept'])} |")
    if rep["truncated_queries"]:
        L += ["", f"Page cap reached (results may be incomplete): {', '.join(rep['truncated_queries'])}"]
    L += ["", f"Changed vs current data/awards.json: **{'yes' if rep['changed'] else 'no'}** "
          f"(+{len(added)} new, -{len(dropped)} dropped)"]
    if added:
        L += ["", "<details><summary>New awards</summary>", "", "| Date | Lane | Recipient | Amount | Score |", "| --- | --- | --- | ---: | ---: |"]
        for a in added:
            name = a["recipient_name"].replace("|", "/")
            L.append(f"| {a['date']} | {a['sector']} | [{name}]({a['source_url']}){' (' + a['ticker'] + ')' if a.get('ticker') else ''} | {fmt_money(a['amount'])} | {a['score']} |")
        L += ["", "</details>"]
    if dropped:
        L += ["", "<details><summary>Dropped awards</summary>", ""]
        for d in dropped:
            L.append(f"- {d['date']} {d['recipient_name']} (`{d['id']}`): {d['reason']}")
        L += ["", "</details>"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
