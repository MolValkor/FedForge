# Sample pipeline run (local test, 2026-10-07)

Produced by `python3 tools/fetch_awards.py --report-md ...` against the live USAspending.gov API on
2026-10-07 at 9:17 AM EDT (13:17 UTC), window 2026-07-09 to 2026-10-07. SAM.gov was not used (no key).
This file is documentation only; the site does not read it. The data files in this PR are unchanged:
the first nightly workflow run after merge proposes the refreshed data as its own pull request.

## Rows returned per query (Award Amount >= $250,000, domestic, new awards only)

| Query | Rows |
| --- | ---: |
| nuclear: keywords x contracts | 8 |
| nuclear: keywords x grants | 60 |
| nuclear: NAICS x contracts | 0 |
| magnets: keywords x contracts | 7 |
| magnets: keywords x grants | 103 |
| magnets: NAICS x contracts | 5 |
| chips: keywords x contracts | 19 |
| chips: keywords x grants | 241 |
| chips: NAICS x contracts | 3 |

## Run summary

### FedForge award pull: 2026-07-09 to 2026-10-07

Pulled 2026-10-07T13:17:53Z from USAspending.gov (12 API requests). SAM.gov: skipped (SAM_API_KEY not set).

446 raw rows, 430 unique awards, 75 kept (1 with a verified ticker).

| Lane | Qualified | Kept | Kept $ (Award Amount) |
| --- | ---: | ---: | ---: |
| Nuclear / SMRs | 33 | 25 | $104.4M |
| Magnets / rare earths | 87 | 25 | $87.6M |
| Semiconductors / CHIPS | 177 | 25 | $76.5M |

Changed vs current data/awards.json: **yes** (+55 new, -26 dropped)

<details><summary>New awards</summary>

