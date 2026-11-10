-- Crawl policy enforcement (docs/CRAWL_POLICY.md section 7), used by src/prospector/crawl.py.
-- Blocklist entries match the domain and all its subdomains (example.com blocks www.example.com).
CREATE TABLE IF NOT EXISTS crawl_blocklist (
  domain   TEXT PRIMARY KEY CHECK (domain = lower(domain) AND domain !~ '[/:@\s]'),
  reason   TEXT NOT NULL,                       -- e.g. 'opt-out email 2026-11-08'
  added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per request attempt or refusal. This is the audit trail.
CREATE TABLE IF NOT EXISTS crawl_fetch_log (
  id              BIGSERIAL PRIMARY KEY,
  run_id          TEXT,
  site            TEXT NOT NULL,                -- site key, e.g. example.com
  url             TEXT NOT NULL,
  kind            TEXT NOT NULL CHECK (kind IN ('robots','page')),
  status          INT,                          -- HTTP status; NULL for refusals and network errors
  bytes           INT NOT NULL DEFAULT 0,
  duration_ms     INT NOT NULL DEFAULT 0,
  robots_decision TEXT NOT NULL CHECK (robots_decision IN ('allowed','disallowed','n/a')),
  outcome         TEXT NOT NULL,                -- ok | truncated | too_large | error | refused:<reason>
  error           TEXT,
  fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS crawl_fetch_log_site_idx ON crawl_fetch_log (site, fetched_at DESC);
