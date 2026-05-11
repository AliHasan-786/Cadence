{{ config(materialized='view') }}

-- Sheet 6: own-initiative measures against terms-of-service violations.
-- Structurally identical to sheet 5 except column D names "incompatibility
-- with T&Cs" instead of "illegal content".

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_dsa_own_initiative_tc') }}
)

SELECT
    {{ safe_text('source_product') }}                              AS product_line,
    {{ reporting_period_canonical() }}                             AS reporting_period_canonical,
    {{ reporting_period_start() }}                                 AS reporting_period_start,
    {{ reporting_period_end() }}                                   AS reporting_period_end,

    {{ safe_text('applicability') }}                               AS applicability,
    {{ safe_text('service') }}                                     AS service,
    {{ safe_text('category_of_incompatibility_tc') }}              AS category_code,
    {{ safe_text('description_subcategory_other') }}               AS description_subcategory_other,

    {{ safe_int('n_measures_own_initiative') }}                    AS measures_own_initiative,
    {{ safe_int('n_measures_automated_detection') }}               AS measures_automated_detection,

    {{ safe_int('vis_restriction_removal') }}                      AS vis_restriction_removal,
    {{ safe_int('vis_restriction_disable') }}                      AS vis_restriction_disable,
    {{ safe_int('vis_restriction_demoted') }}                      AS vis_restriction_demoted,
    {{ safe_int('vis_restriction_age_restricted') }}               AS vis_restriction_age_restricted,
    {{ safe_int('vis_restriction_interaction_restricted') }}       AS vis_restriction_interaction_restricted,
    {{ safe_int('vis_restriction_labelled') }}                     AS vis_restriction_labelled,
    {{ safe_int('vis_restriction_other') }}                        AS vis_restriction_other,

    {{ safe_int('mon_restriction_suspension') }}                   AS mon_restriction_suspension,
    {{ safe_int('mon_restriction_termination') }}                  AS mon_restriction_termination,
    {{ safe_int('mon_restriction_other') }}                        AS mon_restriction_other,

    {{ safe_int('provision_suspension') }}                         AS provision_suspension,
    {{ safe_int('provision_termination') }}                        AS provision_termination,

    {{ safe_int('account_suspension') }}                           AS account_suspension,
    {{ safe_int('account_termination') }}                          AS account_termination,

    {{ safe_text('ctx_n_measures_own_initiative') }}               AS ctx_measures_own_initiative,
    {{ safe_text('ctx_n_measures_automated_detection') }}          AS ctx_measures_automated_detection,
    {{ safe_text('ctx_vis_restriction_removal') }}                 AS ctx_vis_restriction_removal,
    {{ safe_text('ctx_vis_restriction_disable') }}                 AS ctx_vis_restriction_disable,
    {{ safe_text('ctx_vis_restriction_demoted') }}                 AS ctx_vis_restriction_demoted,
    {{ safe_text('ctx_vis_restriction_age_restricted') }}          AS ctx_vis_restriction_age_restricted,
    {{ safe_text('ctx_vis_restriction_interaction_restricted') }}  AS ctx_vis_restriction_interaction_restricted,
    {{ safe_text('ctx_vis_restriction_labelled') }}                AS ctx_vis_restriction_labelled,
    {{ safe_text('ctx_vis_restriction_other') }}                   AS ctx_vis_restriction_other,
    {{ safe_text('ctx_mon_restriction_suspension') }}              AS ctx_mon_restriction_suspension,
    {{ safe_text('ctx_mon_restriction_termination') }}             AS ctx_mon_restriction_termination,
    {{ safe_text('ctx_mon_restriction_other') }}                   AS ctx_mon_restriction_other,
    {{ safe_text('ctx_provision_suspension') }}                    AS ctx_provision_suspension,
    {{ safe_text('ctx_provision_termination') }}                   AS ctx_provision_termination,
    {{ safe_text('ctx_account_suspension') }}                      AS ctx_account_suspension,
    {{ safe_text('ctx_account_termination') }}                     AS ctx_account_termination,

    {{ safe_text('source_sheet') }}                                AS source_sheet,
    {{ safe_int('source_row_index') }}                             AS source_row_index,
    {{ safe_text('source_sha256') }}                               AS source_sha256
FROM source
