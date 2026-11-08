-- Qualification (spec 4.2): real problem AND ability to pay. Logic lives in one SQL function so it is
-- versioned, testable with psql, and tunable by editing the constants at the top of the function.
CREATE TABLE IF NOT EXISTS qualifications (
  prospect_id   BIGINT PRIMARY KEY REFERENCES prospects(id) ON DELETE CASCADE,
  score         INT NOT NULL,
  ability_score INT NOT NULL,   -- reviews + rating (0-35)
  problem_score INT NOT NULL,   -- no website / audit findings (0-60)
  qualified     BOOLEAN NOT NULL,
  reason_codes  TEXT[] NOT NULL,
  rule_version  INT NOT NULL,
  evaluated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION qualify_prospects() RETURNS SETOF qualifications AS $$
DECLARE
  v_rule_version CONSTANT INT := 1;
  v_threshold    CONSTANT INT := 50;   -- minimum total score
  v_min_ability  CONSTANT INT := 15;   -- gate: must look able to pay (>= ~50 reviews)
  v_min_problem  CONSTANT INT := 8;    -- gate: must have a real problem (one medium finding or no site)
BEGIN
  RETURN QUERY
  WITH latest AS (
    SELECT DISTINCT ON (prospect_id) id, prospect_id
    FROM audit_runs WHERE kind = 'pagespeed' AND status = 'ok'
    ORDER BY prospect_id, ran_at DESC
  ), fc AS (
    SELECT l.prospect_id,
      count(*) FILTER (WHERE f.severity = 'high')   AS hi,
      count(*) FILTER (WHERE f.severity = 'medium') AS med,
      count(*) FILTER (WHERE f.severity = 'low')    AS lo,
      array_agg('finding:' || f.check_name || ':' || f.severity ORDER BY f.id) AS codes
    FROM latest l JOIN findings f ON f.audit_run_id = l.id GROUP BY l.prospect_id
  ), s AS (
    SELECT p.id,
      (CASE WHEN p.review_count >= 200 THEN 25 WHEN p.review_count >= 100 THEN 20
            WHEN p.review_count >= 50 THEN 15 WHEN p.review_count >= 20 THEN 8 ELSE 0 END
       + CASE WHEN p.rating >= 4.5 THEN 10 WHEN p.rating >= 4.0 THEN 5 ELSE 0 END) AS ability,
      LEAST(60, CASE WHEN COALESCE(p.website_url,'') = '' THEN 40 ELSE 0 END
                + 20 * COALESCE(fc.hi,0) + 8 * COALESCE(fc.med,0) + 2 * COALESCE(fc.lo,0)) AS problem,
      (l.id IS NOT NULL) AS audited,
      (COALESCE(p.website_url,'') = '') AS no_site,
      p.review_count, p.rating, fc.codes
    FROM prospects p
    LEFT JOIN latest l ON l.prospect_id = p.id
    LEFT JOIN fc ON fc.prospect_id = p.id
    WHERE p.source <> 'mock'
  )
  INSERT INTO qualifications AS q (prospect_id, score, ability_score, problem_score, qualified, reason_codes, rule_version, evaluated_at)
  SELECT s.id, s.ability + s.problem, s.ability, s.problem,
         (s.ability >= v_min_ability AND s.problem >= v_min_problem AND s.ability + s.problem >= v_threshold
          AND (s.audited OR s.no_site)),
         array_remove(ARRAY[
           CASE WHEN s.no_site THEN 'no_website' END,
           CASE WHEN NOT s.audited AND NOT s.no_site THEN 'not_audited' END,
           CASE WHEN s.review_count IS NULL THEN 'no_review_data'
                WHEN s.review_count >= 200 THEN 'reviews_200_plus' WHEN s.review_count >= 100 THEN 'reviews_100_plus'
                WHEN s.review_count >= 50 THEN 'reviews_50_plus' ELSE 'reviews_under_50' END,
           CASE WHEN s.rating >= 4.5 THEN 'rating_4_5_plus' WHEN s.rating >= 4.0 THEN 'rating_4_plus' END
         ], NULL) || COALESCE(s.codes, ARRAY[]::text[]),
         v_rule_version, now()
  FROM s
  ON CONFLICT (prospect_id) DO UPDATE
    SET score = EXCLUDED.score, ability_score = EXCLUDED.ability_score, problem_score = EXCLUDED.problem_score,
        qualified = EXCLUDED.qualified, reason_codes = EXCLUDED.reason_codes,
        rule_version = EXCLUDED.rule_version, evaluated_at = EXCLUDED.evaluated_at
  RETURNING q.*;
END $$ LANGUAGE plpgsql;
