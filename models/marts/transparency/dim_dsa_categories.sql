{{ config(materialized='table') }}

-- Promote the EU harmonised template's 100-row taxonomy from
-- stg_dsa_categories_names. Per Sprint 2's finding, all four products carry
-- byte-identical taxonomy rows, so we pick `main` as the canonical copy.
--
-- IMPORTANT: `category_label` ('Category 1a' etc.) is the unique PK, NOT
-- `category_code`. The harmonised template re-uses `KEYWORD_OTHER` across
-- many sub-categories — code is many-to-one with label. Fact-table joins
-- use the code (and tolerate the ambiguity); the dim resolves to label
-- for display.

WITH canonical AS (
    SELECT
        category_label,
        MAX(category_description) AS category_description,
        MAX(category_code)        AS category_code
    FROM {{ ref('stg_dsa_categories_names') }}
    WHERE product_line = 'main'
      AND category_label IS NOT NULL
    GROUP BY category_label
)

SELECT
    category_label       AS category_id,
    category_label,
    category_description,
    category_code,
    CASE
        WHEN category_label = 'TOTAL'                                    THEN 'aggregate'
        WHEN category_label LIKE 'Category %'
             AND LENGTH(category_label) <= LENGTH('Category 99')         THEN 'top_level'
        ELSE 'sub_category'
    END                  AS category_level
FROM canonical

