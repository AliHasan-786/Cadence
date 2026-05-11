{{ config(materialized='view') }}

-- Signal 5: playlist_stuffing
-- Session-level signal: a session with ≥ min_session_tracks distinct tracks
-- where AI-generated tracks make up ≥ ai_share of the session fires. The
-- signal then propagates to TRACK level — every track participating in a
-- "stuffed" session gets the signal. Track-level entity grain matches the
-- other signals so fct_artificial_streaming_flags can join cleanly.

{% set ps = var('safety_metrics').thresholds.playlist_stuffing %}
{% set cap = var('safety_metrics').severity_cap %}

WITH session_track AS (
    SELECT DISTINCT
        s.session_id,
        s.track_id,
        t.ai_generated_label
    FROM {{ ref('stg_synth_streams') }} s
    JOIN {{ ref('stg_synth_tracks') }} t USING (track_id)
),

session_stats AS (
    SELECT
        session_id,
        COUNT(DISTINCT track_id) AS distinct_tracks,
        SUM(CASE WHEN ai_generated_label THEN 1 ELSE 0 END) AS ai_tracks,
        CAST(SUM(CASE WHEN ai_generated_label THEN 1 ELSE 0 END) AS {{ dbt.type_float() }})
            / NULLIF(COUNT(DISTINCT track_id), 0) AS ai_share
    FROM session_track
    GROUP BY session_id
),

stuffed_sessions AS (
    SELECT
        session_id,
        distinct_tracks,
        ai_tracks,
        ai_share,
        LEAST({{ cap }}, ai_share / {{ ps.ai_share }}) AS severity
    FROM session_stats
    WHERE distinct_tracks >= {{ ps.min_session_tracks }}
      AND ai_share        >= {{ ps.ai_share }}
)

-- Track-level output: every track that participated in any stuffed session.
-- If a track sits in multiple stuffed sessions, take the max severity.
SELECT
    st.track_id,
    CAST('track' AS {{ dbt.type_string() }})            AS entity_kind,
    MAX(ss.distinct_tracks)                              AS session_distinct_tracks,
    MAX(ss.ai_tracks)                                    AS session_ai_tracks,
    MAX(ss.ai_share)                                     AS session_ai_share,
    1                                                    AS fires,
    MAX(ss.severity)                                     AS severity
FROM session_track st
JOIN stuffed_sessions ss USING (session_id)
GROUP BY st.track_id
