/**
 * Methodology source-of-truth loader.
 *
 * Reads models/semantic/safety_metrics.yml at request time (revalidate cached)
 * and returns a typed object the /methodology page can render directly.
 *
 * If the YAML file isn't available on disk (Vercel functions don't have the
 * full repo by default), falls back to a baked-in snapshot that matches the
 * deployed safety_metrics.yml. Document this fallback as honest scope.
 */

import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { z } from "zod";
import yaml from "yaml";

const SafetyMetricsSchema = z.object({
  signal_weights: z.record(z.string(), z.number()),
  signal_thresholds: z.record(z.string(), z.record(z.string(), z.number())),
  action_thresholds: z.object({
    recommend_remove: z.number(),
    recommend_rank_lower: z.number(),
  }),
  severity_cap: z.number(),
  what_is_NOT_measured: z.array(z.string()),
});

export type SafetyMetrics = z.infer<typeof SafetyMetricsSchema>;

// Baked-in snapshot — kept in sync with models/semantic/safety_metrics.yml so
// the page renders even when the YAML file isn't on disk (Vercel serverless).
// The CI check (scripts/lookml_validate.py + a future Sprint 16 sync test) will
// ensure these stay aligned.
const FALLBACK_SNAPSHOT: SafetyMetrics = {
  signal_weights: {
    listen_spike: 0.3,
    geo_anomaly: 0.5,
    stream_to_listener_ratio: 0.3,
    repeat_listener_concentration: 0.4,
    playlist_stuffing: 0.5,
  },
  signal_thresholds: {
    listen_spike: { baseline_multiplier: 10.0, min_baseline_streams_per_day: 0.1 },
    geo_anomaly: { single_country_share: 0.8, min_streams: 100 },
    stream_to_listener_ratio: { threshold: 4.0, min_streams: 200 },
    repeat_listener_concentration: { hhi: 0.2, min_streams: 50 },
    playlist_stuffing: { ai_share: 0.5, min_session_tracks: 5 },
  },
  action_thresholds: { recommend_remove: 70, recommend_rank_lower: 40 },
  severity_cap: 3.0,
  what_is_NOT_measured: [
    "Audio fingerprint similarity (no audio data ingested)",
    "User device-fingerprint depth (only device class — web/ios/android/desktop/tv/speaker — not browser/OS detail)",
    "Historical recidivism by user (not modeled in V1)",
    "Cross-platform fraud markers (MFFA NCFTA shared markers — V1.5)",
    "ML-trained detection (V1 is heuristic + LLM verdicts; V1.4 adds gradient-boosted trees alongside)",
  ],
};

const SEARCH_PATHS = [
  // Local dev: cwd is web/, file lives at ../models/semantic/...
  "../models/semantic/safety_metrics.yml",
  // Some build environments cwd at repo root
  "models/semantic/safety_metrics.yml",
];

export async function loadSafetyMetrics(): Promise<{
  data: SafetyMetrics;
  source: "yaml-file" | "fallback-snapshot";
  resolvedPath?: string;
}> {
  for (const candidate of SEARCH_PATHS) {
    const abs = path.resolve(process.cwd(), candidate);
    try {
      const raw = await fs.readFile(abs, "utf8");
      const parsed = yaml.parse(raw);
      const data = SafetyMetricsSchema.parse(parsed);
      return { data, source: "yaml-file", resolvedPath: abs };
    } catch {
      continue;
    }
  }
  return { data: FALLBACK_SNAPSHOT, source: "fallback-snapshot" };
}

export const COMMIT_SHA = process.env.VERCEL_GIT_COMMIT_SHA ?? process.env.CADENCE_COMMIT_SHA ?? "local";
export const COMMIT_SHORT = COMMIT_SHA.slice(0, 7);
