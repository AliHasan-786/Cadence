{{ config(materialized='table') }}

-- Audit fact for the researcher API. Grain: one row per API call.
-- The FastAPI middleware streams these in real-time; dbt rolls them up
-- for dashboards + the /audit/my_queries endpoint.

SELECT
    q.query_id,
    q.key_id,
    k.researcher_name,
    k.institution,
    q.endpoint,
    q.query_params_json,
    q.response_size_bytes,
    q.response_status_code,
    q.latency_ms,
    q.requested_at,
    q.client_ip_hash,
    DATE(q.requested_at)                                      AS query_date,
    EXTRACT(HOUR FROM q.requested_at)                         AS query_hour_utc,

    CASE
        WHEN q.response_status_code BETWEEN 200 AND 299 THEN 'success'
        WHEN q.response_status_code = 429                THEN 'rate_limited'
        WHEN q.response_status_code BETWEEN 400 AND 499 THEN 'client_error'
        WHEN q.response_status_code BETWEEN 500 AND 599 THEN 'server_error'
        ELSE 'other'
    END                                                       AS outcome_class

FROM {{ ref('stg_researcher_queries') }} q
LEFT JOIN {{ ref('dim_researcher_keys') }} k USING (key_id)
