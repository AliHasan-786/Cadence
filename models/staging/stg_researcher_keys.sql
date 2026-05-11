{{ config(materialized='view') }}

-- Researcher API keys issued by the FastAPI service. Streamed into
-- cadence_raw.raw_researcher_keys at request time; this view normalises
-- + types for dim_researcher_keys.

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_researcher_keys') }}
)

SELECT
    {{ safe_text('key_id') }}                       AS key_id,
    {{ safe_text('researcher_name') }}              AS researcher_name,
    {{ safe_text('institution') }}                  AS institution,
    {{ safe_text('purpose') }}                      AS purpose,
    {{ safe_text('email_hash') }}                   AS email_hash,
    {{ safe_timestamp('created_at') }}              AS created_at,
    {{ safe_text('status') }}                       AS status
FROM source
