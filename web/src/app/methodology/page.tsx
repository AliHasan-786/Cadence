import { Suspense } from "react";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CitationChip } from "@/components/citation-chip";
import { citeMethodologyWeight, citeYamlSection } from "@/lib/citations";
import { COMMIT_SHORT, loadSafetyMetrics } from "@/lib/methodology";

export const revalidate = 3600;

const SIGNAL_DESCRIPTIONS: Record<string, string> = {
  listen_spike: "Recent (7-day) streams/day vs prior 83-day baseline. Catches cold-start anomalies + established-track surges.",
  geo_anomaly: "Single-country share of a track's streams + top-country ≠ artist-country. Catches geo-concentrated bot traffic.",
  stream_to_listener_ratio: "Total streams ÷ distinct listeners. High ratios = a small audience replaying many times.",
  repeat_listener_concentration: "HHI of streams across HOUSEHOLDS (not users) — family plans share households.",
  playlist_stuffing: "AI-generated track share within a session ≥ threshold. Session-level signal propagated to tracks.",
};

const PRD_BASELINE: Record<string, number> = {
  listen_spike: 0.25,
  geo_anomaly: 0.2,
  stream_to_listener_ratio: 0.25,
  repeat_listener_concentration: 0.2,
  playlist_stuffing: 0.1,
};

