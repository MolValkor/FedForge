# Test fixtures (recorded API responses)

The tests never touch the network (`tests/conftest.py` blocks sockets). These files stand in for the APIs:

| File | What it is |
| --- | --- |
| `usaspending_contracts_page1.json` | Real USAspending `spending_by_award` response, recorded 2026-10-07: contracts A-D, window 2026-07-09..2026-10-07, keywords nuclear fuel / enriched uranium / rare earth / semiconductor, `limit` 6, page 1 (`hasNext: true` as recorded). |
| `usaspending_contracts_page2.json` | Page 2 of the same query. One sole-proprietor row (a person's name) was removed and `hasNext` set to `false` so the recording ends here. |
| `usaspending_grants_page1.json` | Same window, grants 02-05, keywords nuclear energy / rare earth / semiconductor, page 1 (`hasNext` set to `false`). |
| `usaspending_nuclear_grants.json` | Five DOE nuclear grants rebuilt in the API's response shape from rows already published in `data/awards.json` (the 2026-09-01 pull). Used because the recorded window had no nuclear contracts. |

Only the `messages` banner was dropped from the recordings; every amount, date, name and description is as the
API returned it. To refresh, re-run the same POST bodies (see `tools/fetch_awards.py` `usa_query`).
