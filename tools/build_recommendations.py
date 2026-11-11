#!/usr/bin/env python3
"""Render recommendations.html from data/recommendations.json (stdlib only).

    python3 tools/build_recommendations.py          # rewrite recommendations.html
    python3 tools/build_recommendations.py --check  # exit 1 if the page is out of date or a citation is bad

Every takeaway in data/recommendations.json must cite at least one award with an https
USAspending.gov source_url and a positive amount copied from the API. Nothing is invented.
Informational only, not investment advice.
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "recommendations.json")
OUT = os.path.join(ROOT, "recommendations.html")
LANE = {"nuclear": "Nuclear / SMRs", "magnets": "Magnets / rare earths", "chips": "Semiconductors / CHIPS", "all": "All lanes"}
LANE_PAGE = {"nuclear": "nuclear.html", "magnets": "magnets.html", "chips": "chips.html"}
COLOR = {"nuclear": "#C4A574", "magnets": "#3D6B4F", "chips": "#8A8F82", "all": "#C47B6A"}
E = html.escape


def money(n):
    n = float(n)
    if n >= 1e9:
        return f"${n / 1e9:,.2f}B"
    if n >= 1e6:
        return f"${n / 1e6:,.1f}M"
    return f"${n / 1e3:,.0f}K"


def validate(doc):
    errs = []
    recs = doc.get("recommendations", [])
    if not 5 <= len(recs) <= 8:
        errs.append(f"expected 5-8 recommendations, found {len(recs)}")
    for r in recs:
        if not r.get("cites"):
            errs.append(f"{r.get('id')}: no cited awards")
        for c in r.get("cites", []):
            if not str(c.get("source_url", "")).startswith("https://www.usaspending.gov/award/"):
                errs.append(f"{r.get('id')}: {c.get('id')} source_url is not a USAspending award link")
            if not (isinstance(c.get("amount"), (int, float)) and c["amount"] > 0):
                errs.append(f"{r.get('id')}: {c.get('id')} has no positive amount")
    return errs


def render(doc):
    w = doc["windows"]
    cur, pri = w["current"], w["prior"]
    rows = []
    for k in ("nuclear", "magnets", "chips"):
        a, b = cur["lanes"][k], pri["lanes"][k]
        rows.append(f'<tr><td><a class="bronze-link" href="{LANE_PAGE[k]}">{E(LANE[k])}</a></td>'
                    f'<td class="text-right">{a["count"]}</td><td class="text-right">{money(a["amount"])}</td>'
                    f'<td class="text-right">{b["count"]}</td><td class="text-right">{money(b["amount"])}</td></tr>')
    rows.append(f'<tr><td><strong>All three lanes</strong></td><td class="text-right"><strong>{cur["count"]}</strong></td>'
                f'<td class="text-right"><strong>{money(cur["amount"])}</strong></td><td class="text-right">{pri["count"]}</td>'
                f'<td class="text-right">{money(pri["amount"])}</td></tr>')
    cards = []
    for n, r in enumerate(doc["recommendations"], 1):
        cites = "".join(
            f'<li><a class="bronze-link" href="{E(c["source_url"])}" target="_blank" rel="noopener">{E(c["recipient_name"])}</a>'
            f' · {money(c["amount"])} · {E(c["agency"])} · {E(c["date"])}</li>' for c in r["cites"])
        extra = "".join(f' <a class="bronze-link" href="{E(l["href"])}">{E(l["label"])} →</a>' for l in r.get("links", []))
        cards.append(
            f'<article id="{E(r["id"])}" class="deco-card rounded-3xl p-6 border-l-4 scroll-mt-24" style="border-left-color:{COLOR.get(r["lane"], "#C4A574")}">'
            f'<div class="text-xs bronze-text mb-1">{n:02d} · {E(LANE.get(r["lane"], r["lane"]))}</div>'
            f'<h2 class="text-xl font-semibold mb-2">{E(r["headline"])}</h2>'
            f'<p class="text-sm text-[#A3A89A] mb-3">{E(r["body"])}{extra}</p>'
            f'<p class="text-xs bronze-text mb-1">Cited awards (USAspending.gov)</p>'
            f'<ul class="rec-cites text-xs text-[#8A8F82]">{cites}</ul>'
            f'<p class="mt-3 no-print"><button type="button" class="filter-btn" data-copy-link="https://thefedforge.com/recommendations.html#{E(r["id"])}">Copy link</button></p>'
            f'</article>')
    desc = ("Data-backed takeaways from FedForge's latest USAspending refresh: which lanes and agencies are accelerating, "
            "notable new primes and what to watch in nuclear, magnets / rare earths and CHIPS. Not investment advice.")
    tmpl = open(os.path.join(ROOT, "findings.html"), encoding="utf-8").read()
    head_end = tmpl.index("</head>")
    head = tmpl[:head_end]
    head = head.replace("<title>Findings · FedForge</title>", "<title>Recommendations: what the latest federal award data says · FedForge</title>")
    head = head.replace("https://thefedforge.com/findings.html", "https://thefedforge.com/recommendations.html")
    head = head.replace("Findings · FedForge", "Recommendations · FedForge")
    old_desc = "PAC-3 face vs obligated, red-after-announcement returns, and LOI vs FINAL CHIPS DFAs. Copy-share findings. Not investment advice."
    head = head.replace(old_desc, desc)
    nav_start = tmpl.index("<a class=\"skip-link\"")
    nav_end = tmpl.index("</nav>") + len("</nav>")
    nav = tmpl[nav_start:nav_end].replace(' class="nav-link is-active" aria-current="page"', ' class="nav-link"').replace(' class="is-active" aria-current="page"', "")
    foot_start = tmpl.index("<footer")
    foot = tmpl[foot_start:]
    body = f"""
