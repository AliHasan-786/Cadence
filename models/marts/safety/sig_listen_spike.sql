{{ config(materialized='view') }}

-- Signal 1: listen_spike
-- Fires when a track's streams/day in the last 7 days exceeds its prior
-- 83-day baseline by 10x or more. Catches established-track surges + cold-
-- start anomalies (new releases generating sudden volume).

{% set ls = var('safety_metrics').thresholds.listen_spike %}
{% set cap = var('safety_metrics').severity_cap %}
{% set recent_days = 7 %}
{% set baseline_days = 83 %}

-- Reference point matches the generator's REFERENCE_NOW (Sprint 3). String
-- literals like "TIMESTAMP '...'" work identically on BQ and DuckDB; dbt's
-- dateadd macro returns DATETIME on BQ which conflicts with TIMESTAMP cols,
-- so we compute the cutoff dates at compile time instead.
{% set ref_date = modules.datetime.datetime(2026, 5, 1) %}
{% set recent_cutoff = (ref_date - modules.datetime.timedelta(days=recent_days)).strftime('%Y-%m-%d %H:%M:%S') %}
{% set window_cutoff = (ref_date - modules.datetime.timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S') %}

WITH per_track AS (
    SELECT
        track_id,
        COUNT(CASE WHEN streamed_at >= TIMESTAMP '{{ recent_cutoff }}'
                   THEN 1 END) AS recent_streams,
        COUNT(CASE WHEN streamed_at <  TIMESTAMP '{{ recent_cutoff }}'
                    AND streamed_at >= TIMESTAMP '{{ window_cutoff }}'
                   THEN 1 END) AS baseline_streams
    FROM {{ ref('stg_synth_streams') }}
    WHERE streamed_at >= TIMESTAMP '{{ window_cutoff }}'
    GROUP BY track_id
),

computed AS (
    SELECT
        track_id,
        recent_streams,
        baseline_streams,
        CAST(recent_streams AS {{ dbt.type_float() }})   / {{ recent_days }}   AS recent_per_day,
        CAST(baseline_streams AS {{ dbt.type_float() }}) / {{ baseline_days }} AS baseline_per_day
    FROM per_track
)

SELECT
    track_id,
    CAST('track' AS {{ dbt.type_string() }})                      AS entity_kind,
    recent_streams,
    baseline_streams,
    recent_per_day,
    baseline_per_day,
    recent_per_day / GREATEST(baseline_per_day, {{ ls.min_baseline_streams_per_day }})
        AS spike_ratio,
    CASE
        WHEN recent_per_day / GREATEST(baseline_per_day, {{ ls.min_baseline_streams_per_day }})
             > {{ ls.baseline_multiplier }}
        THEN 1 ELSE 0
    END                                                           AS fires,
    LEAST(
        {{ cap }},
        (recent_per_day / GREATEST(baseline_per_day, {{ ls.min_baseline_streams_per_day }}))
        / {{ ls.baseline_multiplier }}
    )                                                             AS severity
FROM computed
WHERE recent_streams > 0
