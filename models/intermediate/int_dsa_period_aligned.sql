{{ config(materialized='view') }}

-- Single row today (annual_2025). Once 2024 backfill lands, this view will
-- enumerate every reporting period present in any staged DSA table.

WITH all_periods AS (
    SELECT DISTINCT reporting_period_canonical, reporting_period_start, reporting_period_end
    FROM {{ ref('stg_dsa_notices') }}
    UNION DISTINCT
    SELECT DISTINCT reporting_period_canonical, reporting_period_start, reporting_period_end
    FROM {{ ref('stg_dsa_own_initiative_illegal') }}
    UNION DISTINCT
    SELECT DISTINCT reporting_period_canonical, reporting_period_start, reporting_period_end
    FROM {{ ref('stg_dsa_own_initiative_tc') }}
)
SELECT
    reporting_period_canonical,
    reporting_period_start,
    reporting_period_end,
    {{ dbt.datediff('reporting_period_start', 'reporting_period_end', 'day') }} + 1 AS period_days
FROM all_periods
ORDER BY reporting_period_start
