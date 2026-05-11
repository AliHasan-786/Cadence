-- Period continuity invariants. With 1 period loaded, this asserts:
--   (a) every product has exactly the same set of periods
--       (no product can have data for a period the others lack);
--   (b) every period's start < end;
--   (c) period_days > 0.
--
-- When 2024 backfill lands, this evolves to also assert no inter-period
-- gaps. Today the 1-period case is the graceful baseline.

WITH per_product AS (
    SELECT
        product_line,
        -- STRING_AGG syntax is identical between BQ and DuckDB
        STRING_AGG(reporting_period_canonical, ',') AS periods_present
    FROM {{ ref('rpt_cross_product_summary') }}
    GROUP BY product_line
),

period_set_distinct AS (
    SELECT COUNT(DISTINCT periods_present) AS distinct_sets FROM per_product
),

failures AS (
    -- (a) Different products carrying different period sets
    SELECT 'period_set_mismatch' AS failure_kind,
           CAST(distinct_sets AS {{ dbt.type_string() }}) AS detail
    FROM period_set_distinct
    WHERE distinct_sets > 1

    UNION ALL

    -- (b)/(c) Periods with invalid start/end or zero duration
    SELECT 'invalid_period' AS failure_kind, reporting_period_id AS detail
    FROM {{ ref('dim_dsa_reporting_periods') }}
    WHERE reporting_period_start >= reporting_period_end
       OR period_days <= 0
)

SELECT * FROM failures
