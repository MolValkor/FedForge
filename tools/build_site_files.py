#!/usr/bin/env python3
"""Generate feed.xml and sitemap.xml from the repo's own data (stdlib only, no installs).

    python3 tools/build_site_files.py          # rewrite feed.xml + sitemap.xml
    python3 tools/build_site_files.py --check  # exit 1 if either file is out of date

Feed items come only from data/curated.json (flagship official notices) and
data/public-primes.json (12-month public primes), plus the short EDITORIAL list below.
Every item carries the amount exactly as the data file states it and the official
source URL. Nothing is invented. Output is deterministic (no wall-clock timestamps),
so re-running without data changes produces a byte-identical file.

Netlify does not run this script (the site has no build step). Run it locally after
refreshing data/*.json and commit the output.
"""
import json
import os
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://thefedforge.com"
DISCLAIMER = "Not investment advice."

# Hand-written pages that belong in the feed. Dates are the dates these pages were published.
EDITORIAL = [
    {"title": "Finding: most award-day names went red", "path": "finding-red.html", "guid": "finding-red.html",
     "date": "2026-09-03",
     "description": "10 of 14 announcement-to-now closes in returns.json were negative as of 2026-09-01. Close-to-close only."},
    {"title": "Finding: LOI vs FINAL CHIPS DFAs (GFS)", "path": "finding-loi.html", "guid": "finding-loi.html",
     "date": "2026-09-03",
     "description": "$874M CHIPS LOI package vs curated FINAL DFAs. Status tags matter."},
    {"title": "Finding: PAC-3 MSE $53.86B face / $0 obligated", "path": "finding.html", "guid": "finding.html",
     "date": "2026-09-03",
     "description": "Lockheed Martin PAC-3 MSE Army modification. Face is not cash. UCA/mod."},
    {"title": "How to read a federal award", "path": "guides/how-to-read-a-federal-award.html",
     "guid": "guides/how-to-read-a-federal-award.html", "date": "2026-09-03",
     "description": "FINAL, LOI, UCA, obligated vs face. Educational guide."},
]

# Pages that are templates or utilities rather than content, kept out of the sitemap.
SITEMAP_EXCLUDE = {"award.html"}  # needs ?id=...; the flagship awards have static pages
SKIP_DIRS = {".git", "tools", "node_modules", "img"}


def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


def rfc822(iso_date):
    d = datetime.strptime(iso_date, "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
    return format_datetime(d, usegmt=True)


def item(title, link, guid, date, description, category=None):
    parts = [
        "    <item>",
        f"      <title>{escape(title)}</title>",
        f"      <link>{escape(link)}</link>",
        f'      <guid isPermaLink="true">{escape(guid)}</guid>',
        f"      <pubDate>{rfc822(date)}</pubDate>",
    ]
    if category:
        parts.append(f"      <category>{escape(category)}</category>")
    parts.append(f"      <description>{escape(description)}</description>")
    parts.append("    </item>")
    return "\n".join(parts)


SECTOR = {"nuclear": "Nuclear / SMRs", "magnets": "Magnets / rare earths", "chips": "Semiconductors / CHIPS",
          "other": "Defense / other"}


def build_feed():
    curated = load("curated.json")
    primes = load("public-primes.json")
    entries = []  # (date, sort_key, xml)
    for a in curated.get("awards", []):
        who = a.get("recipient_name", "")
        who_t = f"{who} ({a['ticker']})" if a.get("ticker") else f"{who} (private recipient, no public ticker)"
        status = a.get("status_label") or a.get("status", "")
        desc = " · ".join(x for x in [who_t, status, a.get("amount_display", ""), a.get("agency", "")] if x)
        desc += f". {a.get('description', '').strip()}"
        if a.get("source_url"):
            desc += f" Official source: {a['source_url']}"
        desc += f" {DISCLAIMER}"
        link = f"{SITE}/award/{a['id']}.html"
        guid = f"{SITE}/award/{a['id']}"  # guid format kept from the original hand-written feed
        entries.append((a["date"], a["id"], item(a.get("title", who), link, guid, a["date"], desc,
                                                  SECTOR.get(a.get("sector"), None))))
    for a in primes.get("awards", []):
        who = a.get("recipient_name", "")
        who_t = f"{who} ({a['ticker']})" if a.get("ticker") else who
        desc = " · ".join(x for x in [who_t, a.get("status", ""), a.get("amount_display", ""), a.get("agency", ""),
                                      "12-month USAspending public prime"] if x)
        desc += f". {a.get('description', '').strip()}"
        if a.get("source_url"):
            desc += f" Source: {a['source_url']}"
        desc += f" {DISCLAIMER}"
        link = f"{SITE}/award.html?id={a['id']}"
        entries.append((a["date"], a["id"], item(a.get("title", who), link, link, a["date"], desc,
                                                  SECTOR.get(a.get("sector"), None))))
    for e in EDITORIAL:
        entries.append((e["date"], e["path"], item(e["title"], f"{SITE}/{e['path']}", f"{SITE}/{e['guid']}",
                                                    e["date"], f"{e['description']} {DISCLAIMER}", "FedForge analysis")))
    entries.sort(key=lambda t: (t[0], t[1]), reverse=True)
    newest = max(t[0] for t in entries)
    built = max([newest, curated.get("generated_at", newest), primes.get("generated_at", newest)])
    head = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>FedForge: new federal awards to public companies</title>
    <link>{SITE}/</link>
    <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>New U.S. federal awards and contracts tracked by FedForge: recipient, ticker when public, status (FINAL / CONDITIONAL / LOI / UCA), the dollar amount as the source states it, and the official source link. {DISCLAIMER}</description>
    <language>en-us</language>
    <lastBuildDate>{rfc822(built)}</lastBuildDate>
    <image>
      <url>{SITE}/apple-touch-icon.png</url>
      <title>FedForge: new federal awards to public companies</title>
      <link>{SITE}/</link>
    </image>
"""
    return head + "\n".join(t[2] for t in entries) + "\n  </channel>\n</rss>\n"


def canonical_for(rel):
    rel = rel.replace(os.sep, "/")
    return f"{SITE}/" if rel == "index.html" else f"{SITE}/{rel}"


def html_pages():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(".html"):
                out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/"))
    return out


def build_sitemap():
    pages = [p for p in html_pages() if p not in SITEMAP_EXCLUDE]

    def order(p):  # home first, then top-level pages, then sub-directories
        return (p != "index.html", "/" in p, p)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in sorted(pages, key=order):
        lines.append(f"  <url><loc>{escape(canonical_for(p))}</loc><changefreq>weekly</changefreq></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    check = "--check" in sys.argv
    stale = []
    for name, content in (("feed.xml", build_feed()), ("sitemap.xml", build_sitemap())):
        path = os.path.join(ROOT, name)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old == content:
            print(f"{name}: up to date")
            continue
        if check:
            stale.append(name)
            print(f"{name}: OUT OF DATE (run python3 tools/build_site_files.py)")
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"{name}: written")
    sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
