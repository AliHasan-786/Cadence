import Link from "next/link";
import { Suspense } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CitationChip } from "@/components/citation-chip";
import { StatCard } from "@/components/stat-card";
import {
  citeDbtModel,
  citeMethodologyWeight,
  citeSpotifyTransparencyHub,
  citeSpotifyXlsx,
} from "@/lib/citations";
import { getHomeStatCards } from "@/lib/queries";

export const revalidate = 3600;

async function StatGrid() {
  const stats = await getHomeStatCards();
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {stats.map((s, i) => (
        <StatCard key={s.label} {...s} tone={i === 0 ? "accent" : "default"} />
      ))}
    </div>
  );
}

function StatGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-28 rounded-lg" />
      ))}
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-12 lg:py-20">
      {/* Hero */}
      <section className="grid gap-10 lg:grid-cols-[1.3fr_1fr] lg:items-start">
        <div>
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border/60 bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-[#1DB954]" /> Spotify DSA Transparency · Annual 2025
          </div>
          <h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            The analytics engineering layer{" "}
            <span className="text-[#1DB954]">Spotify&apos;s DSA reports</span> deserve.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Today, anyone wanting to compare moderation activity across Spotify Main, Artists,
            Authors, and Creators has to download four XLSX files and stitch them together by hand.
            Cadence does it once — in BigQuery, modeled through dbt, validated by 219 tests,
            governed by a methodology source-of-truth, and exposed through three surfaces:
            this dashboard, a researcher API, and a synthetic-data Detection Lab.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              href="/lakehouse"
              className={cn(buttonVariants(), "bg-[#1DB954] text-black hover:bg-[#1DB954]/90")}
            >
              View cross-product comparison →
            </Link>
            <a
              href="https://cadence-ashen.vercel.app/docs"
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ variant: "outline" })}
            >
              Try the researcher API ↗
            </a>
            <Link href="/detection-lab" className={buttonVariants({ variant: "ghost" })}>
              Explore the Detection Lab →
            </Link>
          </div>
        </div>

        {/* Right-rail mini callout */}
        <Card className="space-y-4 border-border/60 bg-muted/30 p-6 text-sm">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            The headline
          </h3>
          <p className="leading-relaxed">
            Across Spotify&apos;s four product lines:{" "}
            <span className="font-mono font-medium tabular-nums">927k+</span> moderation
            decisions on{" "}
            <span className="font-mono font-medium tabular-nums">78k</span> notices received in
            annual 2025.{" "}
            <CitationChip citation={citeDbtModel("rpt_cross_product_summary", { layer: "marts/transparency" })} />
          </p>
          <p className="leading-relaxed">
            Creators is <span className="font-medium">6× the decision volume of Main</span> on a
            fifth of the notice intake — almost all own-initiative scanning of the podcast catalog
            (Anchor). The cross-product comparison only surfaces this with the marts layer in place.
          </p>
          <div className="border-t border-border/40 pt-4 text-xs text-muted-foreground">
            Every number on every page resolves via these inline chips to either the dbt model
            that produced it, the Spotify-published XLSX, or the methodology weight in the YAML.
            Click any chip to verify the provenance.
          </div>
        </Card>
      </section>

      {/* Stat cards */}
      <section className="mt-14">
        <Suspense fallback={<StatGridSkeleton />}>
          <StatGrid />
        </Suspense>
      </section>

      {/* Why this exists */}
      <section className="mt-16 grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="text-2xl font-semibold tracking-tight">Why this exists</h2>
          <div className="mt-4 space-y-4 leading-relaxed text-muted-foreground">
            <p>
              Spotify publishes <span className="font-medium text-foreground">four separate</span>{" "}
              DSA Transparency Reports — one for each EU-designated intermediary service: Main,
              Artists, Authors, Creators. Each is a PDF introduction plus a 9-sheet XLSX
              quantitative annex.{" "}
              <CitationChip citation={citeSpotifyTransparencyHub()} />{" "}
              <CitationChip citation={citeSpotifyXlsx("main")} />
            </p>
            <p>
              HIIG&apos;s December 2025 analysis concluded that &ldquo;current transparency reports
              fall short of delivering true accountability&rdquo; and that &ldquo;each platform
              has interpreted the DSA specifications independently.&rdquo; Even within a single
              platform like Spotify with four reports, cross-product comparison today requires
              manual reconciliation — the categories overlap but don&apos;t match, the column
              schemas differ between sheets, and the metadata about who reviewed what is buried.
            </p>
            <p>
              The 2025 reports are the <span className="font-medium text-foreground">first</span>{" "}
              under the EU&apos;s harmonised Implementing Regulation 2024/2835, effective 1 July
              2025. The four sheets are now structurally identical — same column headers, same
              row counts. That makes a unified analytics layer finally tractable. Cadence is what
              that looks like built properly.
            </p>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
            What runs underneath
          </h3>
          <ul className="mt-4 space-y-2 text-sm leading-relaxed">
            <li>
              <span className="font-mono text-xs text-muted-foreground">warehouse</span> ·
              BigQuery (production) + DuckDB (local dev)
            </li>
            <li>
              <span className="font-mono text-xs text-muted-foreground">transform</span> · dbt-core
              1.8, 50+ models, 219 tests
            </li>
            <li>
              <span className="font-mono text-xs text-muted-foreground">semantic</span> ·
              MetricFlow + LookML, parity-validated
            </li>
            <li>
              <span className="font-mono text-xs text-muted-foreground">api</span> · FastAPI on
              Vercel, OpenAPI 3.1, audit log
            </li>
            <li>
              <span className="font-mono text-xs text-muted-foreground">frontend</span> · Next.js
              15 server components, ISR
            </li>
            <li>
              <span className="font-mono text-xs text-muted-foreground">llm</span> · Claude /
              GPT-4o / Gemini verdicts modeled into the warehouse
            </li>
          </ul>
        </div>
      </section>

      {/* Three CTAs in detail */}
      <section className="mt-16 grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 p-6">
          <h3 className="font-semibold tracking-tight">1. The Lakehouse</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Cross-product comparison of all four DSA reports. Side-by-side numbers, automation
            posture, the Creators-vs-Main asymmetry, every metric inspectable.
          </p>
          <div className="mt-4 text-xs text-muted-foreground">
            Powered by{" "}
            <CitationChip citation={citeDbtModel("rpt_cross_product_summary", { layer: "marts/transparency" })} />
          </div>
          <Link
            href="/lakehouse"
            className="mt-3 inline-flex text-sm font-medium text-[#1DB954] hover:underline"
          >
            Open the Lakehouse →
          </Link>
        </Card>

        <Card className="border-border/60 p-6">
          <h3 className="font-semibold tracking-tight">2. The Detection Lab</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Five embedded fraud scenarios on synthetic stream data. Composite suspicion scores,
            LLM verdicts from three providers, full transcripts. The 60% agreement rate is the
            story.
          </p>
          <div className="mt-4 text-xs text-muted-foreground">
            Weights from{" "}
            <CitationChip citation={citeMethodologyWeight("composite formula")} />
          </div>
          <Link
            href="/detection-lab"
            className="mt-3 inline-flex text-sm font-medium text-[#1DB954] hover:underline"
          >
            Open the Detection Lab →
          </Link>
        </Card>

        <Card className="border-border/60 p-6">
          <h3 className="font-semibold tracking-tight">3. The Researcher API</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            DSA Article 40 operationalised. 9 endpoints, OpenAPI 3.1 Swagger UI, citation block on
            every response, rate-limited audit log to BigQuery.
          </p>
          <div className="mt-4 text-xs text-muted-foreground">
            Live at{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.7rem]">
              cadence-ashen.vercel.app
            </code>
          </div>
          <a
            href="https://cadence-ashen.vercel.app/docs"
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex text-sm font-medium text-[#1DB954] hover:underline"
          >
            Open the Swagger UI ↗
          </a>
        </Card>
      </section>
    </div>
  );
}
