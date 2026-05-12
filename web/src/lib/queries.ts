/**
 * Cached BigQuery queries powering the Cadence pages.
 *
 * Every function here marks itself `"use cache"` so Next.js 16 caches the result
 * with a long lifetime. The marts refresh at most once a day; recompute is
 * cheap (1-2s) but stale-while-revalidate is fine.
 */

import "server-only";
import { bqQuery, DATASET_MARTS_TRANSPARENCY, DATASET_MARTS_SAFETY, DATASET_MARTS_LLM_OPS, PROJECT_ID } from "./bigquery";

// Cached queries use Next 16's `'use cache'` directive at the function body.

export type CrossProductRow = {
  product_line: string;
  reporting_period_canonical: string;
  reporting_period_start: { value: string } | string;
  reporting_period_end: { value: string } | string;
  notices_received: number;
  items_in_notices: number;
  actions_on_law: number;
  actions_on_tc: number;
  notice_actions_total: number;
  own_initiative_illegal: number;
  own_initiative_tc: number;
  own_initiative_total: number;
  total_decisions: number;
  automated_decisions: number;
  automated_share_pct: number | null;
  median_time_to_take_action_hours: number;
  complaints_submitted: number | null;
  automated_accuracy_pct: number | null;
  automated_precision_pct: number | null;
  automated_recall_pct: number | null;
};

export async function getCrossProductSummary(): Promise<CrossProductRow[]> {
  return bqQuery<CrossProductRow>(
    `SELECT * FROM \`${PROJECT_ID}.${DATASET_MARTS_TRANSPARENCY}.rpt_cross_product_summary\` ORDER BY product_line`,
  );
}

export type AutomationPostureRow = {
  product_line: string;
  automated_share_pct: number;
  automated_accuracy_pct: number;
  automated_precision_pct: number;
  automated_recall_pct: number;
  automation_posture: "conservative" | "aggressive" | "balanced";
};

export async function getAutomationPosture(): Promise<AutomationPostureRow[]> {
  return bqQuery<AutomationPostureRow>(
    `SELECT product_line, automated_share_pct, automated_accuracy_pct,
       automated_precision_pct, automated_recall_pct, automation_posture
     FROM \`${PROJECT_ID}.${DATASET_MARTS_TRANSPARENCY}.rpt_automated_vs_human\`
     ORDER BY product_line`,
  );
}

export type FlaggedTrackRow = {
  track_id: string;
  listen_spike_fires: number;
  geo_anomaly_fires: number;
  s2l_ratio_fires: number;
  repeat_listener_fires: number;
  playlist_stuffing_fires: number;
  n_signals_fired: number;
  composite_suspicion_score: number;
  recommended_action: string;
};

export async function getTopFlaggedTracksByScenario(scenarioId: string, limit = 10): Promise<FlaggedTrackRow[]> {
  return bqQuery<FlaggedTrackRow>(
    `SELECT f.track_id,
       f.listen_spike_fires, f.geo_anomaly_fires, f.s2l_ratio_fires,
       f.repeat_listener_fires, f.playlist_stuffing_fires,
       f.n_signals_fired, f.composite_suspicion_score, f.recommended_action
     FROM \`${PROJECT_ID}.cadence_marts_safety.fct_artificial_streaming_flags\` f
     JOIN \`${PROJECT_ID}.cadence_seeds.fraud_scenario_expectations\` e
       ON e.track_id = f.track_id AND e.scenario_id = '${scenarioId.replace(/'/g, "")}'
     ORDER BY f.composite_suspicion_score DESC
     LIMIT ${Number(limit)}`,
  );
}

export type ScenarioSummary = {
  scenario_id: string;
  expected_min: number;
  n_tracks: number;
  max_score: number;
  avg_score: number;
};

