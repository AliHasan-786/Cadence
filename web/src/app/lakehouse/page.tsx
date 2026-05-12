import { Suspense } from "react";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CitationChip } from "@/components/citation-chip";
import { CrossProductGrid } from "@/components/cross-product-grid";
import { citeDbtModel } from "@/lib/citations";
import { getAutomationPosture, getCrossProductSummary } from "@/lib/queries";

export const revalidate = 3600;

async function HeadlineGrid() {
  const rows = await getCrossProductSummary();
  return <CrossProductGrid rows={rows} />;
}

async function PostureCallout() {
  const rows = await getAutomationPosture();
  const main = rows.find((r) => r.product_line === "main");
  const artists = rows.find((r) => r.product_line === "artists");

  return (
    <Card className="space-y-3 border-border/60 bg-muted/30 p-5 text-sm">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Cross-product automation posture
      </h3>
      <p className="leading-relaxed">
        <span className="font-medium">Main</span> is the only product labeled{" "}
        <em>conservative</em> — {main?.automated_accuracy_pct?.toFixed(2)}% accuracy vs{" "}
        {main?.automated_recall_pct?.toFixed(2)}% recall ({(((main?.automated_accuracy_pct ?? 0) - (main?.automated_recall_pct ?? 0))).toFixed(1)}pp
        accuracy-over-recall). Their automated systems fire less often but are rarely wrong.
      </p>
      <p className="leading-relaxed">
        <span className="font-medium">Artists</span> is the only product labeled{" "}
        <em>aggressive</em> — recall {artists?.automated_recall_pct?.toFixed(2)}% slightly
        exceeds accuracy {artists?.automated_accuracy_pct?.toFixed(2)}%. The systems catch more
        violations at the cost of a few more false positives.
      </p>
      <p className="leading-relaxed text-muted-foreground">
        This is a real policy-shape distinction visible only at the marts layer. The posture label
        lives in {" "}
        <CitationChip
          citation={citeDbtModel("rpt_automated_vs_human", { layer: "marts/transparency" })}
        />
        .
      </p>
    </Card>
  );
}

function GridSkeleton() {
  return (
    <div className="grid gap-4 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-[480px] rounded-lg" />
      ))}
    </div>
  );
}

export default function LakehousePage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:py-14">
      <div className="grid gap-8 lg:grid-cols-[2fr_1fr] lg:items-start">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            The Lakehouse
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Cross-product DSA comparison — Annual 2025
          </h1>
          <p className="mt-3 max-w-3xl text-muted-foreground">
            Four columns, four products, one reporting period. Today, anyone wanting this view
            had to download four XLSX files from Spotify and stitch them manually. Cadence does it
            once: ingest the harmonised templates, type-coerce in dbt staging, union by{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-[10px]">source_product</code>{" "}
            in the intermediate layer, expose at the marts layer with provenance attached. Every
            number resolves to its source.
          </p>
        </div>
      </div>

      <section className="mt-10">
        <Suspense fallback={<GridSkeleton />}>
          <HeadlineGrid />
        </Suspense>
      </section>

      <section className="mt-10 grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3 border-border/60 p-5 text-sm">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            The Creators bombshell
          </h3>
          <p className="leading-relaxed">
            <span className="font-medium">Spotify Creators</span> (the podcast platform, formerly
            Anchor) discloses ~6× the moderation volume of Main on a fifth of the notice intake.
            Almost all of it is own-initiative scanning of the podcast catalog — not user-reported
            content.
          </p>
          <p className="text-muted-foreground">
            This is the kind of cross-product asymmetry the EU harmonised template was designed to
            surface. Cadence is the analytics layer that does the surfacing.
          </p>
        </Card>
        <Suspense fallback={<Skeleton className="h-40 rounded-lg" />}>
          <PostureCallout />
        </Suspense>
      </section>

      <section className="mt-12">
        <h2 className="text-2xl font-semibold tracking-tight">Per-Member-State data</h2>
        <Card className="mt-4 border-amber-200 bg-amber-50 p-5 text-sm leading-relaxed text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
          <p className="font-medium">
            ⚠ Spotify&apos;s 2025 DSA reports do not disclose per-Member-State granularity.
          </p>
          <p className="mt-2">
            All orders received under Art. 17 are aggregated to EU_AGGREGATE rather than broken
            out per Member State. Cadence surfaces this gap honestly rather than fabricating a
            distribution. When/if Spotify discloses per-state data in future reports, the existing
            schema (
            <CitationChip
              citation={citeDbtModel("rpt_member_state_breakdown", { layer: "marts/transparency" })}
            />
            ) will populate automatically — no Cadence-side change needed.
          </p>
        </Card>
      </section>
    </div>
  );
}
