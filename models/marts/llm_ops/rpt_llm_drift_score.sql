{{ config(materialized='table') }}

-- Per-provider week-over-week drift score (Jensen-Shannon-divergence-style)
-- of recommendation distributions. On the first run with a single
-- pre-cache snapshot there are no prior verdicts to diff against, so the
-- score is NULL — that's the V1 behaviour. When the Airflow DAG (Sprint 12)
-- starts persisting weekly snapshots, this view will populate.
--
-- V1.1: replace the placeholder with an actual JS-divergence computation
-- once we have ≥ 2 snapshots in raw_llm_verdicts_snapshots.

WITH per_provider AS (
    SELECT
        provider,
        MAX(model_name) AS model_name,
        SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS n_ok_current_window,
        SUM(CASE WHEN llm_recommendation = 'recommend_remove'      THEN 1 ELSE 0 END) AS n_remove,
        SUM(CASE WHEN llm_recommendation = 'recommend_rank_lower'  THEN 1 ELSE 0 END) AS n_rank_lower,
        SUM(CASE WHEN llm_recommendation = 'recommend_no_action'   THEN 1 ELSE 0 END) AS n_no_action
    FROM {{ ref('fct_llm_verdicts') }}
    GROUP BY provider
)

SELECT
    provider,
    model_name,
    n_ok_current_window,
    n_remove,
    n_rank_lower,
    n_no_action,
    CAST(NULL AS {{ dbt.type_float() }}) AS drift_score,
    CAST(NULL AS {{ dbt.type_timestamp() }}) AS prior_snapshot_at,
    'no_prior_snapshot' AS drift_status
FROM per_provider
ORDER BY provider
