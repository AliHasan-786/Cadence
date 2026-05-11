-- Every category_code present in the moderation fact tables must exist in
-- the canonical EU taxonomy (dim_dsa_categories). A non-empty result means
-- a `fct_dsa_decisions` row referenced a category not in the taxonomy —
-- either Spotify disclosed a non-standard code, or the staging coercion
-- introduced one. Fix the seed mapping (or the staging coercion) rather
-- than silently dropping the row.

WITH unknown_codes AS (
    SELECT DISTINCT category_code
    FROM {{ ref('fct_dsa_decisions') }}
    WHERE category_code IS NOT NULL
)

SELECT u.category_code
FROM unknown_codes u
LEFT JOIN {{ ref('dim_dsa_categories') }} d
       ON d.category_code = u.category_code
WHERE d.category_code IS NULL
