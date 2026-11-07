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
