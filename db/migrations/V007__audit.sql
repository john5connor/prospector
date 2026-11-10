-- Audit stage (spec 4.3 / 6): one audit_run per prospect+kind, normalized findings per run.
CREATE TABLE IF NOT EXISTS audit_runs (
  id               BIGSERIAL PRIMARY KEY,
  prospect_id      BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
  kind             TEXT NOT NULL,                 -- 'pagespeed' (later: 'browser', 'http')
  strategy         TEXT,                          -- 'mobile' | 'desktop'
  url              TEXT NOT NULL,
  ran_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  status           TEXT NOT NULL CHECK (status IN ('ok','error')),
  scores           JSONB,                         -- {performance, seo, accessibility, best_practices} as 0-100
  metrics          JSONB,                         -- {lcp_ms, cls, tbt_ms, fcp_ms}
  error            TEXT,
  n8n_execution_id TEXT
);
CREATE INDEX IF NOT EXISTS audit_runs_prospect_kind_idx ON audit_runs (prospect_id, kind, ran_at DESC);

CREATE TABLE IF NOT EXISTS findings (
  id                   BIGSERIAL PRIMARY KEY,
  audit_run_id         BIGINT NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
  check_name           TEXT NOT NULL,
  severity             TEXT NOT NULL CHECK (severity IN ('high','medium','low')),
  evidence             TEXT,
  business_impact_text TEXT NOT NULL,
  screenshot_ref       TEXT
);
CREATE INDEX IF NOT EXISTS findings_run_idx ON findings (audit_run_id);
