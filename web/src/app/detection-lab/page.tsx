import Link from "next/link";
import { Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CitationChip } from "@/components/citation-chip";
import { citeDbtModel, citeMethodologyWeight } from "@/lib/citations";
import { getAgreementRates, getScenarioSummaries } from "@/lib/queries";
import { SCENARIOS } from "@/lib/scenarios";

export const revalidate = 3600;

function ScoreBadge({ score, expectedMin }: { score: number; expectedMin: number }) {
  const passed = score >= expectedMin;
  const tone = passed ? "bg-[#1DB954]/15 text-[#0a7a30]" : "bg-amber-50 text-amber-900";
  return (
    <span className={`inline-flex items-baseline gap-1 rounded-md px-2 py-0.5 font-mono text-xs tabular-nums ${tone}`}>
      <span className="text-sm font-semibold">{score.toFixed(0)}</span>
      <span className="opacity-60">/ {expectedMin}+ target</span>
    </span>
  );
}

async function ScenarioCards() {
  const [summaries, agreements] = await Promise.all([getScenarioSummaries(), getAgreementRates()]);
  const summaryMap = Object.fromEntries(summaries.map((s) => [s.scenario_id, s]));
  const agreementMap = Object.fromEntries(agreements.map((a) => [a.scenario_id, a]));

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {SCENARIOS.map((sc) => {
        const summary = summaryMap[sc.id];
        const agreement = agreementMap[sc.id];
        const consensus =
          agreement?.unanimous_agree === 1
            ? "3 of 3 agree"
            : agreement?.two_of_three_agree === 1
              ? "2 of 3 agree"
              : "No majority";
        return (
          <Card key={sc.id} className="border-border/60 p-5 transition hover:border-border">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 text-base font-semibold">
                  <span className="text-xl leading-none">{sc.emoji}</span>
                  <span>{sc.name}</span>
                </div>
                <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {sc.id}
                </p>
              </div>
              <ScoreBadge score={summary?.max_score ?? 0} expectedMin={sc.expectedMinScore} />
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{sc.oneLiner}</p>
            <p className="mt-3 text-xs leading-relaxed">
              <span className="font-medium">Fingerprint:</span>{" "}
              <span className="text-muted-foreground">{sc.fingerprint}</span>
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {sc.expectedSignals.map((s) => (
                <Badge key={s} variant="secondary" className="font-mono text-[10px]">
                  {s}
                </Badge>
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between border-t border-border/40 pt-3 text-xs">
              <span className="text-muted-foreground">
                LLM consensus: <span className="font-medium text-foreground">{consensus}</span>
              </span>
              <Link
                href={`/detection-lab/${sc.id}`}
                className="font-medium text-[#1DB954] hover:underline"
              >
                Drill down →
              </Link>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-60 rounded-lg" />
      ))}
    </div>
  );
}

async function AgreementCallout() {
  const agreements = await getAgreementRates();
  const twoOfThree = agreements.filter((a) => a.two_of_three_agree === 1).length;
  const unanimous = agreements.filter((a) => a.unanimous_agree === 1).length;
  const pct = ((twoOfThree / agreements.length) * 100).toFixed(0);

  return (
    <Card className="border-border/60 bg-muted/30 p-6">
      <div className="grid gap-6 sm:grid-cols-3">
        <div>
          <p className="font-mono text-3xl font-semibold text-[#1DB954] tabular-nums">{pct}%</p>
          <p className="mt-1 text-sm text-muted-foreground">
            of scenarios hit 2-of-3 agreement across Claude / GPT-4o / Gemini
          </p>
        </div>
        <div>
          <p className="font-mono text-3xl font-semibold tabular-nums">{unanimous}/5</p>
          <p className="mt-1 text-sm text-muted-foreground">scenarios where all three providers agreed unanimously</p>
        </div>
        <div className="text-sm leading-relaxed">
          <p>
            The 40% disagreement clusters on bot_ring + ai_fake_artists — where evidence is
            multi-signal rather than obviously bad. <span className="font-medium">Gemini is uniformly aggressive</span>
            , GPT-4o conservative, Claude in the middle. A real argument for multi-LLM
            cross-checking with human escalation.{" "}
            <CitationChip
              citation={citeDbtModel("rpt_llm_agreement_rate", { layer: "marts/llm_ops" })}
            />
          </p>
        </div>
      </div>
    </Card>
  );
}

export default function DetectionLabPage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:py-14">
      <div className="grid gap-8 lg:grid-cols-[2fr_1fr] lg:items-start">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            The Detection Lab
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Five embedded fraud scenarios. Three LLM second-opinions per scenario.
          </h1>
          <p className="mt-3 max-w-3xl text-muted-foreground">
            Synthetic stream-event data with five pre-embedded fraud scenarios — bot ring, AI fake
            artists, family-plan abuse, geographic anomaly, playlist stuffing. Each is detected by
            a composite of 5 signal models, weighted per the methodology YAML, then independently
            evaluated by Claude, GPT-4o, and Gemini. The result: a 60% LLM agreement rate and a
            clear story about <em>where</em> the providers disagree.
          </p>
        </div>
        <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-xs">
          <p className="font-medium text-foreground">Methodology contract</p>
          <p className="mt-2 leading-relaxed text-muted-foreground">
            Every signal weight + threshold below comes from{" "}
            <CitationChip citation={citeMethodologyWeight("composite formula")} />. Edit a number
            in that YAML, push, and{" "}
            <Link href="/methodology" className="underline-offset-2 hover:underline">
              the Methodology page
            </Link>{" "}
            reflects the change on next revalidate.
          </p>
        </div>
      </div>

      <section className="mt-10">
        <Suspense fallback={<Skeleton className="h-32 rounded-lg" />}>
          <AgreementCallout />
        </Suspense>
      </section>

      <section className="mt-10">
        <Suspense fallback={<CardSkeleton />}>
          <ScenarioCards />
        </Suspense>
      </section>
    </div>
  );
}
