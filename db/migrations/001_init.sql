-- Prospect store. Applied manually for now (see docs/SETUP.md); a migration runner comes later.
-- NOTE: columns beyond place_id are provisional until Google Places storage terms are verified.
CREATE TABLE IF NOT EXISTS prospects (
  id               BIGSERIAL PRIMARY KEY,
  place_id         TEXT NOT NULL UNIQUE,          -- Google Place ID, dedupe key
  name             TEXT NOT NULL,
  category         TEXT,
  address          TEXT,
  website_url      TEXT,
  phone            TEXT,
  source_query     TEXT,
  status           TEXT NOT NULL DEFAULT 'discovered',
  discovered_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS discovery_runs (
  id               BIGSERIAL PRIMARY KEY,
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  n8n_execution_id TEXT,
  params           JSONB NOT NULL,
  fetched          INT NOT NULL,
  invalid          INT NOT NULL,
  inserted         INT NOT NULL,
  duplicates       INT NOT NULL
);
