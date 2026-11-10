-- Count paid Places API requests per discovery run (mock runs log 0).
ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS requests_made INT NOT NULL DEFAULT 0;
