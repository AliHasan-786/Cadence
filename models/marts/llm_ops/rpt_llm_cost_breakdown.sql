{{ config(materialized='table') }}

-- Per-provider cost breakdown for the pre-cache snapshot.
-- Total spend should be < $10 (PRD-mandated budget ceiling).

WITH base AS (
    SELECT provider, model_name, status, input_tokens, output_tokens, cost_usd
    FROM {{ ref('fct_llm_verdicts') }}
)

SELECT
    provider,
    MAX(model_name)                                              AS model_name,
    COUNT(*)                                                     AS n_verdicts,
    SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END)               AS n_ok,
    SUM(input_tokens)                                            AS total_input_tokens,
    SUM(output_tokens)                                           AS total_output_tokens,
    ROUND(SUM(cost_usd), 5)                                      AS total_cost_usd,
    ROUND(AVG(CASE WHEN status = 'ok' THEN cost_usd END), 5)     AS mean_cost_per_ok_verdict
FROM base
GROUP BY provider
ORDER BY total_cost_usd DESC
