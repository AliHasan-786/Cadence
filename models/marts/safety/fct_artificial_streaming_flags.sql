{{ config(materialized='table') }}

-- THE composite suspicion-score fact table.
--
-- Grain: one row per track that fires ANY of the 5 detection signals.
-- Weights and thresholds live in models/semantic/safety_metrics.yml (mirrored
-- into dbt_project.yml `vars.safety_metrics`). Edits there, not here.
--
-- Formula (PRD §8 + safety_metrics.yml):
--     composite_score = LEAST(100, 100 × Σ fires_i × weight_i × severity_i)

{% set sm = var('safety_metrics') %}
{% set w  = sm.weights %}
{% set t_remove = sm.action_thresholds.recommend_remove %}
{% set t_lower  = sm.action_thresholds.recommend_rank_lower %}

WITH all_tracks AS (
    -- The track universe = union of any track that any signal saw fire OR not-fire
    SELECT track_id FROM {{ ref('sig_listen_spike') }}
    UNION DISTINCT SELECT track_id FROM {{ ref('sig_geo_anomaly') }}
    UNION DISTINCT SELECT track_id FROM {{ ref('sig_stream_to_listener_ratio') }}
    UNION DISTINCT SELECT track_id FROM {{ ref('sig_repeat_listener_concentration') }}
    UNION DISTINCT SELECT track_id FROM {{ ref('sig_playlist_stuffing') }}
),

ls AS (SELECT track_id, fires AS ls_fires, severity AS ls_sev FROM {{ ref('sig_listen_spike') }}),
ga AS (SELECT track_id, fires AS ga_fires, severity AS ga_sev FROM {{ ref('sig_geo_anomaly') }}),
s2l AS (SELECT track_id, fires AS s2l_fires, severity AS s2l_sev FROM {{ ref('sig_stream_to_listener_ratio') }}),
rlc AS (SELECT track_id, fires AS rlc_fires, severity AS rlc_sev FROM {{ ref('sig_repeat_listener_concentration') }}),
ps  AS (SELECT track_id, fires AS ps_fires,  severity AS ps_sev  FROM {{ ref('sig_playlist_stuffing') }}),

joined AS (
    SELECT
        a.track_id,
        COALESCE(ls.ls_fires,  0)  AS listen_spike_fires,
        COALESCE(ls.ls_sev,    0)  AS listen_spike_severity,
        COALESCE(ga.ga_fires,  0)  AS geo_anomaly_fires,
        COALESCE(ga.ga_sev,    0)  AS geo_anomaly_severity,
        COALESCE(s2l.s2l_fires, 0) AS s2l_ratio_fires,
        COALESCE(s2l.s2l_sev,   0) AS s2l_ratio_severity,
        COALESCE(rlc.rlc_fires, 0) AS repeat_listener_fires,
        COALESCE(rlc.rlc_sev,   0) AS repeat_listener_severity,
        COALESCE(ps.ps_fires,   0) AS playlist_stuffing_fires,
        COALESCE(ps.ps_sev,     0) AS playlist_stuffing_severity
    FROM all_tracks a
    LEFT JOIN ls  USING (track_id)
    LEFT JOIN ga  USING (track_id)
    LEFT JOIN s2l USING (track_id)
    LEFT JOIN rlc USING (track_id)
    LEFT JOIN ps  USING (track_id)
)

SELECT
    j.track_id,
    -- Snapshot time — required by MetricFlow's agg_time_dimension contract.
    -- For V1 this is a synthetic constant matching the synth-data reference
    -- date. Sprint 12's Airflow DAG will replace this with CURRENT_TIMESTAMP()
    -- at build time when snapshots become recurring.
    CAST('2026-05-01 00:00:00' AS {{ dbt.type_timestamp() }}) AS built_at,
    j.listen_spike_fires,
    j.listen_spike_severity,
    j.geo_anomaly_fires,
    j.geo_anomaly_severity,
    j.s2l_ratio_fires,
    j.s2l_ratio_severity,
    j.repeat_listener_fires,
    j.repeat_listener_severity,
    j.playlist_stuffing_fires,
    j.playlist_stuffing_severity,

    j.listen_spike_fires
        + j.geo_anomaly_fires
        + j.s2l_ratio_fires
        + j.repeat_listener_fires
        + j.playlist_stuffing_fires                                    AS n_signals_fired,

    -- Weighted-by-severity composite score, capped at 100
    LEAST(100.0, 100.0 * (
          j.listen_spike_fires      * j.listen_spike_severity     * {{ w.listen_spike }}
        + j.geo_anomaly_fires       * j.geo_anomaly_severity      * {{ w.geo_anomaly }}
        + j.s2l_ratio_fires         * j.s2l_ratio_severity        * {{ w.stream_to_listener_ratio }}
        + j.repeat_listener_fires   * j.repeat_listener_severity  * {{ w.repeat_listener_concentration }}
        + j.playlist_stuffing_fires * j.playlist_stuffing_severity * {{ w.playlist_stuffing }}
    ))                                                                 AS composite_suspicion_score,

    CASE
        WHEN LEAST(100.0, 100.0 * (
              j.listen_spike_fires      * j.listen_spike_severity     * {{ w.listen_spike }}
            + j.geo_anomaly_fires       * j.geo_anomaly_severity      * {{ w.geo_anomaly }}
            + j.s2l_ratio_fires         * j.s2l_ratio_severity        * {{ w.stream_to_listener_ratio }}
            + j.repeat_listener_fires   * j.repeat_listener_severity  * {{ w.repeat_listener_concentration }}
            + j.playlist_stuffing_fires * j.playlist_stuffing_severity * {{ w.playlist_stuffing }}
        )) >= {{ t_remove }}                                           THEN 'recommend_remove'
        WHEN LEAST(100.0, 100.0 * (
              j.listen_spike_fires      * j.listen_spike_severity     * {{ w.listen_spike }}
            + j.geo_anomaly_fires       * j.geo_anomaly_severity      * {{ w.geo_anomaly }}
            + j.s2l_ratio_fires         * j.s2l_ratio_severity        * {{ w.stream_to_listener_ratio }}
            + j.repeat_listener_fires   * j.repeat_listener_severity  * {{ w.repeat_listener_concentration }}
            + j.playlist_stuffing_fires * j.playlist_stuffing_severity * {{ w.playlist_stuffing }}
        )) >= {{ t_lower }}                                            THEN 'recommend_rank_lower'
        ELSE 'no_action'
    END                                                                AS recommended_action
FROM joined j
