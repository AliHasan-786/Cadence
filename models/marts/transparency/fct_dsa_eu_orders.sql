{{ config(materialized='table') }}

-- Member-state orders fact (Art. 17). Grain: (product_line, reporting_period,
-- category_code, scope). For 2025 data, every product reports `scope = 'TOTAL'`
-- (no per-state breakdown disclosed). The seed's EU_AGGREGATE row covers it.

SELECT
    s.product_line,
    s.reporting_period_canonical,
    s.reporting_period_start,
    s.reporting_period_end,
    s.category_code,
    s.scope,
    'EU_AGGREGATE' AS member_state_id,  -- Spotify discloses only aggregated EU totals in 2025

    {{ safe_int('s.orders_to_act') }}                 AS orders_to_act,
    {{ safe_int('s.items_in_orders_to_act') }}        AS items_in_orders_to_act,
    {{ safe_float('s.median_time_to_inform_act_hours') }}      AS median_time_to_inform_act_hours,
    {{ safe_float('s.median_time_to_give_effect_act_hours') }} AS median_time_to_give_effect_act_hours,
    {{ safe_int('s.orders_to_provide_info') }}        AS orders_to_provide_info,
    {{ safe_float('s.median_time_to_inform_info_hours') }}     AS median_time_to_inform_info_hours,
    {{ safe_float('s.median_time_to_give_effect_info_hours') }} AS median_time_to_give_effect_info_hours,

    s.source_sha256
FROM {{ ref('stg_dsa_member_states_orders') }} s
WHERE s.category_code IS NOT NULL
