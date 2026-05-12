/**
 * Static metadata for the 5 embedded fraud scenarios. The data values come from
 * BigQuery; this file holds the human-friendly descriptions and signal-mapping
 * that's stable across runs.
 */

export type ScenarioMeta = {
  id: string;
  emoji: string;
  name: string;
  oneLiner: string;
  fingerprint: string;
  expectedSignals: string[];
  expectedMinScore: number;
};

export const SCENARIOS: ScenarioMeta[] = [
  {
    id: "bot_ring",
    emoji: "🤖",
    name: "Bot Ring",
    oneLiner: "200 fake users in PL stream the same 50 tracks 5 times each over 7 days.",
    fingerprint: "Listen-spike + geo-anomaly + stream-to-listener ratio fire on every target track.",
    expectedSignals: ["listen_spike", "geo_anomaly", "stream_to_listener_ratio"],
    expectedMinScore: 80,
  },
  {
    id: "ai_fake_artists",
    emoji: "🎭",
    name: "AI Fake Artists",
    oneLiner: "5 new artists, 30 AI-generated tracks released ≤7 days ago, 250 listeners drive 10k+ streams.",
    fingerprint: "Cold-start listen-spike fires hard; same artist country as listeners so geo doesn't fire.",
    expectedSignals: ["listen_spike"],
    expectedMinScore: 75,
  },
  {
    id: "family_plan_abuse",
    emoji: "👨‍👩‍👧‍👦",
    name: "Family-Plan Abuse",
    oneLiner: "One household, 5 users on a family plan, 120 plays on one niche track in 24h.",
    fingerprint: "Repeat-listener concentration (HHI=1.0 by household) + listen-spike + s2l ratio all fire.",
    expectedSignals: ["repeat_listener_concentration", "listen_spike"],
    expectedMinScore: 70,
  },
  {
    id: "geographic_anomaly",
    emoji: "🌍",
    name: "Geographic Anomaly",
    oneLiner: "US-registered artist, 10 tracks, 83% of streams come from Japan.",
    fingerprint: "Geo-anomaly fires hard (top-country ≠ artist-country, 83% share). Listen-spike doesn't fire (streams spread over 30 days).",
    expectedSignals: ["geo_anomaly"],
    expectedMinScore: 75,
  },
  {
    id: "playlist_stuffing",
    emoji: "📋",
    name: "Playlist Stuffing",
    oneLiner: "One user plays 20 lo-fi tracks back-to-back in one session; 16 of 20 are AI-generated.",
    fingerprint: "Playlist-stuffing signal alone (session ai_share = 80% ≥ 50% threshold). Weighted heavy in YAML to clear 80 from one signal.",
    expectedSignals: ["playlist_stuffing"],
    expectedMinScore: 80,
  },
];

export function getScenario(id: string): ScenarioMeta | null {
  return SCENARIOS.find((s) => s.id === id) ?? null;
}
