# FedForge

Source for [thefedforge.com](https://thefedforge.com): a radar of U.S. federal awards and contracts won by
public companies. Each entry shows the deal, its status (FINAL / CONDITIONAL / LOI / UCA), the dollar
amount as the source states it, and the official source link. Not investment advice.

## How the site is built

Plain static HTML, CSS and JavaScript, deployed as-is by Netlify. **The repo has no build command**;
everything the site needs is committed. Data lives in `data/*.json` and is rendered
in the browser by the scripts in `js/`.

| Path | What it is |
| --- | --- |
| `index.html`, `*.html` | Top-level pages (dashboard, awards, sectors, companies, findings, follow, …) |
| `award/*.html` | Static permalink page for each flagship award |
| `ticker/*.html` | One page per verified public ticker |
| `guides/` | Explainers |
| `data/*.json` | Award data: `curated.json` (flagship notices), `awards.json` (USAspending new primes), `public-primes.json`, `returns.json`, `top20.json`, `meta.json` |
| `js/nav.js` | Builds the primary menu on every page from one list, plus the shared "Copy link" helper |
| `css/fedforge.css` | Site theme (bronze + forest green) |
| `css/tailwind.css` | Compiled Tailwind utilities (replaces the old `cdn.tailwindcss.com` script) |
| `feed.xml`, `sitemap.xml` | Generated from `data/` by `tools/build_site_files.py` |
| `img/og-fedforge.png` | 1200×630 social sharing image |
| `tools/` | Local maintenance scripts (not run by Netlify) |

`netlify.toml` only holds pretty-URL redirects. Netlify's "Pretty URLs" option rewrites links on the live
site from `awards.html` to `/awards`, so any script that compares links must normalise them first
(see `js/nav.js`).

## After you change data or pages

Requires Python 3 (standard library only). Node is only needed if you rebuild Tailwind.

```sh
python3 tools/build_site_files.py     # regenerate feed.xml + sitemap.xml from data/
python3 tools/seo_head.py             # add any missing canonical / Open Graph / Twitter / favicon tags to new pages
python3 tools/check_site.py           # static checks: meta tags, broken local links, XML well-formed, feed in sync
```

If you add or change Tailwind classes in HTML or JS, rebuild the compiled CSS (Tailwind v3.4.17, the
same version the CDN served):

```sh
npx tailwindcss@3.4.17 -c tools/tailwind.config.js -i tools/tailwind.input.css -o css/tailwind.css --minify
```

To preview locally, serve the repo root over HTTP (the pages fetch `data/*.json`, so `file://` will not
work), for example `python3 -m http.server 8080`.

## Rules the content follows

- Every dollar figure is quoted from its source and links to it. No invented amounts, growth rates,
  price targets, testimonials or user counts.
- Tickers are attached only to verified public recipients. The list is not padded.
- Historical close-to-close returns are shown as history, never as a signal.
