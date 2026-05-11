{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_appeals_synth') }}
)

SELECT
    {{ safe_text('appeal_id') }}                       AS appeal_id,
    {{ safe_text('action_id') }}                       AS action_id,
    {{ safe_timestamp('ts_filed') }}                   AS filed_at,
    {{ safe_timestamp('ts_resolved') }}                AS resolved_at,
    {{ safe_text('status') }}                          AS status,
    {{ safe_text('reviewer_type') }}                   AS reviewer_type
FROM source
