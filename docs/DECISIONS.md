# Decisions

| # | Decision | Status | Notes |
|---|---|---|---|
| 1 | Repo at `~/workspace/prospector` (renamed from `autonomous/`) | Decided | Reference docs in `docs/reference/` |
| 2 | Postgres 17 for both n8n internals and the prospect store | Decided | One container, two databases (`n8n`, `prospector`) |
| 3 | Pinned images: n8n 2.47.2, postgres 17.11 | Decided | Bump deliberately, not via `latest` |
| 4 | Compose v5.7.0 installed as user plugin (`~/.docker/cli-plugins`) | Decided | Standalone `docker-compose` 2.16 is incompatible with Docker 29 (API 1.42 < 1.44) |
| 5 | Ports bound to 127.0.0.1 only | Decided | Dev stack not exposed on network/tailnet |
| 6 | Instance-level MCP enabled by env; Claude Code uses official `n8n-io/skills` plugin (OAuth) | Decided | See docs/WORKFLOWS.md |
| 7 | MVP persists Google Places fields (name, address, phone, website) in `prospects` | Decided, KNOWN RISK | Owner's call, 2026-11-07. Standard terms likely do not permit durable storage of these fields (see docs/research/places-terms-and-pricing.md). Revisit before any scale-up, export or outreach built on stored Google data. Pivot path: keep only `place_id` + own data, fetch fields fresh |
| 8 | Discovery first, template later | Decided | Overrides spec §10 |
| 9 | Provenance columns on `prospects` (source, source_record_id, source_url, collected_at); Overture Places piloted as primary discovery source candidate | Decided (columns) / Pilot only (Overture) | Migration 004. Overture rows are NOT imported yet: `prospects.place_id` is Google-specific and NOT NULL, so choosing the dedupe key for multi-source rows is an open decision. See docs/research/overture-pilot.md |

## Open
- Written clarification from Google on prospecting use / durable storage (unverified; needed before scaling).
- Credential handling in export/import (no credentials exist yet).
- Whether to keep `availableInMCP` default exposure for production-bound workflows.
