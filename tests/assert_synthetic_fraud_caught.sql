-- For each of the 5 embedded fraud scenarios, assert the MAX composite score
-- across the scenario's track set hits the expected_min_score from
-- precache/fraud_scenarios/<scenario>.json (loaded via the
-- fraud_scenario_expectations seed).
--
-- Any failing scenario means either:
--   (a) the signals are mis-tuned (fix the YAML), or
--   (b) the synthetic fraud generator drifted (fix the generator).
--
-- This is the contract that justifies the Detection Lab page existing.

WITH joined AS (
    SELECT
        e.scenario_id,
        e.expected_min_score,
        e.track_id,
        COALESCE(f.composite_suspicion_score, 0) AS score
    FROM {{ ref('fraud_scenario_expectations') }} e
    LEFT JOIN {{ ref('fct_artificial_streaming_flags') }} f
           ON f.track_id = e.track_id
),

per_scenario AS (
    SELECT
        scenario_id,
        MIN(expected_min_score)                                       AS expected_min_score,
        COUNT(DISTINCT track_id)                                      AS expected_track_count,
        MAX(score)                                                    AS actual_max_score,
        COUNT(DISTINCT CASE WHEN score >= expected_min_score
                            THEN track_id END)                        AS tracks_at_or_above_threshold
    FROM joined
    GROUP BY scenario_id
)

SELECT
    scenario_id,
    expected_min_score,
    expected_track_count,
    actual_max_score,
    tracks_at_or_above_threshold,
    'fraud not caught — max(composite_score) < expected_min_score' AS failure_reason
FROM per_scenario
WHERE actual_max_score < expected_min_score
