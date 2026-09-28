#!/usr/bin/env python3
"""Idempotently add sharing/SEO tags to every page's <head> (stdlib only).

    python3 tools/seo_head.py          # patch pages in place
    python3 tools/seo_head.py --check  # exit 1 if any page is missing a tag

For each HTML page it makes sure these exist, reusing the page's own <title> and
meta description (it never rewrites copy):
  canonical URL, Open Graph (title/description/url/type/site_name/image), Twitter
  large-image card, favicon + apple-touch-icon, theme colour, and the RSS feed link.
Tags that already exist are left alone, except twitter:card "summary", which is
upgraded to "summary_large_image" now that a 1200x630 image exists.
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://thefedforge.com"
OG_IMAGE = f"{SITE}/img/og-fedforge.png"
OG_ALT = "FedForge: federal awards to public companies, with the official source."
NO_CANONICAL = {"award.html"}  # template page whose content depends on ?id=
SKIP_DIRS = {".git", "tools", "node_modules", "img"}


def pages():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(".html"):
                yield os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")


def attr(s):
    """Text from the page (already HTML-escaped or not) -> safe attribute value."""
    return html.escape(html.unescape(s), quote=True)


def wanted(rel, head):
    title_m = re.search(r"<title>(.*?)</title>", head, re.S)
    desc_m = re.search(r'<meta name="description" content="([^"]*)"', head)
    title = title_m.group(1).strip() if title_m else "FedForge"
    desc = desc_m.group(1) if desc_m else "Federal awards to public companies, with the official source. Not investment advice."
    url = f"{SITE}/" if rel == "index.html" else f"{SITE}/{rel}"
    tags = []  # (detect-regex, tag)
    if rel not in NO_CANONICAL:
        tags.append((r'rel="canonical"', f'<link rel="canonical" href="{url}">'))
    tags += [
        (r'property="og:title"', f'<meta property="og:title" content="{attr(title)}">'),
        (r'property="og:description"', f'<meta property="og:description" content="{attr(desc)}">'),
        (r'property="og:type"', '<meta property="og:type" content="website">'),
        (r'property="og:site_name"', '<meta property="og:site_name" content="FedForge">'),
        (r'property="og:image"', f'<meta property="og:image" content="{OG_IMAGE}">'
                                 '<meta property="og:image:width" content="1200">'
                                 '<meta property="og:image:height" content="630">'
                                 f'<meta property="og:image:alt" content="{attr(OG_ALT)}">'),
        (r'name="twitter:card"', '<meta name="twitter:card" content="summary_large_image">'),
        (r'name="twitter:title"', f'<meta name="twitter:title" content="{attr(title)}">'),
        (r'name="twitter:description"', f'<meta name="twitter:description" content="{attr(desc)}">'),
        (r'name="twitter:image"', f'<meta name="twitter:image" content="{OG_IMAGE}">'
                                  f'<meta name="twitter:image:alt" content="{attr(OG_ALT)}">'),
        (r'rel="icon"', '<link rel="icon" href="/favicon.ico" sizes="any">'
                        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'),
        (r'rel="apple-touch-icon"', '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'),
        (r'name="theme-color"', '<meta name="theme-color" content="#12150F">'),
        (r'type="application/rss\+xml"', '<link rel="alternate" type="application/rss+xml" '
                                         f'title="FedForge: new federal awards" href="{SITE}/feed.xml">'),
    ]
    if rel not in NO_CANONICAL:
        tags.insert(3, (r'property="og:url"', f'<meta property="og:url" content="{url}">'))
    return tags


def process(rel, check):
    path = os.path.join(ROOT, rel)
    src = open(path, encoding="utf-8").read()
    end = src.find("</head>")
    if end == -1:
        return []
    head = src[:end]
    head2 = head.replace('<meta name="twitter:card" content="summary">',
                         '<meta name="twitter:card" content="summary_large_image">')
    missing = [tag for rx, tag in wanted(rel, head2) if not re.search(rx, head2)]
    if check:
        return missing + (["twitter:card summary"] if head2 != head else [])
    if missing or head2 != head:
        src = head2 + "".join(missing) + src[end:]
        open(path, "w", encoding="utf-8").write(src)
    return missing


def main():
    check = "--check" in sys.argv
    bad = 0
    for rel in pages():
        missing = process(rel, check)
        if missing:
            bad += 1
            print(f"{rel}: {'missing ' if check else 'added '}{len(missing)} tag group(s)")
    print(f"{'pages needing tags' if check else 'pages patched'}: {bad}")
    sys.exit(1 if (check and bad) else 0)


if __name__ == "__main__":
    main()
