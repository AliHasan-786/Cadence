{{ config(materialized='view') }}

-- The 100-row EU harmonised taxonomy is published identically inside every
-- product's report. We materialise it once with a discriminator column for
-- provenance, then Sprint 5's `int_dsa_unified` reads from a single product's
-- rows (they're guaranteed identical across the four).

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_dsa_categories_names') }}
)

SELECT
    {{ safe_text('source_product') }}                  AS product_line,
    {{ reporting_period_canonical() }}                 AS reporting_period_canonical,

    {{ safe_text('category_label') }}                  AS category_label,
    {{ safe_text('category_description') }}            AS category_description,
    {{ safe_text('category_of_illegal_or_tc') }}       AS category_code,
    {{ safe_text('contextual_information') }}          AS contextual_information,

    {{ safe_text('source_sheet') }}                    AS source_sheet,
    {{ safe_int('source_row_index') }}                 AS source_row_index,
    {{ safe_text('source_sha256') }}                   AS source_sha256
FROM source
