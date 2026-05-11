{{ config(materialized='view') }}

-- Per-verdict view enriched with heuristic context: each LLM verdict carries
-- the composite suspicion score and heuristic recommendation Spotify's
-- automated detection produced for the same track. This is the JOIN that
-- lets rpt_* models ask "do LLMs agree with the heuristic?"

WITH verdicts AS (
    SELECT * FROM {{ ref('stg_llm_verdicts') }}
),

heuristic AS (
    SELECT
        track_id,
        composite_suspicion_score,
        recommended_action AS heuristic_action,
        n_signals_fired
    FROM {{ ref('fct_artificial_streaming_flags') }}
)

SELECT
    v.verdict_id,
    v.scenario_id,
    v.track_id,
    v.provider,
    v.model_name,
    v.status,
    v.error_class,

    v.recommendation                                            AS llm_recommendation,
    v.confidence                                                AS llm_confidence,
    v.primary_signal                                            AS llm_primary_signal,
    v.reasoning                                                 AS llm_reasoning,

    h.composite_suspicion_score                                 AS heuristic_score,
    h.heuristic_action,
    h.n_signals_fired,

    CASE
        WHEN v.recommendation IS NULL THEN NULL
        WHEN v.recommendation = h.heuristic_action THEN 1
        ELSE 0
    END                                                         AS llm_agrees_with_heuristic,

    v.requested_at, v.completed_at,
    v.latency_ms, v.input_tokens, v.output_tokens, v.cost_usd,
    v.prompt_hash, v.response_hash
FROM verdicts v
LEFT JOIN heuristic h ON h.track_id = v.track_id
