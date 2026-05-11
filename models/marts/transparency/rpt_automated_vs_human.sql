{{ config(materialized='table') }}

-- Surfaces the cross-product Main-conservative / Artists-aggressive finding.
-- For each product:
--   - automation_share: % of moderation decisions taken by automated means
--   - quality triplet at Total scope: accuracy / precision / recall
--   - the qualitative "conservative" vs "aggressive" label derived from the
--     accuracy-vs-recall trade-off

WITH summary AS (
    SELECT
        product_line,
        reporting_period_canonical,
        total_decisions,
        automated_decisions,
        automated_share_pct,
        automated_accuracy_pct,
        automated_precision_pct,
        automated_recall_pct,
        measures_solely_automated,
        measures_not_automated
    FROM {{ ref('rpt_cross_product_summary') }}
)

SELECT
    product_line,
    reporting_period_canonical,

    total_decisions,
    automated_decisions,
    automated_share_pct,

    measures_solely_automated,
    measures_not_automated,
    CASE WHEN measures_solely_automated + measures_not_automated > 0
         THEN ROUND(100.0 * measures_solely_automated
                    / (measures_solely_automated + measures_not_automated), 2)
         ELSE NULL
    END AS measures_solely_automated_share_pct,

    automated_accuracy_pct,
    automated_precision_pct,
    automated_recall_pct,

    -- Labels for the Sprint 4 cross-product finding:
    --   Main: accuracy 100% / recall 94.4% → 5.6pp accuracy-over-recall → conservative
    --   Artists: accuracy 95.0% / recall 96.0% → 1pp recall-over-accuracy → aggressive
    --   Authors/Creators: <3pp gap either way → balanced
    -- Thresholds chosen so a 1pp gap counts as a deliberate posture, not noise.
    CASE
        WHEN automated_accuracy_pct - automated_recall_pct >= 3.0  THEN 'conservative'
        WHEN automated_recall_pct  - automated_accuracy_pct >= 0.5  THEN 'aggressive'
        ELSE 'balanced'
    END AS automation_posture
FROM summary
ORDER BY product_line
