# Local setup

Prereqs: Docker (with the `docker compose` v2+ plugin).

```bash
cp .env.example .env          # then replace each change-me (openssl rand -hex 24)
docker compose up -d
docker compose ps             # both services should be healthy/up
```
- n8n: http://localhost:5678 (create the owner account on first visit)
- Postgres: 127.0.0.1:5432, databases `n8n` and `prospector`

State lives in named volumes `prospector_pgdata` and `prospector_n8n_data`.
`docker compose down` keeps data; `docker compose down -v` DELETES it.
Back up `N8N_ENCRYPTION_KEY`: without it saved n8n credentials are unrecoverable.
The postgres init script runs only on a fresh volume.

## Database schema and credentials
Schema is managed by Flyway (`migrate` service in `compose.yaml`). It runs automatically on `docker compose up`
and applies any new `db/migrations/V<NNN>__<name>.sql` files in order, tracking them in `flyway_schema_history`.
To add a change, create the next numbered file; never edit an applied one. Run by hand with
`docker compose run --rm migrate` (or `... migrate info` for status).

n8n credentials are not in Git. Create/refresh them from `.env` (stack must be running):
```bash
scripts/sync-n8n-credentials.sh
```
This builds the "Prospector Postgres" (id `prospectorPg01`), Google Places and PageSpeed credentials and imports
them with `n8n import:credentials`. Exported workflows reference credentials by id only.