<body>
    {nav}
    <main id="main">
    <div class="max-w-3xl mx-auto px-6 py-12">
        <p class="text-sm bronze-text mb-2">Analysis · refreshed {E(doc["generated_at"])}</p>
        <h1 class="text-4xl font-semibold mb-3">Recommendations</h1>
        <p class="text-[#8A8F82] mb-3">{len(doc["recommendations"])} takeaways from the latest USAspending.gov pull: what is accelerating, who is new, and what to watch. Each one cites the awards behind it. Window {E(cur["start"])} to {E(cur["end"])}, compared with the prior 90 days ({E(pri["start"])} to {E(pri["end"])}).</p>
        <p class="meta-stamp mb-6" data-meta-stamp>Loading last USAspending pull…</p>
        <div class="disclaimer-banner rounded-2xl p-4 mb-8 text-sm"><strong>Not investment advice.</strong> {E(doc["disclaimer"])}</div>
        <section class="deco-card rounded-3xl p-6 mb-8" aria-labelledby="rec-totals">
            <h2 id="rec-totals" class="text-xl font-semibold mb-3">Qualifying new awards by lane</h2>
            <div class="rec-table-wrap"><table class="rec-table text-sm">
                <thead><tr><th>Lane</th><th class="text-right">Awards<br><span class="text-xs text-[#8A8F82]">{E(cur["start"][5:])}–{E(cur["end"][5:])}</span></th><th class="text-right">Award Amount</th><th class="text-right">Awards<br><span class="text-xs text-[#8A8F82]">{E(pri["start"][5:])}–{E(pri["end"][5:])}</span></th><th class="text-right">Award Amount</th></tr></thead>
                <tbody>{"".join(rows)}</tbody>
            </table></div>
            <p class="text-xs text-[#8A8F82] mt-3">{E(doc["method"])} The <a class="bronze-link" href="awards.html#new-primes">New primes feed</a> shows the top 25 per lane.</p>
        </section>
        <div class="space-y-4">
            {"".join(cards)}
        </div>
        <p class="text-xs text-[#8A8F82] mt-8">Method and data: <a class="bronze-link" href="data/recommendations.json">data/recommendations.json</a> · <a class="bronze-link" href="data/awards.json">data/awards.json</a> · <a class="bronze-link" href="glossary.html">Glossary</a> · <a class="bronze-link" href="guides/how-to-read-a-federal-award.html">How to read a federal award</a></p>
    </div>
    </main>
    {foot}"""
    return head + "</head>" + body


def main():
    doc = json.load(open(SRC, encoding="utf-8"))
    errs = validate(doc)
    if errs:
        print("recommendations.json errors:\n  " + "\n  ".join(errs))
        return 1
    page = render(doc)
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if cur != page:
            print("recommendations.html is out of date: run python3 tools/build_recommendations.py")
            return 1
        print(f"recommendations ok ({len(doc['recommendations'])} takeaways)")
        return 0
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote recommendations.html ({len(doc['recommendations'])} takeaways)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
