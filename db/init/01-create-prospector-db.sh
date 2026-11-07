#!/bin/bash
# Runs once, on first initialization of the postgres volume only.
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -c "CREATE DATABASE \"${PROSPECTOR_DB}\""
