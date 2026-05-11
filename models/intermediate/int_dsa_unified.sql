{{ config(materialized='view') }}

-- The cross-product, cross-sheet unification.
--
-- Grain: (product_line, reporting_period, category_code).
-- Joins notices + own_initiative_illegal + own_initiative_tc by category for
-- every product. Result: ~400 rows (4 products × ~100 categories) representing
-- every (product, category) combination Spotify discloses, with both the
-- notice-driven and own-initiative metrics in one place.
--
-- Per the harmonised-template uniformity finding from Sprint 2: source_product
-- is the only discriminator we need — no bespoke per-product reconciliation.

WITH grain AS (
    SELECT product_line, reporting_period_canonical, reporting_period_start,
           reporting_period_end, category_code
    FROM {{ ref('stg_dsa_notices') }}
    UNION DISTINCT
    SELECT product_line, reporting_period_canonical, reporting_period_start,
           reporting_period_end, category_code
    FROM {{ ref('stg_dsa_own_initiative_illegal') }}
    UNION DISTINCT
    SELECT product_line, reporting_period_canonical, reporting_period_start,
           reporting_period_end, category_code
    FROM {{ ref('stg_dsa_own_initiative_tc') }}
),

notices AS (
    SELECT product_line, reporting_period_canonical, category_code,
           notices_received, notices_from_trusted_flaggers,
           items_in_notices, items_in_tf_notices,
           median_time_to_take_action_hours,
           actions_on_law, actions_on_law_tf,
           actions_on_tc, actions_on_tc_tf,
           source_sha256
    FROM {{ ref('stg_dsa_notices') }}
),

oi_illegal AS (
    SELECT product_line, reporting_period_canonical, category_code,
           measures_own_initiative AS oi_illegal_measures,
           measures_automated_detection AS oi_illegal_automated,
           vis_restriction_removal AS oi_illegal_removals,
           account_suspension + account_termination AS oi_illegal_account_actions
    FROM {{ ref('stg_dsa_own_initiative_illegal') }}
),

oi_tc AS (
    SELECT product_line, reporting_period_canonical, category_code,
           measures_own_initiative AS oi_tc_measures,
           measures_automated_detection AS oi_tc_automated,
           vis_restriction_removal AS oi_tc_removals,
           account_suspension + account_termination AS oi_tc_account_actions
    FROM {{ ref('stg_dsa_own_initiative_tc') }}
)

SELECT
    g.product_line,
    g.reporting_period_canonical,
    g.reporting_period_start,
    g.reporting_period_end,
    g.category_code,

    -- Notices-driven (Art. 16)
    COALESCE(n.notices_received, 0)              AS notices_received,
    COALESCE(n.notices_from_trusted_flaggers, 0) AS notices_from_trusted_flaggers,
    COALESCE(n.items_in_notices, 0)              AS items_in_notices,
    COALESCE(n.items_in_tf_notices, 0)           AS items_in_tf_notices,
    COALESCE(n.actions_on_law, 0)                AS actions_on_law,
    COALESCE(n.actions_on_law_tf, 0)             AS actions_on_law_tf,
    COALESCE(n.actions_on_tc, 0)                 AS actions_on_tc,
    COALESCE(n.actions_on_tc_tf, 0)              AS actions_on_tc_tf,
    n.median_time_to_take_action_hours,

    -- Own-initiative against illegal content
    COALESCE(i.oi_illegal_measures, 0)           AS own_initiative_illegal_measures,
    COALESCE(i.oi_illegal_automated, 0)          AS own_initiative_illegal_automated,
    COALESCE(i.oi_illegal_removals, 0)           AS own_initiative_illegal_removals,
    COALESCE(i.oi_illegal_account_actions, 0)    AS own_initiative_illegal_account_actions,

    -- Own-initiative against T&C violations
    COALESCE(t.oi_tc_measures, 0)                AS own_initiative_tc_measures,
    COALESCE(t.oi_tc_automated, 0)               AS own_initiative_tc_automated,
    COALESCE(t.oi_tc_removals, 0)                AS own_initiative_tc_removals,
    COALESCE(t.oi_tc_account_actions, 0)         AS own_initiative_tc_account_actions,

    -- Canonical totals
    COALESCE(n.actions_on_law, 0) + COALESCE(n.actions_on_tc, 0)
        + COALESCE(i.oi_illegal_measures, 0) + COALESCE(t.oi_tc_measures, 0)   AS total_decisions,
    COALESCE(i.oi_illegal_automated, 0) + COALESCE(t.oi_tc_automated, 0)        AS automated_decisions,

    -- Provenance — use the notices SHA when present (most rows have notices)
    n.source_sha256
FROM grain g
LEFT JOIN notices    n USING (product_line, reporting_period_canonical, category_code)
LEFT JOIN oi_illegal i USING (product_line, reporting_period_canonical, category_code)
LEFT JOIN oi_tc      t USING (product_line, reporting_period_canonical, category_code)
