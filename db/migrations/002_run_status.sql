-- Record every discovery run's outcome, including runs that found nothing usable.
ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'ok';
-- status values: ok | no_results (source returned nothing) | no_valid_records (all records failed validation)
