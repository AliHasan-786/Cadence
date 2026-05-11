{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_moderation_actions_synth') }}
)

SELECT
    {{ safe_text('action_id') }}                       AS action_id,
    {{ safe_text('subject_type') }}                    AS subject_type,
    {{ safe_text('subject_id') }}                      AS subject_id,
    {{ safe_text('category') }}                        AS category_code,
    {{ safe_text('decision_type') }}                   AS decision_type,
    {{ safe_text('decision_basis') }}                  AS decision_basis,
    {{ safe_timestamp('ts') }}                         AS action_ts,
    {{ safe_text('notice_origin') }}                   AS notice_origin
FROM source
