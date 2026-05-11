{{ config(materialized='view') }}

-- Signal 3: stream_to_listener_ratio
-- Total-streams ÷ distinct-listeners for each track. High ratios indicate
-- a small audience replaying the same track many times — the bot-ring and
-- family-plan-abuse fingerprints.

{% set s2l = var('safety_metrics').thresholds.stream_to_listener_ratio %}
{% set cap = var('safety_metrics').severity_cap %}

WITH per_track AS (
    SELECT
        track_id,
        COUNT(*)                   AS total_streams,
        COUNT(DISTINCT user_id)    AS distinct_listeners
    FROM {{ ref('stg_synth_streams') }}
    GROUP BY track_id
)

SELECT
    track_id,
    CAST('track' AS {{ dbt.type_string() }})                                AS entity_kind,
    total_streams,
    distinct_listeners,
    CAST(total_streams AS {{ dbt.type_float() }}) / NULLIF(distinct_listeners, 0)
        AS streams_per_listener,
    CASE
        WHEN total_streams >= {{ s2l.min_streams }}
         AND CAST(total_streams AS {{ dbt.type_float() }}) / NULLIF(distinct_listeners, 0)
             >= {{ s2l.ratio }}
        THEN 1 ELSE 0
    END                                                                     AS fires,
    LEAST(
        {{ cap }},
        (CAST(total_streams AS {{ dbt.type_float() }}) / NULLIF(distinct_listeners, 0))
        / {{ s2l.ratio }}
    )                                                                       AS severity
FROM per_track
