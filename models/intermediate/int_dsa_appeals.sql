{{ config(materialized='view') }}

-- Pivot stg_dsa_appeals_and_recidivism to surface the disclosed indicators
-- as named columns. Today there's one indicator disclosed per product
-- ("Number of complaints submitted to the internal-complaints mechanism");
-- the harmonised template defines many more — Spotify left them blank.

SELECT
    product_line,
    reporting_period_canonical,
    reporting_period_start,
    reporting_period_end,

    MAX(CASE WHEN indicator LIKE 'Number of complaints submitted%' THEN value END)
        AS complaints_submitted,
    MAX(CASE WHEN indicator LIKE '%reversed%'           THEN value END)
        AS complaints_reversed,
    MAX(CASE WHEN indicator LIKE '%upheld%'             THEN value END)
        AS complaints_upheld,
    MAX(CASE WHEN indicator LIKE '%recidivism%'         THEN value END)
        AS recidivism_count

FROM {{ ref('stg_dsa_appeals_and_recidivism') }}
GROUP BY product_line, reporting_period_canonical, reporting_period_start, reporting_period_end
