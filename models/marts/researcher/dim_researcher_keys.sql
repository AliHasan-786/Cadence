{{ config(materialized='table') }}

-- One row per active researcher API key.
-- Streamed-in from FastAPI; rolled up here for dashboard + audit lookups.

SELECT
    key_id,
    researcher_name,
    institution,
    purpose,
    email_hash,
    created_at,
    status,
    CURRENT_TIMESTAMP() AS dim_built_at
FROM {{ ref('stg_researcher_keys') }}
WHERE status = 'active' OR status IS NULL  -- NULL = pre-status-field rows
