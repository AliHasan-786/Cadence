{{ config(materialized='table') }}

-- Period dimension. Today: one row (annual_2025). Future: one row per
-- Spotify reporting period as more years are ingested.

SELECT
    reporting_period_canonical                 AS reporting_period_id,
    reporting_period_start,
    reporting_period_end,
    period_days,
    CASE
        WHEN period_days >= 350 THEN 'annual'
        WHEN period_days >= 175 THEN 'biannual'
        WHEN period_days >=  85 THEN 'quarterly'
        ELSE 'other'
    END                                        AS period_granularity,
    EXTRACT(YEAR FROM reporting_period_start)  AS calendar_year,
    'Spotify DSA (2024/2835 harmonised template)' AS reporting_framework
FROM {{ ref('int_dsa_period_aligned') }}
