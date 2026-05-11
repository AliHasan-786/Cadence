{{ config(materialized='table') }}

-- Per-EU-Member-State drilldown. For 2025 data, Spotify discloses only
-- EU_AGGREGATE — every order rolls up to a single state ID. The schema
-- supports per-state granularity when later reports include it.

SELECT
    f.product_line,
    f.reporting_period_canonical,
    f.member_state_id,
    m.member_state_name,
    m.is_aggregate,

    SUM(f.orders_to_act)                AS orders_to_act,
    SUM(f.items_in_orders_to_act)       AS items_in_orders_to_act,
    SUM(f.orders_to_provide_info)       AS orders_to_provide_info,

    AVG(f.median_time_to_inform_act_hours)        AS avg_median_time_to_inform_act_hours,
    AVG(f.median_time_to_give_effect_act_hours)   AS avg_median_time_to_give_effect_act_hours
FROM {{ ref('fct_dsa_eu_orders') }} f
LEFT JOIN {{ ref('dim_eu_member_states') }} m
       ON m.member_state_id = f.member_state_id
WHERE f.scope = 'TOTAL'   -- the aggregate scope row per product
GROUP BY f.product_line, f.reporting_period_canonical, f.member_state_id, m.member_state_name, m.is_aggregate
ORDER BY f.product_line, f.member_state_id
