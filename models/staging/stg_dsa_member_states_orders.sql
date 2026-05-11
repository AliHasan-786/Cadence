{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_dsa_member_states_orders') }}
)

SELECT
    {{ safe_text('source_product') }}                                AS product_line,
    {{ reporting_period_canonical() }}                               AS reporting_period_canonical,
    {{ reporting_period_start() }}                                   AS reporting_period_start,
    {{ reporting_period_end() }}                                     AS reporting_period_end,

    {{ safe_text('applicability') }}                                 AS applicability,
    {{ safe_text('service') }}                                       AS service,
    {{ safe_text('category_of_illegal_content') }}                   AS category_code,
    {{ safe_text('description_subcategory_other') }}                 AS description_subcategory_other,
    {{ safe_text('scope') }}                                         AS scope,

    {{ safe_int('n_orders_to_act') }}                                AS orders_to_act,
    {{ safe_int('n_items_in_orders_to_act') }}                       AS items_in_orders_to_act,
    {{ safe_float('median_time_to_inform_act') }}                    AS median_time_to_inform_act_hours,
    {{ safe_float('median_time_to_give_effect_act') }}               AS median_time_to_give_effect_act_hours,
    {{ safe_int('n_orders_to_provide_info') }}                       AS orders_to_provide_info,
    {{ safe_float('median_time_to_inform_info') }}                   AS median_time_to_inform_info_hours,
    {{ safe_float('median_time_to_give_effect_info') }}              AS median_time_to_give_effect_info_hours,

    {{ safe_text('ctx_n_orders_to_act') }}                           AS ctx_orders_to_act,
    {{ safe_text('ctx_n_items_in_orders_to_act') }}                  AS ctx_items_in_orders_to_act,
    {{ safe_text('ctx_median_time_to_inform_act') }}                 AS ctx_median_time_to_inform_act,
    {{ safe_text('ctx_median_time_to_give_effect_act') }}            AS ctx_median_time_to_give_effect_act,
    {{ safe_text('ctx_n_orders_to_provide_info') }}                  AS ctx_orders_to_provide_info,
    {{ safe_text('ctx_median_time_to_inform_info') }}                AS ctx_median_time_to_inform_info,
    {{ safe_text('ctx_median_time_to_give_effect_info') }}           AS ctx_median_time_to_give_effect_info,

    {{ safe_text('source_sheet') }}                                  AS source_sheet,
    {{ safe_int('source_row_index') }}                               AS source_row_index,
    {{ safe_text('source_sha256') }}                                 AS source_sha256
FROM source
