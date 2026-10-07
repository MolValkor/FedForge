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
| `private-capital.html`, `data/private-capital.json` | Private capital section: company money going into facilities the federal government relies on (shipyards, rocket motors, drones, nuclear fuel, magnets, chips, launch). Rendered by `js/private-capital.js` |
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
                                      # (also runs tools/check_private_capital.py)
python3 -m unittest discover -s tests # data-rule tests for the private capital section
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

## Private capital section

`data/private-capital.json` lists private-company investments in U.S. facilities the federal government will
benefit from. Rules, enforced by `tools/check_private_capital.py` (run on its own or via `check_site.py`):

- every entry has at least one https source, and every amount, status, ticker, listing note and federal link
  points to one of that entry's sources
- `date` is a real `YYYY-MM-DD` inside `window` and not after `reviewed`
- `amount_usd` only with an `amount_source_url`; otherwise `amount_display` must say "Undisclosed" / "Not stated"
- no percentages in amount text; tickers only on `"ownership": "public"` entries, each with `ticker_source_url`
- `lane` is one of the site's sector keys (`nuclear`, `magnets`, `chips`, `other`)

To add an entry, copy an existing one, fill every field from the source, bump `reviewed`, then run
`python3 tools/check_site.py` and `python3 -m unittest discover -s tests`.
