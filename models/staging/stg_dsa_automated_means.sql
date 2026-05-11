{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_dsa_automated_means') }}
)

SELECT
    {{ safe_text('source_product') }}                  AS product_line,
    {{ reporting_period_canonical() }}                 AS reporting_period_canonical,
    {{ reporting_period_start() }}                     AS reporting_period_start,
    {{ reporting_period_end() }}                       AS reporting_period_end,

    {{ safe_text('applicability') }}                   AS applicability,
    {{ safe_text('service') }}                         AS service,
    {{ safe_text('section') }}                         AS section,
    {{ safe_text('indicator') }}                       AS indicator,
    {{ safe_text('scope') }}                           AS scope,
    {{ safe_float('value') }}                          AS value,
    {{ safe_text('contextual_information') }}          AS contextual_information,

    -- Convenience flag for the three quality indicators. The source strings
    -- "Accuracy of the automated means - Accuracy/Precision/Recall" all contain
    -- "Accuracy" — must check the more-specific suffixes first.
    CASE
        WHEN {{ safe_text('indicator') }} LIKE '%- Precision%' THEN 'precision'
        WHEN {{ safe_text('indicator') }} LIKE '%- Recall%' THEN 'recall'
        WHEN {{ safe_text('indicator') }} LIKE '%- Accuracy%' THEN 'accuracy'
        ELSE NULL
    END                                                AS quality_metric_kind,

    {{ safe_text('source_sheet') }}                    AS source_sheet,
    {{ safe_int('source_row_index') }}                 AS source_row_index,
    {{ safe_text('source_sha256') }}                   AS source_sha256
FROM source