| Date | Lane | Recipient | Amount | Score |
| --- | --- | --- | ---: | ---: |
| 2026-09-23 | magnets | [UNIVERSITY OF TEXAS AT AUSTIN](https://www.usaspending.gov/award/ASST_NON_DEFE0032590_089) | $7.5M | 60 |
| 2026-09-22 | magnets | [GEORGIA TECH RESEARCH CORP](https://www.usaspending.gov/award/ASST_NON_DEFE0032586_089) | $7.5M | 68 |
| 2026-09-21 | magnets | [OHIO UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_DEFE0032716_089) | $2.0M | 61 |
| 2026-09-18 | magnets | [UNIVERSITY OF ILLINOIS](https://www.usaspending.gov/award/ASST_NON_DEFE0032588_089) | $7.5M | 78 |
| 2026-09-18 | chips | [SOUTHERN METHODIST UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_60NANB26D244_013) | $4.2M | 63 |
| 2026-09-18 | chips | [SYRACUSE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_60NANB26D211_013) | $1.0M | 68 |
| 2026-09-17 | nuclear | [DEPARTMENT OF CONSERVATION AND ENERGY, STATE OF LOUISIANA](https://www.usaspending.gov/award/ASST_NON_DENE0009664_089) | $500K | 58 |
| 2026-09-16 | nuclear | [UTAH OFFICE OF ENERGY DEVELOPMENT](https://www.usaspending.gov/award/ASST_NON_DEEE0010692_089) | $1.1M | 53 |
| 2026-09-16 | chips | [RESEARCH FOUNDATION OF THE CITY UNIVERSITY OF NEW YORK](https://www.usaspending.gov/award/ASST_NON_60NANB26D314_013) | $1.0M | 81 |
| 2026-09-15 | magnets | [TEXAS A&M ENGINEERING EXPERIMENT STATION](https://www.usaspending.gov/award/ASST_NON_DEEE0011727_089) | $1.0M | 80 |
| 2026-09-14 | chips | [ARIZONA STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_60NANB26D167_013) | $2.1M | 71 |
| 2026-09-10 | chips | [UNIVERSITY OF DAYTON](https://www.usaspending.gov/award/ASST_NON_60NANB26D300_013) | $1.5M | 88 |
| 2026-09-09 | nuclear | [LEHIGH UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_2641406_049) | $900K | 61 |
| 2026-09-08 | chips | [TEXAS A&M UNIVERSITY-CENTRAL TEXAS](https://www.usaspending.gov/award/ASST_NON_60NANB26D287_013) | $2.0M | 78 |
| 2026-09-05 | nuclear | [ENERGY DELTA LAB](https://www.usaspending.gov/award/ASST_NON_60NANB26D087_013) | $1.4M | 61 |
| 2026-09-03 | magnets | [UNIVERSITY OF WYOMING](https://www.usaspending.gov/award/ASST_NON_DEFE0032589_089) | $7.5M | 68 |
| 2026-08-31 | nuclear | [THE RESEARCH FOUNDATION FOR THE STATE UNIVERSITY OF NEW YORK](https://www.usaspending.gov/award/ASST_NON_DENE0009649_089) | $750K | 91 |
| 2026-08-28 | nuclear | [SIERRA LOBO INC](https://www.usaspending.gov/award/CONT_AWD_80GRC026FA019_8000_80GRC024DA003_8000) | $38.5M | 71 |
| 2026-08-28 | nuclear | [SIERRA LOBO INC](https://www.usaspending.gov/award/CONT_AWD_80GRC026FA018_8000_80GRC024DA003_8000) | $37.2M | 71 |
| 2026-08-27 | nuclear | [VIRGINIA POLYTECHNIC INSTITUTE & STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_60NANB26D190_013) | $1.0M | 76 |
| 2026-08-26 | magnets | [VIRGINIA POLYTECHNIC INSTITUTE & STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_DEFE0032587_089) | $7.5M | 78 |
| 2026-08-26 | chips | [RAGIN' CAJUN FACILITIES, INC.](https://www.usaspending.gov/award/ASST_NON_60NANB26D180_013) | $5.0M | 88 |
| 2026-08-26 | nuclear | [TRANSMUTEX U.S.A., INC.](https://www.usaspending.gov/award/ASST_NON_DEAR0002079_089) | $2.8M | 68 |
| 2026-08-26 | chips | [FLORIDA INTERNATIONAL UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_60NANB26D114_013) | $2.1M | 80 |
| 2026-08-26 | nuclear | [OMEGA P R&D, INC.](https://www.usaspending.gov/award/ASST_NON_DEAR0002087_089) | $1.8M | 68 |
| 2026-08-24 | nuclear | [UNIVERSITY OF MISSOURI SYSTEM](https://www.usaspending.gov/award/ASST_NON_60NANB26D110_013) | $4.2M | 61 |
| 2026-08-24 | chips | [FLORIDA ATLANTIC UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_60NANB26D120_013) | $1.0M | 78 |
| 2026-08-21 | chips | [THE TRUSTEES OF PRINCETON UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_2553633_049) | $6.5M | 71 |
| 2026-08-21 | chips | [MORGAN STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_60NANB26D146_013) | $3.4M | 96 |
| 2026-08-21 | chips | [OREGON STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_60NANB26D162_013) | $2.5M | 88 |
| 2026-08-20 | nuclear | [UNIVERSITY OF TENNESSEE](https://www.usaspending.gov/award/ASST_NON_60NANB26D251_013) | $4.2M | 86 |
| 2026-08-20 | nuclear | [THE PENNSYLVANIA STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_DENE0009647_089) | $463K | 91 |
| 2026-08-19 | magnets | [UNIVERSITY OF HOUSTON SYSTEM](https://www.usaspending.gov/award/ASST_NON_DEAR0002153_089) | $2.9M | 63 |
| 2026-08-19 | chips | [TEXAS A&M ENGINEERING EXPERIMENT STATION](https://www.usaspending.gov/award/ASST_NON_2523110_049) | $1.2M | 60 |
| 2026-08-18 | nuclear | [UNIVERSITY OF TENNESSEE](https://www.usaspending.gov/award/ASST_NON_DEEE0011618_089) | $2.5M | 53 |
| 2026-08-17 | chips | [WEST VIRGINIA UNIVERSITY RESEARCH CORPORATION](https://www.usaspending.gov/award/ASST_NON_2614998_049) | $2.6M | 61 |
| 2026-08-17 | nuclear | [GENERAL ATOMICS](https://www.usaspending.gov/award/ASST_NON_DEAR0002081_089) | $2.6M | 78 |
| 2026-08-17 | chips | [UNIVERSITY OF DELAWARE](https://www.usaspending.gov/award/ASST_NON_2614999_049) | $1.4M | 61 |
| 2026-08-11 | magnets | [UNIVERSITY OF OKLAHOMA](https://www.usaspending.gov/award/ASST_NON_2634532_049) | $1.5M | 76 |
| 2026-08-04 | nuclear | [UNIVERSITY OF TEXAS AT AUSTIN](https://www.usaspending.gov/award/ASST_NON_DENE0009645_089) | $549K | 91 |
| 2026-07-31 | magnets | [RACK-WILDNER & REESE, INC.](https://www.usaspending.gov/award/CONT_AWD_89243426FEE000621_8900_89243423AEE000009_8900) | $1.3M | 60 |
| 2026-07-30 | nuclear | [MASSACHUSETTS INSTITUTE OF TECHNOLOGY](https://www.usaspending.gov/award/ASST_NON_DENE0009641_089) | $500K | 91 |
| 2026-07-30 | nuclear | [CINCINNATI UNIV OF](https://www.usaspending.gov/award/ASST_NON_DENE0009639_089) | $490K | 91 |
| 2026-07-29 | chips | [MASSACHUSETTS INSTITUTE OF TECHNOLOGY](https://www.usaspending.gov/award/ASST_NON_2614673_049) | $3.0M | 61 |
| 2026-07-29 | chips | [THE TRUSTEES OF COLUMBIA UNIVERSITY IN THE CITY OF NEW YORK](https://www.usaspending.gov/award/ASST_NON_2614607_049) | $3.0M | 61 |
| 2026-07-29 | magnets | [MASSACHUSETTS INSTITUTE OF TECHNOLOGY](https://www.usaspending.gov/award/ASST_NON_DEAR0002152_089) | $2.1M | 63 |
| 2026-07-29 | nuclear | [THE PENNSYLVANIA STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_DENE0009640_089) | $400K | 91 |
| 2026-07-24 | chips | [LIGHTFINDER INC.](https://www.usaspending.gov/award/ASST_NON_2537908_049) | $1.2M | 61 |
| 2026-07-23 | nuclear | [TEXAS A&M ENGINEERING EXPERIMENT STATION](https://www.usaspending.gov/award/ASST_NON_DENE0009646_089) | $422K | 91 |
| 2026-07-22 | nuclear | [PURDUE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_DENE0009642_089) | $533K | 91 |
| 2026-07-22 | nuclear | [MISSISSIPPI STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_DENE0009644_089) | $430K | 91 |
| 2026-07-21 | chips | [THE PENNSYLVANIA STATE UNIVERSITY](https://www.usaspending.gov/award/ASST_NON_2607536_049) | $5.5M | 63 |
| 2026-07-20 | nuclear | [IOWA STATE UNIVERSITY OF SCIENCE AND TECHNOLOGY](https://www.usaspending.gov/award/ASST_NON_DENE0009648_089) | $533K | 91 |
| 2026-07-17 | magnets | [THE UNIVERSITY OF CENTRAL FLORIDA BOARD OF TRUSTEES](https://www.usaspending.gov/award/ASST_NON_DEAR0002156_089) | $1.1M | 63 |
| 2026-07-10 | nuclear | [MASSACHUSETTS INSTITUTE OF TECHNOLOGY](https://www.usaspending.gov/award/ASST_NON_2539606_049) | $380K | 66 |

</details>

<details><summary>Dropped awards</summary>

- 2026-09-01 THE PENNSYLVANIA STATE UNIVERSITY (`2535875`): qualified (score 53) but below the top 25 by amount in chips
- 2026-09-01 RARETERRA, INC. (`2604674`): qualified (score 91) but below the top 25 by amount in magnets
- 2026-08-13 IOWA STATE UNIVERSITY OF SCIENCE AND TECHNOLOGY (`DEAR0002178`): qualified (score 53) but below the top 25 by amount in magnets
- 2026-08-11 PMT CRITICAL METALS INC. (`DEAR0002154`): qualified (score 73) but below the top 25 by amount in magnets
- 2026-08-01 THE PENNSYLVANIA STATE UNIVERSITY (`DENE0009629`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-08-01 UNIVERSITY OF UTAH (`DENE0009630`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-08-01 UNIVERSITY OF ILLINOIS (`DENE0009631`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-08-01 MXENE INC (`2537894`): qualified (score 45) but below the top 25 by amount in chips
- 2026-08-01 OSO SEMICONDUCTOR INC. (`2538080`): qualified (score 53) but below the top 25 by amount in chips
- 2026-08-01 UNIVERSITY OF TENNESSEE (`DENE0009598`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-08-01 NORTH CAROLINA STATE UNIVERSITY (`DENE0009616`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-08-01 BOISE STATE UNIVERSITY (`DENE0009611`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-08-01 VIRGINIA POLYTECHNIC INSTITUTE & STATE UNIVERSITY (`DEEE0011724`): qualified (score 60) but below the top 25 by amount in magnets
- 2026-08-01 FREE FORM FIBERS L.L.C. (`DEEE0011723`): qualified (score 65) but below the top 25 by amount in chips
- 2026-07-31 CAMECA INSTRUMENTS, INC (`1333ND26PNB680225`): qualified (score 58) but below the top 25 by amount in chips
- 2026-07-30 UNITED SEMICONDUCTORS, LLC (`80JSC026C0007`): qualified (score 50) but below the top 25 by amount in chips
- 2026-07-30 EDWARDS SEMICONDUCTOR SOLUTIONS LLC (`1333ND26PNB680185`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-07-22 MASSACHUSETTS INSTITUTE OF TECHNOLOGY (`DEAR0002159`): qualified (score 45) but below the top 25 by amount in magnets
- 2026-07-21 MOSAIC MICROSYSTEMS LLC (`1333ND26PNB030260`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-07-20 TEXAS A&M ENGINEERING EXPERIMENT STATION (`DEAR0002170`): qualified (score 53) but below the top 25 by amount in magnets
- 2026-07-07 GOVERNMENT SCIENTIFIC SOURCE INC (`1333ND26FNB030141`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-07-06 AMERICAN CENTRIFUGE OPERATING, LLC (`89243226FNE400212`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-07-02 REGENTS OF THE UNIVERSITY OF CALIFORNIA, THE (`DENA0004277`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-07-01 UNIVERSITY OF ARKANSAS (`W911NF262A096`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-07-01 MICHIGAN TECHNOLOGICAL UNIVERSITY (`2529953`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)
- 2026-06-29 GLOBAL LASER ENRICHMENT LLC (`DENE0009559`): not a new award inside 2026-07-09..2026-10-07 (aged out of the rolling window or not matched by the lane queries)

</details>
