view: dsa_decisions {
  sql_table_name: `spry-smithy-489221-p4.cadence.fct_dsa_decisions` ;;
  label: "DSA Decisions"

  dimension: product_line {
    type: string
    sql: ${TABLE}.product_line ;;
  }

  dimension: reporting_period_canonical {
    type: string
    sql: ${TABLE}.reporting_period_canonical ;;
  }

  dimension_group: reporting_period_start {
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.reporting_period_start ;;
  }

  dimension: category_code {
    type: string
    sql: ${TABLE}.category_code ;;
  }

  # ─── Mirrors MetricFlow metrics in models/semantic/transparency_metrics.yml ───

  measure: dsa_decisions_total {
    type: sum
    sql: ${TABLE}.total_decisions ;;
    description: "Total moderation decisions disclosed across the 4 product lines."
  }

  measure: dsa_automated_decisions {
    type: sum
    sql: ${TABLE}.automated_decisions ;;
    description: "Total automated moderation decisions."
  }

  measure: dsa_automated_share {
    type: number
    sql: SAFE_DIVIDE(${dsa_automated_decisions}, ${dsa_decisions_total}) ;;
    value_format_name: percent_2
    description: "Ratio of automated to total decisions. Mirrors MetricFlow `dsa_automated_share`."
  }

  measure: dsa_notices_received {
    type: sum
    sql: ${TABLE}.notices_received ;;
    description: "Total Art. 16 notices received."
  }
}

view: dsa_appeals {
  sql_table_name: `spry-smithy-489221-p4.cadence.fct_dsa_appeals` ;;
  label: "DSA Appeals"

  dimension: product_line {
    primary_key: yes
    type: string
    sql: ${TABLE}.product_line ;;
  }

  dimension: reporting_period_canonical {
    type: string
    sql: ${TABLE}.reporting_period_canonical ;;
  }

  measure: dsa_complaints_submitted {
    type: sum
    sql: ${TABLE}.complaints_submitted ;;
    description: "Internal-complaints-mechanism submissions (Art. 24)."
  }
}
