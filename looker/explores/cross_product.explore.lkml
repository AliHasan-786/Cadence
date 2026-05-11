explore: cross_product_summary {
  view_name: dsa_decisions
  label: "Cross-Product DSA Summary"
  description: "Headline view — backs the Looker Studio Executive Summary dashboard."

  join: dsa_appeals {
    type: left_outer
    sql_on: ${dsa_decisions.product_line} = ${dsa_appeals.product_line}
         AND ${dsa_decisions.reporting_period_canonical} = ${dsa_appeals.reporting_period_canonical} ;;
    relationship: many_to_one
  }
}

explore: detection_lab {
  view_name: artificial_streaming_signals
  label: "Detection Lab"
  description: "Per-track suspicion scores joined to LLM verdicts."

  join: llm_verdicts {
    type: left_outer
    sql_on: ${artificial_streaming_signals.track_id} = ${llm_verdicts.verdict_id} ;;  -- placeholder join
    relationship: one_to_many
  }
}
