{{ config(materialized='table') }}

-- Appeals lifecycle per product. Today Spotify discloses only `complaints
-- submitted` — the other Art. 24 indicators (reversed/upheld/recidivism)
-- are placeholders that will populate as future reports do.

SELECT
    f.product_line,
    f.reporting_period_canonical,
    f.reporting_period_start,
    f.reporting_period_end,

    f.complaints_submitted,
    f.complaints_reversed,
    f.complaints_upheld,
    f.recidivism_count,
    f.reversal_rate_pct,

    -- Per-product context — useful in the dashboard
    s.total_decisions,
    CASE WHEN s.total_decisions > 0 AND f.complaints_submitted IS NOT NULL
         THEN ROUND(100.0 * f.complaints_submitted / s.total_decisions, 2)
         ELSE NULL
    END AS complaints_per_100_decisions
FROM {{ ref('fct_dsa_appeals') }} f
LEFT JOIN {{ ref('rpt_cross_product_summary') }} s USING (product_line, reporting_period_canonical)
ORDER BY f.product_line
