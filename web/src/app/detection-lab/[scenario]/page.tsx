import Link from "next/link";
import { notFound } from "next/navigation";
import { promises as fs } from "node:fs";
import path from "node:path";
import { Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CitationChip } from "@/components/citation-chip";
import { VerdictCard } from "@/components/verdict-card";
import { citeDbtModel, citeMethodologyWeight } from "@/lib/citations";
import { getTopFlaggedTracksByScenario, getVerdictsForScenario } from "@/lib/queries";
import { getScenario, SCENARIOS } from "@/lib/scenarios";

export const revalidate = 3600;

export async function generateStaticParams() {
  return SCENARIOS.map((s) => ({ scenario: s.id }));
}

async function getTranscript(scenarioId: string, provider: string): Promise<string | undefined> {
  // Read the verbatim prompt from precache/fraud_scenarios/llm_verdicts/. Best-effort —
  // the directory is gitignored, so this only resolves when the repo is hydrated.
  const p = path.join(
    process.cwd(),
    "..",
    "precache",
    "fraud_scenarios",
    "llm_verdicts",
    `${scenarioId}_${provider}.json`,
  );
  try {
    const raw = await fs.readFile(p, "utf8");
    return JSON.parse(raw).prompt as string;
  } catch {
    return undefined;
  }
}

async function VerdictRow({ scenarioId }: { scenarioId: string }) {
  const verdicts = await getVerdictsForScenario(scenarioId);
  const transcripts = await Promise.all(
    verdicts.map((v) => getTranscript(scenarioId, v.provider).then((p) => [v.provider, p] as const)),
  );
  const transcriptMap = Object.fromEntries(transcripts);

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {verdicts.map((v) => (
        <VerdictCard key={v.verdict_id} verdict={v} transcriptPrompt={transcriptMap[v.provider]} />
      ))}
    </div>
  );
}

async function TopTracks({ scenarioId }: { scenarioId: string }) {
  const rows = await getTopFlaggedTracksByScenario(scenarioId, 10);
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="text-xs">Track</TableHead>
          <TableHead className="text-center text-xs">ls</TableHead>
          <TableHead className="text-center text-xs">ga</TableHead>
          <TableHead className="text-center text-xs">s2l</TableHead>
          <TableHead className="text-center text-xs">rlc</TableHead>
          <TableHead className="text-center text-xs">ps</TableHead>
          <TableHead className="text-center text-xs">n</TableHead>
          <TableHead className="text-right text-xs">Score</TableHead>
          <TableHead className="text-right text-xs">Action</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.track_id}>
            <TableCell className="font-mono text-xs">{r.track_id}</TableCell>
            <FireCell on={r.listen_spike_fires === 1} />
            <FireCell on={r.geo_anomaly_fires === 1} />
            <FireCell on={r.s2l_ratio_fires === 1} />
            <FireCell on={r.repeat_listener_fires === 1} />
            <FireCell on={r.playlist_stuffing_fires === 1} />
            <TableCell className="text-center font-mono text-xs">{r.n_signals_fired}</TableCell>
            <TableCell className="text-right font-mono text-sm font-semibold">
              {Number(r.composite_suspicion_score).toFixed(1)}
            </TableCell>
            <TableCell className="text-right">
              <Badge
                variant="secondary"
                className={`font-mono text-[10px] ${
                  r.recommended_action === "recommend_remove"
                    ? "bg-red-50 text-red-800"
                    : r.recommended_action === "recommend_rank_lower"
                      ? "bg-amber-50 text-amber-800"
                      : "bg-slate-50 text-slate-700"
                }`}
              >
                {r.recommended_action}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function FireCell({ on }: { on: boolean }) {
  return (
    <TableCell className="text-center">
      <span className={`inline-block h-2 w-2 rounded-full ${on ? "bg-[#1DB954]" : "bg-border"}`} />
    </TableCell>
  );
}

export default async function ScenarioPage({
  params,
}: {
  params: Promise<{ scenario: string }>;
}) {
  const { scenario: scenarioId } = await params;
  const scenario = getScenario(scenarioId);
  if (!scenario) notFound();

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:py-14">
      <Link
        href="/detection-lab"
        className="text-sm text-muted-foreground transition hover:text-foreground"
      >
        ← All scenarios
      </Link>

      <div className="mt-4 flex items-start gap-4">
        <span className="text-4xl leading-none">{scenario.emoji}</span>
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{scenario.name}</h1>
          <p className="mt-1 font-mono text-xs uppercase tracking-widest text-muted-foreground">
            scenario_id: {scenario.id}
          </p>
          <p className="mt-3 max-w-3xl text-muted-foreground">{scenario.oneLiner}</p>
        </div>
      </div>

      <Card className="mt-8 border-border/60 bg-muted/30 p-5 text-sm leading-relaxed">
        <p>
          <span className="font-medium">Fingerprint:</span> {scenario.fingerprint}
        </p>
        <p className="mt-3 text-xs text-muted-foreground">
          Detection signals expected to fire: {" "}
          {scenario.expectedSignals.map((s) => (
            <Badge key={s} variant="secondary" className="ml-1 font-mono text-[10px]">
              {s}
            </Badge>
          ))}
          {" · "}Weights live in {" "}
          <CitationChip citation={citeMethodologyWeight(scenario.expectedSignals[0])} />.
        </p>
      </Card>

      <section className="mt-10">
        <h2 className="text-xl font-semibold tracking-tight">LLM second opinions</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Three providers, one shared prompt, three independent verdicts. Click any card to see
          the verbatim prompt + structured response. The 60% agreement rate across the 5 scenarios
          is the headline LLM-ops metric — captured in {" "}
          <CitationChip citation={citeDbtModel("rpt_llm_agreement_rate", { layer: "marts/llm_ops" })} />.
        </p>
        <div className="mt-5">
          <Suspense fallback={<Skeleton className="h-64 rounded-lg" />}>
            <VerdictRow scenarioId={scenario.id} />
          </Suspense>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-semibold tracking-tight">Per-track signal breakdown</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Top 10 flagged tracks from this scenario&apos;s track set, showing which of the 5
          signals fired on each. Composite score formula:{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">
            LEAST(100, 100 × Σ fires_i × weight_i × severity_i)
          </code>{" "}
          per{" "}
          <CitationChip citation={citeMethodologyWeight("composite formula")} /> {" "}
          and{" "}
          <CitationChip citation={citeDbtModel("fct_artificial_streaming_flags", { layer: "marts/safety" })} />.
        </p>
        <div className="mt-5 overflow-x-auto rounded-lg border border-border/60">
          <Suspense fallback={<Skeleton className="h-64" />}>
            <TopTracks scenarioId={scenario.id} />
          </Suspense>
        </div>
      </section>
    </div>
  );
}
