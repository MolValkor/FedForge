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
| `tools/fetch_awards.py`, `tools/pipeline/lanes.json` | Automated award pipeline (see below) |
| `tools/pipeline/nightly-awards.yml` | Nightly job definition; move to `.github/workflows/` to enable (see below) |

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

## Automated award pipeline (new primes)

`data/awards.json` (and its baked copy `js/awards-data.js`) is produced by `tools/fetch_awards.py`
(Python 3, standard library only):

1. **Fetch.** For each lane in `tools/pipeline/lanes.json` (nuclear / SMRs, magnets / rare earths,
   semiconductors / CHIPS) it queries the public USAspending.gov `spending_by_award` API three ways:
   lane keywords x contracts (A-D), lane keywords x grants (02-05), lane NAICS codes x contracts.
   Window: the last 90 days of *new* awards, domestic recipients, prime awards, Award Amount >= $250,000.
   Every result page is followed.
2. **Dedupe** on USAspending's `generated_internal_id`.
3. **Score** each award 0-100 per lane from its own description and recipient (strong / weak lane terms,
   with masks for look-alikes such as "nuclear magnetic resonance", "mitochondrial fission" or "wood chips"),
   a bonus when the lane term is in the title / lead sentence, NAICS match, awarding agency and amount.
   NAICS / agency / amount alone never qualify an award. Keep it under its best lane if score >= 45.
4. **Cap** each lane at 25: core awards (score >= 60) first, largest dollars first.
5. **Tickers** are attached only when the award id or the exact recipient name already carries a
   human-verified ticker in `data/*.json`. The pipeline never guesses or adds tickers.
6. **Write** `data/awards.json`, `js/awards-data.js` and stamp `data/meta.json`
   (`last_usaspending_pull`, `primes_count`, `primes_window`). All amounts, dates, names and descriptions
   are copied from the API response. `date` is the base obligation (award) date.

```sh
python3 tools/fetch_awards.py --dry-run               # fetch + print the run summary, write nothing
python3 tools/fetch_awards.py                         # rewrite the data files
python3 tools/fetch_awards.py --days 120 --per-lane 30 --min-amount 500000
```

Tune lanes, terms and weights in `tools/pipeline/lanes.json`; no code change is needed. A sample run is in
`tools/pipeline/SAMPLE_RUN.md`.

### Nightly job (`tools/pipeline/nightly-awards.yml`)

**One-time install:** move the file to `.github/workflows/nightly-awards.yml`. GitHub only runs workflows from
that folder, and the token that opened the pipeline PR did not have GitHub's `workflow` scope, so it could not
add the file there itself. Either `git mv tools/pipeline/nightly-awards.yml .github/workflows/nightly-awards.yml`
and push, or on github.com use Add file > Create new file, name it `.github/workflows/nightly-awards.yml`, and
paste the contents (delete the first two INSTALL comment lines if you like).

Runs every day at 10:23 UTC (6:23 AM EDT) and on demand (Actions tab > Nightly award refresh > Run workflow).
It runs the unit tests first and the data-quality gate before and after writing (see below).
If the award list changed it regenerates `feed.xml` / `sitemap.xml`, runs `tools/check_site.py`, force-pushes
the result to the `bot/award-refresh` branch and opens (or updates) a pull request into `main`.

- **It never pushes to `main`.** Nothing reaches thefedforge.com until a human merges the PR, so Netlify only
  builds production when you choose to.
- Netlify cost: Deploy Previews for the bot PR are free on credit-based plans; each merge into `main` is one
  production deploy (15 credits). The bot branch is rebuilt from `main` nightly, so you can let the PR sit and
  merge it weekly instead of nightly.
- The bot branch is rebuilt from `main` each night; do not hand-edit it (edit `main` instead).
- For the job to open the PR itself, enable **Settings > Actions > General > Workflow permissions >
  "Allow GitHub Actions to create and approve pull requests"**. Without it the job still pushes the branch and
  prints a one-click compare link in the run summary.

### Optional: SAM.gov

Set a repository secret named `SAM_API_KEY` (Settings > Secrets and variables > Actions > New repository
secret) to also query the SAM.gov Contract Awards API for base contracts in each lane's NAICS codes.
Get the key at https://sam.gov/profile/details ("Public API Key"; a free SAM.gov account is enough).
A personal key without a SAM.gov role is limited to 10 requests a day, so the pipeline makes at most
3 (`SAM_MAX_REQUESTS`). SAM.gov rows only fill in contracts USAspending has not loaded yet and are labelled
"obligated (SAM.gov)". Without the secret the pipeline runs on USAspending alone. Locally:
`SAM_API_KEY=... python3 tools/fetch_awards.py --dry-run`.

### Tests and data-quality gate

**Unit tests** (`tests/`, pytest) cover `tools/fetch_awards.py` and the gate: API response parsing, paging,
lane matching (including the look-alike masks), dedup, per-lane caps, verified-only tickers and the exact output
shape. They replay recorded USAspending responses from `tests/fixtures/` and never touch the network.

```sh
python3 -m pip install -r requirements-dev.txt   # pytest only; the pipeline itself stays stdlib-only
python3 -m pytest -q
```

**Data-quality gate** (`tools/pipeline/validate_awards.py`). `fetch_awards.py` runs it on the new data *before*
writing anything; if it fails, the script writes nothing and exits 3. The nightly job runs it again on the
written files against `main`'s copy. It fails on:

- schema problems: missing or unknown fields (so no invented growth %, returns or price targets can slip in),
  `count` not matching the rows, or a bad window
- amounts that are not positive numbers, are below the run's `min_amount`, or are above the $50B sanity cap
- dates that are not real `YYYY-MM-DD` dates or fall after the window end or in the future
- duplicate award ids, or links that are not USAspending award pages
- tickers that are not already human-verified in `data/*.json`, or `public` not matching "has a ticker"
- a row-count swing vs the previous snapshot over the limits in `lanes.json` > `quality` (default: more than a
  50% drop or a 100% rise, ignoring changes of 10 rows or fewer), or a lane that had 5+ rows going to zero
- `data/meta.json` or `js/awards-data.js` disagreeing with `data/awards.json`

Blank recipient, agency or description text is left blank and listed as a warning; it is never filled in.

```sh
python3 tools/pipeline/validate_awards.py data/awards.json --previous data/awards.json \
    --meta data/meta.json --js js/awards-data.js
```

In the nightly job a failure turns the run red (GitHub emails the repo owner), prints the reasons in the run
summary, and opens or updates **no** data PR. If a big count change is intended (for example after editing
lanes), run the workflow by hand with **allow_count_change** ticked, or pass `--allow-count-change` locally.
That skips only the row-count check; every other check still runs.

## Rules the content follows

- Every dollar figure is quoted from its source and links to it. No invented amounts, growth rates,
  price targets, testimonials or user counts.
- Tickers are attached only to verified public recipients. The list is not padded.
- Historical close-to-close returns are shown as history, never as a signal.
