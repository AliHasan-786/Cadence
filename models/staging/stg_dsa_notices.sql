{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_dsa_notices') }}
)

SELECT
    {{ safe_text('source_product') }}                          AS product_line,
    {{ reporting_period_canonical() }}                         AS reporting_period_canonical,
    {{ reporting_period_start() }}                             AS reporting_period_start,
    {{ reporting_period_end() }}                               AS reporting_period_end,

    {{ safe_text('applicability') }}                           AS applicability,
    {{ safe_text('service') }}                                 AS service,
    {{ safe_text('category_of_illegal_content') }}             AS category_code,
    {{ safe_text('description_subcategory_other') }}           AS description_subcategory_other,

    {{ safe_int('n_notices_received') }}                       AS notices_received,
    {{ safe_int('n_notices_from_trusted_flaggers') }}          AS notices_from_trusted_flaggers,
    {{ safe_int('n_items_in_notices') }}                       AS items_in_notices,
    {{ safe_int('n_items_in_tf_notices') }}                    AS items_in_tf_notices,

    {{ safe_float('median_time_to_take_action') }}             AS median_time_to_take_action_hours,
    {{ safe_float('median_time_to_take_action_tf') }}          AS median_time_to_take_action_tf_hours,

    {{ safe_int('n_actions_on_law') }}                         AS actions_on_law,
    {{ safe_int('n_actions_on_law_tf') }}                      AS actions_on_law_tf,
    {{ safe_int('n_actions_on_tc') }}                          AS actions_on_tc,
    {{ safe_int('n_actions_on_tc_tf') }}                       AS actions_on_tc_tf,

    {{ safe_text('ctx_n_notices_received') }}                  AS ctx_notices_received,
    {{ safe_text('ctx_n_notices_from_trusted_flaggers') }}     AS ctx_notices_from_trusted_flaggers,
    {{ safe_text('ctx_n_items_in_notices') }}                  AS ctx_items_in_notices,
    {{ safe_text('ctx_n_items_in_tf_notices') }}               AS ctx_items_in_tf_notices,
    {{ safe_text('ctx_median_time_to_take_action') }}          AS ctx_median_time_to_take_action,
    {{ safe_text('ctx_median_time_to_take_action_tf') }}       AS ctx_median_time_to_take_action_tf,
    {{ safe_text('ctx_n_actions_on_law') }}                    AS ctx_actions_on_law,
    {{ safe_text('ctx_n_actions_on_law_tf') }}                 AS ctx_actions_on_law_tf,
    {{ safe_text('ctx_n_actions_on_tc') }}                     AS ctx_actions_on_tc,
    {{ safe_text('ctx_n_actions_on_tc_tf') }}                  AS ctx_actions_on_tc_tf,

    {{ safe_text('source_sheet') }}                            AS source_sheet,
    {{ safe_int('source_row_index') }}                         AS source_row_index,
    {{ safe_text('source_sha256') }}                           AS source_sha256
FROM source
