-- Mark whether a discovery run's requests hit the real (billable) Places API.
-- Runs 7-9 were tests against tests/stub_places_server.py and never reached Google.
ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS billable BOOLEAN NOT NULL DEFAULT true;
UPDATE discovery_runs SET billable = false WHERE id IN (7, 8, 9) AND params->>'source' = 'places';
UPDATE discovery_runs SET billable = false WHERE requests_made = 0;
