view: llm_verdicts {
  sql_table_name: `spry-smithy-489221-p4.cadence.fct_llm_verdicts` ;;
  label: "LLM Verdicts"

  dimension: verdict_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.verdict_id ;;
  }

  dimension: scenario_id {
    type: string
    sql: ${TABLE}.scenario_id ;;
  }

  dimension: provider {
    type: string
    sql: ${TABLE}.provider ;;
  }

  dimension: llm_recommendation {
    type: string
    sql: ${TABLE}.llm_recommendation ;;
  }

  dimension: heuristic_action {
    type: string
    sql: ${TABLE}.heuristic_action ;;
  }

  dimension: status {
    type: string
    sql: ${TABLE}.status ;;
  }

  dimension_group: requested_at {
    type: time
    timeframes: [time, date, week, month]
    sql: ${TABLE}.requested_at ;;
  }

  # ─── Mirrors MetricFlow metrics in safety_metrics.yml + llm_ops_metrics.yml ───

  measure: n_verdicts {
    type: count
    description: "Total verdicts (all statuses)."
  }

  measure: llm_total_cost_usd {
    type: sum
    sql: ${TABLE}.cost_usd ;;
    value_format_name: usd
    description: "Total spend on LLM verdicts. Mirrors MetricFlow `llm_total_cost_usd`."
  }

  measure: llm_mean_latency_ms {
    type: average
    sql: ${TABLE}.latency_ms ;;
    value_format_name: decimal_0
    filters: [status: "ok"]
    description: "Mean latency across OK verdicts. Mirrors MetricFlow `llm_mean_latency_ms`."
  }

  measure: llm_heuristic_agreement_count {
    type: sum
    sql: ${TABLE}.llm_agrees_with_heuristic ;;
    description: "Number of OK verdicts where LLM matched Cadence heuristic action."
  }

  # ─── Derived metrics — mirror MetricFlow's llm_ops_metrics.yml `derived` block ───

  measure: llm_provider_uptime {
    type: number
    sql: SAFE_DIVIDE(
      COUNTIF(${TABLE}.status = 'ok'),
      COUNT(*)
    ) ;;
    value_format_name: percent_2
    description: "Share of attempted verdicts that returned OK. Mirrors MetricFlow `llm_provider_uptime`."
  }

  measure: llm_verdict_agreement_rate {
    type: number
    sql: SAFE_DIVIDE(
      SUM(${TABLE}.llm_agrees_with_heuristic),
      COUNT(*)
    ) ;;
    value_format_name: percent_2
    description: "Share of OK verdicts that match the heuristic action. Mirrors MetricFlow `llm_verdict_agreement_rate`."
  }
}
