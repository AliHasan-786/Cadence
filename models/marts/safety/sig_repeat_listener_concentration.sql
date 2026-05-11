{{ config(materialized='view') }}

-- Signal 4: repeat_listener_concentration
-- Herfindahl-Hirschman Index (HHI) of streams across HOUSEHOLDS (not users)
-- for each track. HHI = sum of squared household shares. HHI = 1.0 when one
-- household drives 100% of streams — the family-plan-abuse fingerprint.
--
-- Why household_id, not user_id: family plans share a household. The abuse
-- pattern is "one household × one track", not "one user × one track".

{% set rlc = var('safety_metrics').thresholds.repeat_listener_concentration %}
{% set cap = var('safety_metrics').severity_cap %}

WITH stream_with_household AS (
    SELECT
        s.track_id,
        u.household_id,
        COUNT(*) AS streams
    FROM {{ ref('stg_synth_streams') }} s
    JOIN {{ ref('stg_synth_users') }} u USING (user_id)
    GROUP BY s.track_id, u.household_id
),

per_track AS (
    SELECT
        track_id,
        SUM(streams) AS total_streams,
        COUNT(*)     AS distinct_households
    FROM stream_with_household
    GROUP BY track_id
),

hhi AS (
    SELECT
        sh.track_id,
        SUM(POWER(CAST(sh.streams AS {{ dbt.type_float() }}) / NULLIF(p.total_streams, 0), 2))
            AS hhi_value,
        MAX(CAST(sh.streams AS {{ dbt.type_float() }}) / NULLIF(p.total_streams, 0))
            AS top_household_share
    FROM stream_with_household sh
    JOIN per_track p USING (track_id)
    GROUP BY sh.track_id
)

SELECT
    h.track_id,
    CAST('track' AS {{ dbt.type_string() }})  AS entity_kind,
    p.total_streams,
    p.distinct_households,
    h.hhi_value,
    h.top_household_share,
    CASE
        WHEN p.total_streams >= {{ rlc.min_streams }}
         AND h.hhi_value     >= {{ rlc.hhi }}
        THEN 1 ELSE 0
    END                                       AS fires,
    LEAST({{ cap }}, h.hhi_value / {{ rlc.hhi }}) AS severity
FROM hhi h
JOIN per_track p USING (track_id)
