# Overture Places pilot (2026-11-07)

Release `2026-10-21.0` (latest per the STAC catalog). Counties: Oakland, Wayne, Genesee, Livingston (MI), selected by point-in-polygon against Overture's own county polygons. Categories (Overture `taxonomy.primary`): `hvac_service`, `plumbing`, `roofing`. Reproduce with `scripts/overture_pilot.py`. Data stays in `data/` (gitignored). No requests were made to any business website.

Docs: the `categories` field no longer exists in the Places schema; use `taxonomy.primary` / `basic_category`. Places theme is CDLA-Permissive-2.0 / Apache-2.0 (per Overture docs as read by a subagent); keep attribution notices per `/attribution/` when we ingest.

## Results

| Measure | Value |
|---|---|
| All places in the four counties | ~186,000 |
| Pilot categories (3) | 1,383 rows (HVAC 518, roofing 440, plumbing 425) |
| After strict dedupe (same phone, or name+ZIP, or domain+street) | 1,316 |
| `confidence >= 0.7` and not permanently closed | 1,027 rows / 990 clusters |
| `permanently_closed` | 29 |
| Confidence buckets | >=0.9: 888, 0.7-0.9: 156, 0.5-0.7: 130, <0.5: 209 |

Per county (rows): Oakland 600, Wayne 511, Genesee 147, Livingston 125.

Field coverage (of 1,383): website 1,244 (90%), phone 1,365 (99%), street address 1,366, social links 521, **email 423 (31%)**, brand 27.
Businesses with no website at all: 139; of those 55 have social links only. Only 6 "websites" are aggregator/social pages.

Source datasets feeding these rows (a row can have several): BrightQuery 606, meta 476, Microsoft 403, Foursquare 79, Uberall 20, DAC 6, AllThePlaces 6.

## Findings

- Coverage for these trades is workable: ~1,000 plausible businesses across four counties, ~990 after dedupe.
- Website coverage is high, so most prospects can go straight to the audit stage. The ~136 with no real website are the strongest "clear problem" group (but "no website field" does not prove no website).
- Overture has no rating, review count or hours. The spec's qualification signals (review count/rating) are NOT available here; that is where a narrow Places lookup on the shortlist would fit.
- Email is sparse (31%). Contact extraction from business sites is still required.
- Quality noise exists: suppliers/chains show up under these categories (example in the sample: a building-products supplier under `roofing`), franchises share domains (e.g. Roto-Rooter 12 rows), 119 domain groups appear on more than one row. Multi-signal dedupe is needed, not name alone.
- `confidence` is existence-only, not a quality measure; >=0.7 removes ~25% of rows.

## NOT measured (needs a human)

Real-world accuracy: is the business still operating, does the website work, is the category right. `data/manual_review_sample.csv` has 30 random records (confidence >= 0.7, one per dedupe cluster) with blank columns to fill in. Website liveness was deliberately not probed automatically (robots/terms/rate-limit policy not decided yet).
