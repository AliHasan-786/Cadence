{{ config(materialized='table') }}

-- Source: seeds/eu_member_states.csv. Includes both GR (ISO 3166-1 alpha-2)
-- and EL (EU's preferred code for Greece) as aliases, plus the EU_AGGREGATE
-- sentinel for product lines that don't disclose per-state granularity.

SELECT
    member_state_code AS member_state_id,
    member_state_name,
    is_eu,
    is_aggregate
FROM {{ ref('eu_member_states') }}
