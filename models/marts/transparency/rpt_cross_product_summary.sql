{{ config(materialized='table') }}

-- THE HEADLINE QUERY for the Looker Studio Cross-Product Executive Summary.
-- One row per Spotify product line × reporting period. Surface the metrics a
-- Compliance Counsel or Policy Manager would compare side-by-side.

WITH notices_total AS (
    SELECT product_line, reporting_period_canonical,
           reporting_period_start, reporting_period_end,
           notices_received, items_in_notices,
           actions_on_law, actions_on_tc,
           median_time_to_take_action_hours
    FROM {{ ref('stg_dsa_notices') }}
    WHERE category_code = 'TOTAL'
),

oi_illegal_total AS (
    SELECT product_line,
           measures_own_initiative AS oi_illegal_measures,
           measures_automated_detection AS oi_illegal_automated
    FROM {{ ref('stg_dsa_own_initiative_illegal') }}
    WHERE category_code = 'TOTAL'
),

oi_tc_total AS (
    SELECT product_line,
           measures_own_initiative AS oi_tc_measures,
           measures_automated_detection AS oi_tc_automated
    FROM {{ ref('stg_dsa_own_initiative_tc') }}
    WHERE category_code = 'TOTAL'
),

complaints AS (
    SELECT product_line, complaints_submitted
    FROM {{ ref('int_dsa_appeals') }}
),

quality_total AS (
    SELECT product_line, accuracy, precision_score, recall,
           measures_solely_automated, measures_not_automated
    FROM {{ ref('int_dsa_automated_quality') }}
    WHERE scope = 'Total number'
)

SELECT
    n.product_line,
    n.reporting_period_canonical,
    n.reporting_period_start,
    n.reporting_period_end,

    -- Notices (Art. 16)
    n.notices_received,
    n.items_in_notices,
    n.actions_on_law,
    n.actions_on_tc,
    n.actions_on_law + n.actions_on_tc                            AS notice_actions_total,

    -- Own-initiative measures
    COALESCE(i.oi_illegal_measures, 0)                            AS own_initiative_illegal,
    COALESCE(t.oi_tc_measures, 0)                                 AS own_initiative_tc,
    COALESCE(i.oi_illegal_measures, 0) + COALESCE(t.oi_tc_measures, 0)
        AS own_initiative_total,

    -- Canonical decision total = notice-driven actions + own-initiative measures
    n.actions_on_law + n.actions_on_tc
        + COALESCE(i.oi_illegal_measures, 0)
        + COALESCE(t.oi_tc_measures, 0)                           AS total_decisions,

    COALESCE(i.oi_illegal_automated, 0) + COALESCE(t.oi_tc_automated, 0)
        AS automated_decisions,

    CASE WHEN n.actions_on_law + n.actions_on_tc
             + COALESCE(i.oi_illegal_measures, 0)
             + COALESCE(t.oi_tc_measures, 0) > 0
         THEN ROUND(
             100.0 * (COALESCE(i.oi_illegal_automated, 0) + COALESCE(t.oi_tc_automated, 0))
             / (n.actions_on_law + n.actions_on_tc
                + COALESCE(i.oi_illegal_measures, 0)
                + COALESCE(t.oi_tc_measures, 0))
         , 2)
         ELSE NULL
    END                                                            AS automated_share_pct,

    -- Median time-to-act on notices (hours)
    n.median_time_to_take_action_hours,

    -- Art. 24: appeals lifecycle
    COALESCE(c.complaints_submitted, 0)                            AS complaints_submitted,

    -- Automated-means quality (Total scope)
    ROUND(100.0 * q.accuracy,        2)                            AS automated_accuracy_pct,
    ROUND(100.0 * q.precision_score, 2)                            AS automated_precision_pct,
    ROUND(100.0 * q.recall,          2)                            AS automated_recall_pct,

    -- Notices solely vs not-solely processed by automated means (NAM scope's count split)
    q.measures_solely_automated,
    q.measures_not_automated

FROM notices_total n
LEFT JOIN oi_illegal_total i USING (product_line)
LEFT JOIN oi_tc_total      t USING (product_line)
LEFT JOIN complaints       c USING (product_line)
LEFT JOIN quality_total    q USING (product_line)
ORDER BY n.product_line
