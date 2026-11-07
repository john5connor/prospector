# Workflow export / import

Git is the source of truth for workflow definitions. n8n stores them in Postgres, so export explicitly.

```bash
# export one workflow (writes into ./workflows via the bind mount)
docker compose exec -T -u node n8n n8n export:workflow --id=<ID> --output=/workflows/<name>.json --pretty
# import (same ID => overwrites, no duplicate; imported workflows are INACTIVE by default)
docker compose exec -T -u node n8n n8n import:workflow --input=/workflows/<name>.json
```
Verified 2026-11-07 (n8n 2.47.2): export, then re-import, left exactly one workflow with the same ID.
Exports contain no secrets (credentials are referenced by ID only, never exported here). Exports include
`createdAt`/`updatedAt`, so diffs will show timestamp noise.

## MCP notes
- Claude Code connects through the `n8n-skills` plugin (`plugin:n8n-skills:n8n-mcp`), OAuth; no token on disk.
- Instance MCP is enabled via `N8N_MCP_MANAGED_BY_ENV` / `N8N_MCP_ACCESS_ENABLED` in `compose.yaml`.
- Workflows created via MCP showed `availableInMCP: true` (exposed to MCP clients by default here).
- Smoke test: `workflows/mcp-smoke-test.json` built via `create_workflow_from_code`, run via `execute_workflow`.
