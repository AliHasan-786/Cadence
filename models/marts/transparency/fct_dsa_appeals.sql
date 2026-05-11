{{ config(materialized='table') }}

-- Appeals fact. Today sparse — Spotify discloses one indicator
-- ("complaints submitted to internal-complaints mechanism") per product —
-- but the column shape supports the full Art. 24 indicator set as more
-- gets disclosed in future reports.

SELECT
    product_line,
    reporting_period_canonical,
    reporting_period_start,
    reporting_period_end,

    complaints_submitted,
    complaints_reversed,
    complaints_upheld,
    recidivism_count,

    CASE
        WHEN complaints_submitted > 0 AND complaints_reversed IS NOT NULL
        THEN ROUND(100.0 * complaints_reversed / complaints_submitted, 2)
        ELSE NULL
    END AS reversal_rate_pct
FROM {{ ref('int_dsa_appeals') }}
