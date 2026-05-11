{{ config(materialized='view') }}

-- Pivot stg_dsa_automated_means from long format (Indicator/Scope/Value) to
-- wide format. Grain: (product_line, scope). Surfaces accuracy / precision /
-- recall as named columns + the automation-share counts.

WITH source AS (
    SELECT * FROM {{ ref('stg_dsa_automated_means') }}
)

SELECT
    product_line,
    reporting_period_canonical,
    reporting_period_start,
    reporting_period_end,
    scope,

    MAX(CASE WHEN quality_metric_kind = 'accuracy'  THEN value END) AS accuracy,
    MAX(CASE WHEN quality_metric_kind = 'precision' THEN value END) AS precision_score,
    MAX(CASE WHEN quality_metric_kind = 'recall'    THEN value END) AS recall,

    -- The two count indicators per scope (separately for measures vs notices)
    MAX(CASE WHEN indicator LIKE 'Number of measures solely taken by automated%' THEN value END) AS measures_solely_automated,
    MAX(CASE WHEN indicator LIKE 'Number of measures not taken by automated%'    THEN value END) AS measures_not_automated,
    MAX(CASE WHEN indicator LIKE 'Number of notices solely processed by automated%' THEN value END) AS notices_solely_automated,
    MAX(CASE WHEN indicator LIKE 'Number of notices not processed by automated%'    THEN value END) AS notices_not_automated
FROM source
GROUP BY product_line, reporting_period_canonical, reporting_period_start, reporting_period_end, scope
