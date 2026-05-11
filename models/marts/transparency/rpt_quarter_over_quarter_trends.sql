{{ config(materialized='table') }}

-- Time-series-ready trend view. With only annual_2025 loaded today, this
-- returns one row per product (one datapoint per series). When 2024 backfill
-- lands, it picks up the prior period automatically.
--
-- The `n_periods_available` column is the graceful-1-period signal the
-- frontend uses to decide whether to render "more periods coming" annotation.

WITH summary AS (
    SELECT * FROM {{ ref('rpt_cross_product_summary') }}
),

ranked AS (
    SELECT
        s.*,
        COUNT(*) OVER (PARTITION BY product_line) AS n_periods_available,
        ROW_NUMBER() OVER (PARTITION BY product_line ORDER BY reporting_period_start) AS period_seq
    FROM summary s
)

SELECT
    product_line,
    reporting_period_canonical,
    reporting_period_start,
    reporting_period_end,
    period_seq,
    n_periods_available,
    total_decisions,
    automated_decisions,
    automated_share_pct,
    notices_received,
    notice_actions_total,
    complaints_submitted,
    automated_accuracy_pct,
    automated_precision_pct,
    automated_recall_pct,

    -- Period-over-period deltas (NULL for the first period of each product)
    total_decisions - LAG(total_decisions) OVER (PARTITION BY product_line ORDER BY reporting_period_start)
        AS total_decisions_delta_vs_prior,
    automated_share_pct - LAG(automated_share_pct) OVER (PARTITION BY product_line ORDER BY reporting_period_start)
        AS automated_share_delta_vs_prior
FROM ranked
ORDER BY product_line, period_seq
