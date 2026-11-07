#!/bin/bash
# Create/refresh n8n credentials from .env via the n8n CLI. Secrets never touch Git.
# Usage: scripts/sync-n8n-credentials.sh   (stack must be running)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
TMP=$(mktemp); trap 'rm -f "$TMP"' EXIT; chmod 600 "$TMP"
python3 -I - "$TMP" <<'PY'
import json, os, sys
key = os.environ.get("GOOGLE_PLACES_API_KEY") or "PLACEHOLDER-set-GOOGLE_PLACES_API_KEY-in-.env"
creds = [
  {"id": "prospectorPg01", "name": "Prospector Postgres", "type": "postgres",
   "data": {"host": "postgres", "port": 5432, "database": os.environ["PROSPECTOR_DB"],
            "user": os.environ["POSTGRES_USER"], "password": os.environ["POSTGRES_PASSWORD"],
            "ssl": "disable", "allowUnauthorizedCerts": False, "maxConnections": 10}},
  {"id": "placesApiKey01", "name": "Google Places API Key", "type": "httpHeaderAuth",
   "data": {"name": "X-Goog-Api-Key", "value": key}},
]
json.dump(creds, open(sys.argv[1], "w"))
PY
docker compose cp "$TMP" n8n:/tmp/creds.json
docker compose exec -T -u node n8n n8n import:credentials --input=/tmp/creds.json
docker compose exec -T n8n rm -f /tmp/creds.json
[ -n "${GOOGLE_PLACES_API_KEY:-}" ] || echo "NOTE: GOOGLE_PLACES_API_KEY is empty; Places credential holds a placeholder."
