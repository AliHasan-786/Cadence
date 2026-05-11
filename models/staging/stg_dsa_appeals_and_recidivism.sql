{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_dsa_appeals_and_recidivism') }}
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

    {{ safe_text('source_sheet') }}                    AS source_sheet,
    {{ safe_int('source_row_index') }}                 AS source_row_index,
    {{ safe_text('source_sha256') }}                   AS source_sha256
FROM source
