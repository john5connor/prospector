# Google Places API (New): terms, storage, pricing (researched 2026-11-07)

Sources: official developers.google.com pages only. The Service Specific Terms pages (cloud.google.com/maps-platform/terms)
could not be read, so anything that depends on their exact wording is UNVERIFIED. Not legal advice; the Places policies
page itself says to consult counsel.

## Storage and caching
- **place_id: storable indefinitely** ("exempt from the caching restrictions"). Refresh IDs older than 12 months; a
  Place Details call with `fields=id` is free (Essentials IDs Only). Obsolete IDs return NOT_FOUND.
- **Latitude/longitude: cache up to 30 consecutive days**, then delete.
- **Name, address, phone, website, rating, review count: no permitted storage period found** in readable pages.
  The policies page says not to "export, extract, or scrape Google Maps Content for use outside the Services",
  nor "pre-fetch, index, store, or redistribute" it, and lists "copy and save business names, addresses, or user
  reviews" as an example. Treat persistent storage of these as NOT permitted until verified.
- "Lead generation / prospect database" is not named explicitly in readable text. UNVERIFIED either way.
- Deriving content from Places lat/lng (e.g. point-in-polygon analysis) is listed as prohibited.

Implication: the current `prospects` columns (name, address, phone, website_url) are the questionable part.
Safe-by-the-text design: persist `place_id` (+ our own derived data, status, audit results), and fetch display fields
fresh when needed. Needs a decision, see below.

## Pricing, Text Search (New), per 1,000 requests (first tier)
Billed at the highest SKU among requested fields.
| Tier | Fields (examples) | Free/month | Price |
|---|---|---|---|
| Essentials (IDs Only) | id, name | unlimited | free |
| Pro | displayName, formattedAddress, primaryType, businessStatus, location, types | 5,000 | $32.00 |
| Enterprise | nationalPhoneNumber, websiteUri, rating, userRatingCount, regularOpeningHours | 1,000 | $35.00 |
| Enterprise + Atmosphere | reviews, editorialSummary, ... | 1,000 | $40.00 |

## Limits
- pageSize 1-20; max 60 results per query across pages (nextPageToken). Phone/website come back from Text Search
  directly if in the field mask (Enterprise rate); no Place Details needed.
- A 60-result query costs up to 3 requests. 15-20 businesses x 3 industries is about 3-9 requests: negligible.

## Spend controls
- Per-day quota per API method in Cloud Console (Maps Platform > Quotas). Suggested: free cap / 31.
- Quotas and budgets do NOT hard-cap spend; budgets only alert. A low daily quota is the real brake.
- Restrict the key: API restriction to Places API (New) plus IP restriction (server-side). Keep it out of Git.
- You are financially responsible for abuse of unrestricted keys.
