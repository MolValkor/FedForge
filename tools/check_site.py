#!/usr/bin/env python3
"""Static checks for the FedForge site (stdlib only). Run: python3 tools/check_site.py

- every page has title, description, canonical, Open Graph image, large Twitter card, favicon
- no page loads the Tailwind CDN script (compiled css/tailwind.css is used instead)
- exactly one <h1> per page, no duplicate id="" values in the static markup
- JSON-LD blocks parse as JSON
- local href/src references resolve to files in the repo
- feed.xml and sitemap.xml are well-formed, and every sitemap URL maps to a real file
- feed.xml / sitemap.xml are in sync with data/ (tools/build_site_files.py --check)
- every flagship award in data/curated.json has an https source_url
"""
import json
import os
import re
import subprocess
import sys
import xml.dom.minidom
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://thefedforge.com"
SKIP_DIRS = {".git", "tools", "node_modules", "img"}
errors = []


def err(msg):
    errors.append(msg)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.h1, self.refs, self.ld, self._in_ld, self._buf = [], 0, [], [], False, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "h1":
            self.h1 += 1
        for k in ("href", "src"):
            if a.get(k):
                self.refs.append(a[k])
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld, self._buf = True, []

    def handle_data(self, data):
        if self._in_ld:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self.ld.append("".join(self._buf))
            self._in_ld = False


def pages():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(".html"):
                yield os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")


def resolve(rel_page, ref):
    ref = ref.split("#")[0].split("?")[0]
    if not ref or re.match(r"^[a-z][a-z0-9+.-]*:", ref, re.I) or ref.startswith("//"):
        return None  # external, mailto:, data:, anchor-only
    if ref.startswith("/"):
        target = ref.lstrip("/")
    else:
        target = os.path.normpath(os.path.join(os.path.dirname(rel_page), ref)).replace(os.sep, "/")
    target = target.rstrip("/")
    cands = [target, target + ".html", (target + "/index.html").lstrip("/")] if target else ["index.html"]
    return None if any(os.path.isfile(os.path.join(ROOT, c)) for c in cands) else target


REQUIRED = {
    "title": r"<title>[^<]{10,}</title>",
    "description": r'<meta name="description" content="[^"]{30,}"',
    "og:image": r'<meta property="og:image" content="https://thefedforge\.com/img/og-fedforge\.png"',
    "twitter large card": r'<meta name="twitter:card" content="summary_large_image"',
    "favicon": r'rel="icon"',
    "rss link": r'type="application/rss\+xml"',
    "viewport": r'name="viewport"',
    'lang="en"': r'<html lang="en"',
}

all_pages = list(pages())
for rel in all_pages:
    src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    for name, rx in REQUIRED.items():
        if not re.search(rx, src):
            err(f"{rel}: missing {name}")
    if rel != "award.html" and not re.search(r'<link rel="canonical" href="https://thefedforge\.com/', src):
        err(f"{rel}: missing canonical")
    if "cdn.tailwindcss.com" in src:
        err(f"{rel}: still loads the Tailwind CDN")
    p = Page()
    p.feed(src)
    if p.h1 != 1 and not (rel == "award.html" and p.h1 == 0):  # award.html renders its <h1> from ?id=
        err(f"{rel}: {p.h1} <h1> elements (want 1)")
    dupes = sorted({i for i in p.ids if p.ids.count(i) > 1})
    if dupes:
        err(f"{rel}: duplicate ids {dupes}")
    for block in p.ld:
        try:
            json.loads(block)
        except ValueError as e:
            err(f"{rel}: JSON-LD does not parse ({e})")
    for ref in p.refs:
        missing = resolve(rel, ref)
        if missing is not None:
            err(f"{rel}: broken local link {ref!r}")

for name in ("feed.xml", "sitemap.xml"):
    try:
        xml.dom.minidom.parse(os.path.join(ROOT, name))
    except Exception as e:  # noqa: BLE001
        err(f"{name}: not well-formed XML ({e})")

feed = xml.dom.minidom.parse(os.path.join(ROOT, "feed.xml"))
items = feed.getElementsByTagName("item")
if not items:
    err("feed.xml: no items")
for it in items:
    for tag in ("title", "link", "guid", "pubDate", "description"):
        if not it.getElementsByTagName(tag):
            err(f"feed.xml: item missing <{tag}>")

sm = xml.dom.minidom.parse(os.path.join(ROOT, "sitemap.xml"))
for loc in sm.getElementsByTagName("loc"):
    url = loc.firstChild.nodeValue.strip()
    path = url[len(SITE):].lstrip("/") or "index.html"
    if not os.path.isfile(os.path.join(ROOT, path)):
        err(f"sitemap.xml: {url} has no file")

for a in json.load(open(os.path.join(ROOT, "data", "curated.json"), encoding="utf-8"))["awards"]:
    if not str(a.get("source_url", "")).startswith("https://"):
        err(f"curated.json: {a.get('id')} has no https source_url")

for script in ("build_site_files.py", "seo_head.py"):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", script), "--check"], capture_output=True, text=True)
    if r.returncode != 0:
        err(f"tools/{script} --check failed:\n{r.stdout}{r.stderr}")

if not os.path.isfile(os.path.join(ROOT, "css", "tailwind.css")):
    err("css/tailwind.css is missing")

print(f"checked {len(all_pages)} pages, {len(items)} feed items")
if errors:
    print(f"{len(errors)} problem(s):")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("all checks passed")
