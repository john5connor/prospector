# Decisions

| # | Decision | Status | Notes |
|---|---|---|---|
| 1 | Repo at `~/workspace/prospector` (renamed from `autonomous/`) | Decided | Reference docs in `docs/reference/` |
| 2 | Postgres 17 for both n8n internals and the prospect store | Decided | One container, two databases (`n8n`, `prospector`) |
| 3 | Pinned images: n8n 2.47.2, postgres 17.11 | Decided | Bump deliberately, not via `latest` |
| 4 | Compose v5.7.0 installed as user plugin (`~/.docker/cli-plugins`) | Decided | Standalone `docker-compose` 2.16 is incompatible with Docker 29 (API 1.42 < 1.44) |
| 5 | Ports bound to 127.0.0.1 only | Decided | Dev stack not exposed on network/tailnet |
| 6 | Discovery first, template later | Decided | Overrides spec §10 |

## Open
- Which Google Places fields may be persisted (verify before schema work).
- n8n MCP setup and operations (Phase B).
- Workflow export/import procedure and credential handling.
