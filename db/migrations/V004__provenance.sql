-- Provenance for every prospect row, so sources are swappable and auditable.
-- source: where the row came from (mock | google_places | overture | ...)
-- source_record_id: the record's id inside that source (place_id, Overture GERS id, ...)
-- source_url: page the data was observed on, when applicable (NULL for APIs/bulk files)
-- collected_at: when this system observed it
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS source_record_id TEXT;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS collected_at TIMESTAMPTZ;
-- Existing rows are all mock rows (stub rows were deleted).
UPDATE prospects SET source = 'mock', source_record_id = place_id, collected_at = discovered_at WHERE source IS NULL;
ALTER TABLE prospects ALTER COLUMN source SET NOT NULL;      -- no default: writers must say where data came from
ALTER TABLE prospects ALTER COLUMN collected_at SET NOT NULL;
ALTER TABLE prospects ALTER COLUMN collected_at SET DEFAULT now();
