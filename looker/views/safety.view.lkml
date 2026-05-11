view: artificial_streaming_signals {
  sql_table_name: `spry-smithy-489221-p4.cadence.fct_artificial_streaming_flags` ;;
  label: "Artificial Streaming Signals"

  dimension: track_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.track_id ;;
  }

  dimension: recommended_action {
    type: string
    sql: ${TABLE}.recommended_action ;;
  }

  dimension: n_signals_fired {
    type: number
    sql: ${TABLE}.n_signals_fired ;;
  }

  dimension: composite_suspicion_score_raw {
    hidden: yes
    type: number
    sql: ${TABLE}.composite_suspicion_score ;;
  }

  # ─────────────────────────────────────────────────────────────────────
  # Measures — MUST match models/semantic/safety_metrics.yml metric names.
  # If you rename a measure here, update the semantic YAML too (or use
  # scripts/sync_lookml_from_yaml.py to regenerate this file).
  # ─────────────────────────────────────────────────────────────────────

  measure: composite_suspicion_score_avg {
    type: average
    sql: ${TABLE}.composite_suspicion_score ;;
    value_format_name: decimal_1
    description: "Mean composite suspicion score across flagged tracks."
  }

  measure: composite_suspicion_score_max {
    type: max
    sql: ${TABLE}.composite_suspicion_score ;;
    value_format_name: decimal_1
    description: "Max composite suspicion score in the cohort."
  }

  measure: n_flagged_tracks {
    type: count
    description: "Distinct tracks in the flagged set."
  }

  measure: composite_suspicion_score {
    type: number
    sql: ${composite_suspicion_score_avg} ;;
    description: "Canonical metric — Cadence's 0-100 composite. Mirrors MetricFlow metric `composite_suspicion_score`."
  }
}
