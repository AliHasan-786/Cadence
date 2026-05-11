{{ config(materialized='table') }}

-- Researcher API audit summary. Aggregated for dashboards.
-- Per (researcher, day) — how many calls, what fraction succeeded, mean latency.

SELECT
    key_id,
    researcher_name,
    institution,
    query_date,
    COUNT(*)                                                AS n_queries,
    SUM(CASE WHEN outcome_class = 'success'      THEN 1 ELSE 0 END) AS n_success,
    SUM(CASE WHEN outcome_class = 'rate_limited' THEN 1 ELSE 0 END) AS n_rate_limited,
    SUM(CASE WHEN outcome_class = 'client_error' THEN 1 ELSE 0 END) AS n_client_error,
    SUM(CASE WHEN outcome_class = 'server_error' THEN 1 ELSE 0 END) AS n_server_error,
    ROUND(AVG(latency_ms), 1)                               AS mean_latency_ms,
    SUM(response_size_bytes)                                AS total_response_bytes,
    COUNT(DISTINCT endpoint)                                AS distinct_endpoints_hit
FROM {{ ref('fct_researcher_queries') }}
GROUP BY key_id, researcher_name, institution, query_date
