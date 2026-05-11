{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_users_synth') }}
)

SELECT
    {{ safe_text('user_id') }}                         AS user_id,
    {{ safe_text('country') }}                         AS country_iso2,
    {{ safe_text('plan_type') }}                       AS plan_type,
    {{ safe_timestamp('signup_ts') }}                  AS signup_ts,
    {{ safe_text('age_band') }}                        AS age_band,
    {{ safe_text('household_id') }}                    AS household_id,

    -- Convenience flags for downstream detection signals
    CASE WHEN {{ safe_text('plan_type') }} = 'family' THEN TRUE ELSE FALSE END
        AS is_family_plan,
    CASE WHEN {{ safe_text('user_id') }} LIKE 'u_990%' THEN TRUE ELSE FALSE END
        AS is_synth_fraud_injected_user  -- diagnostic only — detection models must not depend on this
FROM source
