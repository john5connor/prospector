-- Multi-source prospects. prospects.id is the stable internal prospect ID; place_id is just
-- one source's identifier. Source records link to a prospect through prospect_sources.

-- 1. place_id is Google-specific: allow rows that never came from Google (still unique when set).
ALTER TABLE prospects ALTER COLUMN place_id DROP NOT NULL;

-- 2. Google rating data (Overture has none). Collected with the Places scan, same SKU tier as phone/website.
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS rating NUMERIC(2,1);
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS review_count INT;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS ratings_collected_at TIMESTAMPTZ;

-- 3. Normalized match keys (generated, indexed, non-unique: used to FIND candidates, never to merge blindly).
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS phone_norm TEXT
  GENERATED ALWAYS AS (NULLIF(right(regexp_replace(COALESCE(phone,''), '\D', '', 'g'), 10), '')) STORED;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS domain_norm TEXT
  GENERATED ALWAYS AS (NULLIF(lower(regexp_replace(regexp_replace(COALESCE(website_url,''), '^https?://(www\.)?', ''), '[/?#].*$', '')), '')) STORED;
CREATE INDEX IF NOT EXISTS prospects_phone_norm_idx ON prospects (phone_norm);
CREATE INDEX IF NOT EXISTS prospects_domain_norm_idx ON prospects (domain_norm);

-- 4. One row per (source, record). Idempotent re-imports hit the unique constraint.
CREATE TABLE IF NOT EXISTS prospect_sources (
  id               BIGSERIAL PRIMARY KEY,
  prospect_id      BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
  source           TEXT NOT NULL,
  source_record_id TEXT NOT NULL,
  source_url       TEXT,
  collected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source, source_record_id)
);
CREATE INDEX IF NOT EXISTS prospect_sources_prospect_idx ON prospect_sources (prospect_id);

INSERT INTO prospect_sources (prospect_id, source, source_record_id, source_url, collected_at)
SELECT id, source, COALESCE(source_record_id, place_id), source_url, collected_at
FROM prospects
WHERE COALESCE(source_record_id, place_id) IS NOT NULL
ON CONFLICT (source, source_record_id) DO NOTHING;

-- Keep the invariant "every prospect has its originating source row" without touching the workflow.
CREATE OR REPLACE FUNCTION prospects_record_source() RETURNS trigger AS $$
BEGIN
  IF COALESCE(NEW.source_record_id, NEW.place_id) IS NOT NULL THEN
    INSERT INTO prospect_sources (prospect_id, source, source_record_id, source_url, collected_at)
    VALUES (NEW.id, NEW.source, COALESCE(NEW.source_record_id, NEW.place_id), NEW.source_url, NEW.collected_at)
    ON CONFLICT (source, source_record_id) DO NOTHING;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS prospects_record_source_trg ON prospects;
CREATE TRIGGER prospects_record_source_trg AFTER INSERT ON prospects
  FOR EACH ROW EXECUTE FUNCTION prospects_record_source();

-- 5. Ambiguous matches wait here for a human decision; nothing is auto-merged on a weak signal.
CREATE TABLE IF NOT EXISTS prospect_match_candidates (
  id            BIGSERIAL PRIMARY KEY,
  prospect_a_id BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
  prospect_b_id BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
  signals       JSONB NOT NULL,                       -- e.g. {"phone":true,"name_zip":false,"domain_street":false}
  status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','merged','distinct')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at    TIMESTAMPTZ,
  CHECK (prospect_a_id < prospect_b_id),
  UNIQUE (prospect_a_id, prospect_b_id)
);
