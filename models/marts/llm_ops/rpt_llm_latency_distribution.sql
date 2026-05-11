{{ config(materialized='table') }}

-- Per-provider latency distribution. Only OK verdicts — failed calls
-- have latency_ms = 0 and would skew the distribution.

WITH base AS (
    SELECT provider, model_name, latency_ms
    FROM {{ ref('fct_llm_verdicts') }}
    WHERE status = 'ok' AND latency_ms > 0
)

SELECT
    provider,
    MAX(model_name)                              AS model_name,
    COUNT(*)                                     AS n_ok_verdicts,
    MIN(latency_ms)                              AS latency_ms_min,
    AVG(latency_ms)                              AS latency_ms_mean,
    MAX(latency_ms)                              AS latency_ms_max,
    -- p50/p95: dialect divergence lives in this macro-equivalent branch.
    -- BQ uses APPROX_QUANTILES; DuckDB uses QUANTILE_CONT.
    {% if target.type == 'bigquery' %}
    APPROX_QUANTILES(latency_ms, 100)[OFFSET(50)] AS latency_ms_p50,
    APPROX_QUANTILES(latency_ms, 100)[OFFSET(95)] AS latency_ms_p95
    {% else %}
    QUANTILE_CONT(latency_ms, 0.50)              AS latency_ms_p50,
    QUANTILE_CONT(latency_ms, 0.95)              AS latency_ms_p95
    {% endif %}
FROM base
GROUP BY provider
ORDER BY provider
