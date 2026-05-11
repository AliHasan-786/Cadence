{{ config(materialized='table') }}

-- Canonical moderation-decision fact table.
-- Grain: (product_line, reporting_period, category_code).
-- One row per (product × category) — the cross-product unified view that
-- powers rpt_cross_product_summary, rpt_quarter_over_quarter_trends, and
-- rpt_automated_vs_human.

SELECT
    u.product_line,
    u.reporting_period_canonical,
    u.reporting_period_start,
    u.reporting_period_end,
    u.category_code,

    u.notices_received,
    u.notices_from_trusted_flaggers,
    u.items_in_notices,
    u.items_in_tf_notices,

    u.actions_on_law,
    u.actions_on_tc,
    u.actions_on_law + u.actions_on_tc                 AS actions_on_notice_total,

    u.own_initiative_illegal_measures,
    u.own_initiative_illegal_automated,
    u.own_initiative_tc_measures,
    u.own_initiative_tc_automated,

    u.total_decisions,
    u.automated_decisions,

    CASE WHEN u.total_decisions > 0
         THEN ROUND(100.0 * u.automated_decisions / u.total_decisions, 2)
         ELSE NULL
    END                                                AS automated_share_pct,

    u.median_time_to_take_action_hours,
    u.source_sha256
FROM {{ ref('int_dsa_unified') }} u
WHERE u.category_code IS NOT NULL
