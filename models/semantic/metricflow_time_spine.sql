{{ config(materialized='table') }}

-- MetricFlow time spine — required for any time-based metric aggregation.
-- Generates a daily date series covering the data range. dbt-utils provides
-- `date_spine` which is cross-dialect (BigQuery + DuckDB both supported).

WITH days AS (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2025-01-01' as date)",
        end_date="cast('2027-01-01' as date)"
    ) }}
)
SELECT
    {{ safe_date('date_day') }} AS date_day
FROM days
