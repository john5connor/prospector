-- Report (spec 4.4): one per prospect; token is the unguessable path segment. url stays NULL until hosted.
CREATE TABLE IF NOT EXISTS reports (
  prospect_id  BIGINT PRIMARY KEY REFERENCES prospects(id) ON DELETE CASCADE,
  token        TEXT NOT NULL UNIQUE,
  finding_ids  BIGINT[] NOT NULL,
  audit_run_id BIGINT NOT NULL REFERENCES audit_runs(id),
  local_path   TEXT NOT NULL,
  url          TEXT,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