async function MethodologyContent() {
  const { data, source, resolvedPath } = await loadSafetyMetrics();

  return (
    <div className="space-y-12">
      {/* Source-revision banner */}
      <Card className="border-border/60 bg-muted/30 p-4 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <span className="font-mono font-medium">
            commit · <span className="text-[#1DB954]">{COMMIT_SHORT}</span>
          </span>
          <span className="text-muted-foreground">
            rendered from {source === "yaml-file" ? `disk · ${resolvedPath?.split("/").slice(-3).join("/")}` : "baked-in snapshot (Vercel serverless fallback)"}
          </span>
          <span className="ml-auto text-muted-foreground">
            <CitationChip citation={citeYamlSection("safety_metrics.yml")} />
          </span>
        </div>
      </Card>

      {/* Signal weights table */}
      <section>
        <h2 className="text-2xl font-semibold tracking-tight">Detection signal weights</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          The composite suspicion score is{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
            LEAST(100, 100 × Σ fires<sub>i</sub> × weight<sub>i</sub> × severity<sub>i</sub>)
          </code>
          . Weights are tuned so each of the 5 embedded fraud scenarios clears its
          expected minimum score. Deviations from the PRD §8.2 baseline are documented
          here line-by-line — the YAML carries the same notes inline.
        </p>
        <div className="mt-4 overflow-x-auto rounded-lg border border-border/60">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Signal</TableHead>
                <TableHead className="text-xs">Description</TableHead>
                <TableHead className="text-right text-xs">PRD baseline</TableHead>
                <TableHead className="text-right text-xs">Cadence weight</TableHead>
                <TableHead className="text-right text-xs">Δ</TableHead>
                <TableHead className="text-xs">Source</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(data.signal_weights).map(([name, weight]) => {
                const baseline = PRD_BASELINE[name] ?? 0;
                const delta = weight - baseline;
                return (
                  <TableRow key={name}>
                    <TableCell className="font-mono text-xs">{name}</TableCell>
                    <TableCell className="max-w-xs text-xs text-muted-foreground">
                      {SIGNAL_DESCRIPTIONS[name]}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">{baseline.toFixed(2)}</TableCell>
                    <TableCell className="text-right font-mono font-semibold tabular-nums">{weight.toFixed(2)}</TableCell>
                    <TableCell
                      className={`text-right font-mono tabular-nums ${
                        delta > 0 ? "text-[#0a7a30]" : delta < 0 ? "text-red-600" : "text-muted-foreground"
                      }`}
                    >
                      {delta > 0 ? "+" : ""}
                      {delta.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <CitationChip citation={citeMethodologyWeight(name)} />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </section>

      {/* Thresholds */}
      <section>
        <h2 className="text-2xl font-semibold tracking-tight">Signal thresholds</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          What counts as &ldquo;fired&rdquo; for each signal. Severity scales 0-{data.severity_cap} based on how far above the threshold the metric lands.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(data.signal_thresholds).map(([name, thresh]) => (
            <Card key={name} className="border-border/60 p-4">
              <h3 className="font-mono text-xs font-semibold tracking-wide">{name}</h3>
              <dl className="mt-3 space-y-1.5 text-xs">
                {Object.entries(thresh).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3">
                    <dt className="text-muted-foreground">{k}</dt>
                    <dd className="font-mono font-medium tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          ))}
        </div>
      </section>

      {/* Action thresholds */}
      <section>
        <h2 className="text-2xl font-semibold tracking-tight">Action thresholds</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          What the composite score recommends. Above the &ldquo;remove&rdquo; threshold gets routed
          to Compliance Counsel; below the &ldquo;rank-lower&rdquo; threshold means no action.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Card className="border-l-4 border-l-red-500 p-4">
            <h3 className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
              recommend_remove
            </h3>
            <p className="mt-2 font-mono text-2xl font-semibold tabular-nums">≥ {data.action_thresholds.recommend_remove}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Composite score at or above this threshold is queued for human review.
            </p>
          </Card>
          <Card className="border-l-4 border-l-amber-500 p-4">
            <h3 className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
              recommend_rank_lower
            </h3>
            <p className="mt-2 font-mono text-2xl font-semibold tabular-nums">≥ {data.action_thresholds.recommend_rank_lower}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Visibility lowered; no removal. Tracked but not acted on.
            </p>
          </Card>
        </div>
      </section>

      {/* MetricFlow ↔ LookML proof */}
      <section>
        <h2 className="text-2xl font-semibold tracking-tight">Methodology contract — one metric, three sources</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          The composite_suspicion_score metric exists in three places in the repo. They MUST stay
          in sync — the LookML validator (
          <code className="rounded bg-muted px-1 font-mono text-xs">scripts/lookml_validate.py</code>
          ) asserts this on every push.
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <Card className="border-border/60 bg-amber-50/40 p-4 dark:bg-amber-950/20">
            <p className="text-xs font-medium uppercase tracking-wide text-amber-800 dark:text-amber-300">
              (1) YAML config
            </p>
            <p className="mt-2 text-xs text-muted-foreground">models/semantic/safety_metrics.yml</p>
            <pre className="mt-3 overflow-x-auto rounded-md bg-muted/40 p-3 font-mono text-[10px] leading-relaxed">
{`signal_weights:
  listen_spike: ${data.signal_weights.listen_spike}
  geo_anomaly:  ${data.signal_weights.geo_anomaly}
  s2l_ratio:    ${data.signal_weights.stream_to_listener_ratio}
  rlc:          ${data.signal_weights.repeat_listener_concentration}
  playlist:     ${data.signal_weights.playlist_stuffing}`}
            </pre>
          </Card>
          <Card className="border-border/60 bg-blue-50/40 p-4 dark:bg-blue-950/20">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-800 dark:text-blue-300">
              (2) MetricFlow
            </p>
            <p className="mt-2 text-xs text-muted-foreground">semantic_models[].measures</p>
            <pre className="mt-3 overflow-x-auto rounded-md bg-muted/40 p-3 font-mono text-[10px] leading-relaxed">
{`- name: composite_suspicion_score
  type: simple
  type_params:
    measure: composite_suspicion_score_avg
  label: "Composite Suspicion Score"`}
            </pre>
          </Card>
          <Card className="border-border/60 bg-emerald-50/40 p-4 dark:bg-emerald-950/20">
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
              (3) LookML
            </p>
            <p className="mt-2 text-xs text-muted-foreground">looker/views/safety.view.lkml</p>
            <pre className="mt-3 overflow-x-auto rounded-md bg-muted/40 p-3 font-mono text-[10px] leading-relaxed">
{`measure: composite_suspicion_score {
  type: number
  sql: \${composite_suspicion_score_avg}
  description: "Mirrors MetricFlow"
}`}
            </pre>
          </Card>
        </div>
      </section>

      {/* What is NOT measured */}
      <section>
        <h2 className="text-2xl font-semibold tracking-tight">What is NOT measured</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Honest scope boundary. Listed in the methodology YAML alongside everything that{" "}
          <em>is</em> measured.
        </p>
        <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
          {data.what_is_NOT_measured.map((item) => (
            <li key={item} className="flex gap-2">
              <span className="mt-1 inline-block h-1 w-1 shrink-0 rounded-full bg-muted-foreground/40" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:py-14">
      <div className="max-w-3xl">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Methodology
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          Rendered from <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-2xl">safety_metrics.yml</code>
        </h1>
        <p className="mt-3 text-muted-foreground">
          No hand-edits on this page. Every weight, threshold, and methodology note below is read
          live from{" "}
          <CitationChip citation={citeYamlSection("safety_metrics.yml")} /> at build/revalidate
          time. Edit a number in the YAML, push to <code className="font-mono">main</code>, watch
          this page update on next deploy. The Looker dashboards + the dbt models + this page all
          read from the same source — the architectural promise that distinguishes Cadence from a
          portfolio piece with screenshots.
        </p>
      </div>

      <div className="mt-10">
        <Suspense fallback={<Skeleton className="h-[600px] rounded-lg" />}>
          <MethodologyContent />
        </Suspense>
      </div>
    </div>
  );
}
