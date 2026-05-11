{{ config(materialized='view') }}

-- Audit log of every researcher-API call. Streamed into
-- cadence_raw.raw_researcher_queries by the FastAPI middleware.

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_researcher_queries') }}
)

SELECT
    {{ safe_text('query_id') }}                   AS query_id,
    {{ safe_text('key_id') }}                     AS key_id,
    {{ safe_text('endpoint') }}                   AS endpoint,
    {{ safe_text('query_params_json') }}          AS query_params_json,
    {{ safe_int('response_size_bytes') }}         AS response_size_bytes,
    {{ safe_int('response_status_code') }}        AS response_status_code,
    {{ safe_int('latency_ms') }}                  AS latency_ms,
    {{ safe_timestamp('requested_at') }}          AS requested_at,
    {{ safe_text('client_ip_hash') }}             AS client_ip_hash
FROM source
