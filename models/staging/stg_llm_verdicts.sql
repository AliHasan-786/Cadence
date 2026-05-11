{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_llm_verdicts') }}
)

SELECT
    {{ safe_text('verdict_id') }}                  AS verdict_id,
    {{ safe_text('scenario_id') }}                 AS scenario_id,
    {{ safe_text('track_id') }}                    AS track_id,
    {{ safe_text('provider') }}                    AS provider,
    {{ safe_text('model') }}                       AS model_name,

    {{ safe_text('status') }}                      AS status,
    {{ safe_text('error_class') }}                 AS error_class,

    {{ safe_text('recommendation') }}              AS recommendation,
    {{ safe_float('confidence') }}                 AS confidence,
    {{ safe_text('primary_signal') }}              AS primary_signal,
    {{ safe_text('reasoning') }}                   AS reasoning,
    {{ safe_text('uncertainty_flags') }}           AS uncertainty_flags_json,

    {{ safe_timestamp('requested_at') }}           AS requested_at,
    {{ safe_timestamp('completed_at') }}           AS completed_at,
    {{ safe_int('latency_ms') }}                   AS latency_ms,
    {{ safe_int('input_tokens') }}                 AS input_tokens,
    {{ safe_int('output_tokens') }}                AS output_tokens,
    {{ safe_float('cost_usd') }}                   AS cost_usd,
    {{ safe_text('prompt_hash') }}                 AS prompt_hash,
    {{ safe_text('response_hash') }}               AS response_hash
FROM source