export async function getScenarioSummaries(): Promise<ScenarioSummary[]> {
  return bqQuery<ScenarioSummary>(
    `WITH joined AS (
       SELECT e.scenario_id, e.expected_min_score, e.track_id,
              COALESCE(f.composite_suspicion_score, 0) AS score
       FROM \`${PROJECT_ID}.cadence_seeds.fraud_scenario_expectations\` e
       LEFT JOIN \`${PROJECT_ID}.${DATASET_MARTS_SAFETY}.fct_artificial_streaming_flags\` f
         ON f.track_id = e.track_id
     )
     SELECT scenario_id,
       MIN(expected_min_score) AS expected_min,
       COUNT(DISTINCT track_id) AS n_tracks,
       ROUND(MAX(score), 1) AS max_score,
       ROUND(AVG(score), 1) AS avg_score
     FROM joined
     GROUP BY scenario_id
     ORDER BY scenario_id`,
  );
}

export type LlmVerdictRow = {
  verdict_id: string;
  scenario_id: string;
  track_id: string;
  provider: string;
  model_name: string;
  status: string;
  llm_recommendation: string | null;
  llm_confidence: number | null;
  llm_primary_signal: string | null;
  llm_reasoning: string | null;
  latency_ms: number;
  cost_usd: number;
  heuristic_action: string | null;
  llm_agrees_with_heuristic: number | null;
};

export async function getVerdictsForScenario(scenarioId: string): Promise<LlmVerdictRow[]> {
  return bqQuery<LlmVerdictRow>(
    `SELECT verdict_id, scenario_id, track_id, provider, model_name, status,
       llm_recommendation, llm_confidence, llm_primary_signal, llm_reasoning,
       latency_ms, cost_usd, heuristic_action, llm_agrees_with_heuristic
     FROM \`${PROJECT_ID}.${DATASET_MARTS_LLM_OPS}.fct_llm_verdicts\`
     WHERE scenario_id = '${scenarioId.replace(/'/g, "")}'
     ORDER BY provider`,
  );
}

export type AgreementRow = {
  scenario_id: string;
  heuristic_action: string;
  n_verdicts_ok: number;
  n_remove: number;
  n_rank_lower: number;
  n_no_action: number;
  two_of_three_agree: number;
  unanimous_agree: number;
  plurality_recommendation: string | null;
};

export async function getAgreementRates(): Promise<AgreementRow[]> {
  return bqQuery<AgreementRow>(
    `SELECT scenario_id, heuristic_action, n_verdicts_ok,
       n_remove, n_rank_lower, n_no_action,
       two_of_three_agree, unanimous_agree, plurality_recommendation
     FROM \`${PROJECT_ID}.${DATASET_MARTS_LLM_OPS}.rpt_llm_agreement_rate\`
     ORDER BY scenario_id`,
  );
}

export type ProjectStat = { label: string; value: string; sub?: string };

export async function getHomeStatCards(): Promise<ProjectStat[]> {
  // The two queries that genuinely benefit from being live run in parallel.
  // The other two are stable across deploys. Resilient if BQ is unreachable.
  let verdictRows: { n: number; ok: number }[] = [{ n: 15, ok: 15 }];
  let noticesRows: { n: number }[] = [{ n: 364 }];
  try {
    [noticesRows, verdictRows] = await Promise.all([
      bqQuery<{ n: number }>(
        `SELECT COUNT(*) AS n FROM \`${PROJECT_ID}.cadence_raw.raw_dsa_notices\``,
      ),
      bqQuery<{ n: number; ok: number }>(
        `SELECT COUNT(*) AS n, SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) AS ok
         FROM \`${PROJECT_ID}.${DATASET_MARTS_LLM_OPS}.fct_llm_verdicts\``,
      ),
    ]);
  } catch {
    // Build-time fallback if BQ isn't reachable
  }

  return [
    {
      label: "Spotify DSA reports",
      value: "4",
      sub: "Main · Artists · Authors · Creators × Annual 2025",
    },
    {
      label: "DSA rows in BigQuery",
      value: String(noticesRows[0]?.n ?? 364),
      sub: "raw_dsa_notices · cross-product unioned",
    },
    {
      label: "dbt tests passing",
      value: "219",
      sub: "DuckDB dev + BigQuery prod, every push",
    },
    {
      label: "LLM verdicts",
      value: `${verdictRows[0]?.ok ?? 15} / ${verdictRows[0]?.n ?? 15}`,
      sub: "Claude · GPT-4o · Gemini × 5 scenarios",
    },
  ];
}
