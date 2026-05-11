{{ config(materialized='table') }}

-- Per-scenario LLM agreement metrics. "2-of-3 agreement" is the JD-relevant
-- analyst measure: how often do at least 2 providers concur on the
-- recommended action? "3-of-3 agreement" is the strict consensus signal.

WITH verdicts AS (
    SELECT scenario_id, provider, llm_recommendation, status, heuristic_action
    FROM {{ ref('fct_llm_verdicts') }}
),

per_scenario AS (
    SELECT
        scenario_id,
        MAX(heuristic_action)                                                AS heuristic_action,
        SUM(CASE WHEN status = 'ok'  THEN 1 ELSE 0 END)                       AS n_verdicts_ok,
        SUM(CASE WHEN status <> 'ok' THEN 1 ELSE 0 END)                       AS n_verdicts_failed,

        -- Vote tallies per recommendation (portable: SUM/CASE not COUNT/FILTER)
        SUM(CASE WHEN llm_recommendation = 'recommend_remove'      THEN 1 ELSE 0 END) AS n_remove,
        SUM(CASE WHEN llm_recommendation = 'recommend_rank_lower'  THEN 1 ELSE 0 END) AS n_rank_lower,
        SUM(CASE WHEN llm_recommendation = 'recommend_no_action'   THEN 1 ELSE 0 END) AS n_no_action,
        SUM(CASE WHEN llm_recommendation IS NULL                   THEN 1 ELSE 0 END) AS n_null_rec
    FROM verdicts
    GROUP BY scenario_id
)

SELECT
    scenario_id,
    heuristic_action,
    n_verdicts_ok,
    n_verdicts_failed,
    n_remove,
    n_rank_lower,
    n_no_action,
    n_null_rec,

    -- 2-of-3 agreement: at least one bucket has >= 2 verdicts
    CASE
        WHEN GREATEST(n_remove, n_rank_lower, n_no_action) >= 2 THEN 1 ELSE 0
    END                                                          AS two_of_three_agree,

    -- 3-of-3 unanimous agreement
    CASE
        WHEN n_verdicts_ok = 3
         AND GREATEST(n_remove, n_rank_lower, n_no_action) = 3
        THEN 1 ELSE 0
    END                                                          AS unanimous_agree,

    -- The plurality recommendation (NULL if no vote bucket has ≥2)
    CASE
        WHEN n_remove     = GREATEST(n_remove, n_rank_lower, n_no_action) AND n_remove     >= 2 THEN 'recommend_remove'
        WHEN n_rank_lower = GREATEST(n_remove, n_rank_lower, n_no_action) AND n_rank_lower >= 2 THEN 'recommend_rank_lower'
        WHEN n_no_action  = GREATEST(n_remove, n_rank_lower, n_no_action) AND n_no_action  >= 2 THEN 'recommend_no_action'
        ELSE NULL
    END                                                          AS plurality_recommendation,

    -- Did the LLM plurality match Cadence's heuristic?
    CASE
        WHEN GREATEST(n_remove, n_rank_lower, n_no_action) >= 2 AND (
                 (n_remove     = GREATEST(n_remove, n_rank_lower, n_no_action) AND n_remove     >= 2 AND heuristic_action = 'recommend_remove') OR
                 (n_rank_lower = GREATEST(n_remove, n_rank_lower, n_no_action) AND n_rank_lower >= 2 AND heuristic_action = 'recommend_rank_lower') OR
                 (n_no_action  = GREATEST(n_remove, n_rank_lower, n_no_action) AND n_no_action  >= 2 AND heuristic_action = 'recommend_no_action')
             )
        THEN 1 ELSE 0
    END                                                          AS llm_plurality_matches_heuristic
FROM per_scenario
ORDER BY scenario_id
