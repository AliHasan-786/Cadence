# Cadence — Product Requirements Document v3

> **A unified analytics engineering platform that ingests Spotify's actual published Trust & Safety transparency data — across all four product lines (Main, Spotify for Artists, Spotify for Authors, Spotify for Creators) — into a tested BigQuery + dbt warehouse, surfaces it through Looker Studio dashboards and a Next.js + TypeScript frontend, exposes it via a researcher API operationalizing the DSA Article 40 data-access obligation, and pairs it with an artificial-streaming detection lab on synthetic data.**
>
> **Cadence solves a problem that exists today: Spotify's DSA reports are published as PDFs and XLSX files with no cross-product reconciliation, no time-series continuity, and no machine-readable standardization until the EU's harmonised template kicked in mid-2025. Researchers, regulators, and Spotify's own legal/policy teams have to read four separate documents to answer cross-product questions. Cadence is the analytics engineering layer that should exist on top.**

---

| | |
|---|---|
| **Project Owner** | Ali Hasan |
| **Target Roles** | Spotify, Associate Analytics Engineer (T&S) + Analytics Engineer, T&S Infrastructure |
| **Status** | Spec — ready for Claude Code execution |
| **Deployment Targets** | BigQuery (free tier) · Astro/Airflow local + Cloud Composer if scaled · Looker Studio (free) · Vercel · GitHub Pages (dbt docs) · Vercel (researcher API) |
| **The Standard** | Spotify would want to ingest this into their internal stack. Real data, real tools, real value. |
| **Tagline** | *"The analytics engineering layer Spotify's DSA reports deserve."* |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Problem — Real, Verified, Spotify-Specific](#2-the-problem--real-verified-spotify-specific)
3. [The Product — Three Surfaces, One Warehouse](#3-the-product--three-surfaces-one-warehouse)
4. [Strategy: Personas, Stories, Success Metrics, Scope](#4-strategy-personas-stories-success-metrics-scope)
5. [Senior Design: IA, Pages, Recruiter Path](#5-senior-design-ia-pages-recruiter-path)
6. [Senior Engineering: Architecture, Tech Stack, Repo Structure](#6-senior-engineering-architecture-tech-stack-repo-structure)
7. [Data Sources: Real Spotify DSA + Synthetic Streaming](#7-data-sources-real-spotify-dsa--synthetic-streaming)
8. [The Methodology Contract](#8-the-methodology-contract)
9. [BI Governance Layer](#9-bi-governance-layer)
10. [Multi-LLM Analytics Module](#10-multi-llm-analytics-module)
11. [The Researcher API — DSA Article 40 in Practice](#11-the-researcher-api--dsa-article-40-in-practice)
12. [Implementation Plan for Claude Code](#12-implementation-plan-for-claude-code)
13. [Acceptance Criteria — The Acquisition Bar](#13-acceptance-criteria--the-acquisition-bar)
14. [What Cadence is NOT](#14-what-cadence-is-not)
15. [Sources & Citations](#15-sources--citations)

---

## 1. Executive Summary

### What Cadence Is, Concretely
Cadence is a working analytics product with three user-facing surfaces sitting on top of one shared BigQuery + dbt warehouse:

1. **The Unified DSA Lakehouse** — ingests the four published Spotify DSA Transparency Reports (Main, Artists, Authors, Creators) plus prior reporting periods, normalizes them through 50+ tested dbt models, and exposes them through 3 deployed Looker Studio dashboards + a polished Next.js frontend. Solves the cross-product data-disconnect problem documented by HIIG and arxiv researchers.

2. **The Researcher API** — a FastAPI endpoint operationalizing DSA Article 40's "researcher access" obligation, with rate limiting, audit logging, schema documentation, and a public OpenAPI spec. Demonstrates what good Article 40 implementation could look like.

3. **The Artificial Streaming Detection Lab** — a synthetic-data testbed for the five public detection signals (listen-spike, geo-anomaly, stream-to-listener ratio, repeat-listener concentration, playlist stuffing) modeled into the same warehouse alongside an LLM-verdict feed. Demonstrates the same architecture handles operational T&S detection, not just regulatory reporting.

Underneath: BigQuery as the warehouse, dbt-core for transformations, MetricFlow + LookML as parallel semantic layers, Airflow (Astro CLI local + Cloud Composer–ready) as the orchestrator, GitHub Actions CI, dbt-expectations + custom tests for validation, Looker Studio dashboards published from BigQuery, a Next.js + TypeScript app on Vercel for the rich interactive frontend (the same stack as the candidate's AgentRadar portfolio piece), FastAPI on Vercel for the researcher endpoint.

### Why Now
The EU's Implementing Regulation 2024/2835, in force since 1 July 2025, standardized DSA transparency reporting templates across providers. The first harmonised reports were published in February 2026 — including [Spotify's 2025 DSA Transparency Report](https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_introduction_spotify) dated 27 February 2026. Spotify publishes four separate reports (one per product line) as PDF + XLSX. Cross-product analysis requires manual stitching. A properly modeled lakehouse fixes this once.

### Why It Maps to Both JDs
Spotify's [Associate Analytics Engineer (T&S)](https://jobs.lever.co/spotify/d95e1989-9a1a-4853-95b1-ecdebf5f81ff) JD asks for: dbt, SQL, Python, control versioning, validation frameworks, semantic layers, regulatory reporting, platform safety monitoring, cross-functional translation, data definitions, documentation standards.

Spotify's [Analytics Engineer, T&S Infrastructure](https://jobs.lever.co/spotify/54ab7173-774b-410b-a05d-5746ab78632f) JD adds: **BigQuery, Airflow/Flyte, Looker/Tableau, BI governance best practices, advanced SQL, self-service analytics ecosystems, monitoring frameworks with structured escalation paths**.

Cadence ships every named technology as a working artifact. Not a stub, not a mention in skills — a deployable, recruiter-clickable product surface backed by each tool.

### What Makes This Acquisition-Grade
- **Real data, real value.** Spotify's actual DSA XLSX reports are ingested. The unified output is something Spotify's own legal team would benefit from internally.
- **Real tools, real configs.** BigQuery has a working dataset. Airflow has DAG files that run. Looker Studio has a published dashboard URL. Not theatrical.
- **Three surfaces, one source of truth.** Every metric in the Looker dashboards, the Next.js frontend, and the researcher API resolves back to the same dbt model + tests.
- **DSA Article 40 implemented, not described.** The researcher API is real, with OpenAPI docs, rate limits, and audit logging. Demonstrates what good Article 40 implementation looks like — something many VLOPs are still figuring out.
- **Engineering rigor.** Pre-commit hooks, sqlfluff + ruff + mypy, dbt-expectations, Write-Audit-Publish, GitHub Actions CI on every PR, dbt docs deployed, methodology rendered from source.
- **Honest scope.** Synthetic data is clearly labeled as synthetic. Real data is clearly attributed. What Cadence cannot do is documented in §14.

---

## 2. The Problem — Real, Verified, Spotify-Specific

### 2.1 Spotify's Current Transparency Reporting Architecture (Documented)

Spotify publishes [four separate DSA Transparency Reports](https://www.spotify.com/us/safetyandprivacy/transparency) for its four EU-designated intermediary services:

| Product line | What it covers | Format published |
|---|---|---|
| Spotify Main | The core music streaming service in the EU | PDF Introduction + XLSX quantitative annex |
| Spotify for Artists | The artist-facing platform (profile management, analytics, tools) | PDF Introduction + XLSX quantitative annex |
| Spotify for Authors | Audiobook author platform | PDF Introduction + XLSX quantitative annex |
| Spotify for Creators | Podcast creator platform (Anchor successor) | PDF Introduction + XLSX quantitative annex |

The 2025 reports were published 27 February 2026, conforming to the [EU's harmonised Implementing Regulation 2024/2835](https://digital-strategy.ec.europa.eu/en/news/commission-harmonises-transparency-reporting-rules-under-digital-services-act) effective 1 July 2025. Prior reports (2024 and earlier) used Spotify's older custom format.

### 2.2 The Data-Disconnect Gap (Documented Externally)

**HIIG (Humboldt Institute for Internet & Society), December 2025:** Their [analysis of the DSA's transparency reports](https://www.hiig.de/en/analysis-of-the-dsas-transparency-reports/) concluded that *"current transparency reports fall short of delivering true accountability with regard to the moderation of illegal content,"* and that *"each platform has interpreted the DSA specifications independently"* — meaning even within a platform like Spotify with four reports, cross-product comparison requires manual reconciliation.

**arxiv 2312.10269** (Tessa et al., 2024, peer-reviewed in PACM HCI): A systematic audit of the DSA Transparency Database vs. platforms' own transparency reports concluded that *"a remarkable fraction of the database data is inconsistent"* and that *"the platforms exhibited substantial differences in their moderation actions"* — establishing that the cross-platform analytical value of these reports today is severely limited.

**arxiv 2506.04145** (Tessa, Amram, Monreale, Cresci, June 2025): Proposes formal *Transparency Report Cross-Checking* and *Verification* processes that the DSA framework structurally lacks. Cadence operationalizes a version of this for Spotify's four-product structure.

**TechPolicy.Press, July 2024:** A 19-VLOP comparative analysis found *"significant disparities remain in the granularity, consistency, and standardization of disclosures across platforms,"* with a specific gap in *"the composition of content moderation teams, their language skills, or the specifics of their training regimes."*

### 2.3 Why an Analytics Engineering Solution

The fix is canonical analytics engineering applied to a real data set:
- **One ingestion layer** parses the four published XLSX files into raw tables.
- **A staging layer** types and renames columns, deduplicates, applies referential integrity.
- **An intermediate layer** unions equivalent metrics across products (e.g., "appeals received" exists in all four reports but with different column names).
- **A marts layer** delivers cross-product fact tables, time-series-aware dimension tables, and pre-built reporting views matching the EU harmonised template.
- **A semantic layer** (MetricFlow + LookML) makes every metric self-service.
- **A test suite** enforces consistency invariants (e.g., totals across products reconcile to disclosed aggregates).
- **A documentation layer** (dbt docs) makes lineage navigable.

This is the canonical analytics engineering value proposition. Cadence proves it on real data.

### 2.4 The Artificial Streaming Side of T&S (Verified Real Pain Point)

Beyond regulatory reporting, Spotify's other major T&S workstream is artificial streaming fraud, where the operational stakes are visible in their public disclosures:

- **75 million tracks removed** from Spotify in the 12 months before September 2025 — explicitly tied to *"the explosion of generative AI tools"* — per Spotify's [official announcement](https://www.musicbusinessworldwide.com/spotify-has-deleted-75m-spammy-tracks-as-it-unveils-new-ai-music-policies/) covering their three-pronged AI policy update.
- **$1B (2014) → $10B (2024)** Spotify total music payouts — Spotify's own framing: *"Big payouts entice bad actors. Left unchecked, these behaviors can dilute the royalty pool and impact attention for artists playing by the rules."*
- **Zero-tolerance enforcement** since April 2024 with a [€10/track penalty](https://support.fuga.com/hc/en-us/articles/36690008503700-Understanding-Spotify-s-Artificial-Streaming-Penalty-and-FUGA-s-Enforcement-Policy) charged to distributors.
- **Music Fights Fraud Alliance** founded June 2023 — Spotify and Amazon Music are the two digital service providers; the other founders are nine distributors (CD Baby + Downtown, TuneCore + Believe, DistroKid, UnitedMasters, Symphonic, EMPIRE, Vydia). 2025 expansion added YouTube Music, SoundCloud, Meta, Merlin, ONErpm, STEM, Revelator, Too Lost. Coordinates with NCFTA on a [shared fraud markers database](https://www.musicbusinessworldwide.com/merlin-joins-music-fights-fraud-alliance-to-tackle-streaming-fraud/).
- **Documented attack taxonomy** ([HUMAN Security, January 2026](https://www.humansecurity.com/learn/blog/ai-powered-streaming-fraud/)): residential proxies + VPNs + Selenium/Puppeteer + AI-generated tracks → *"scalable, high-volume fraud infrastructure that clients can hire […] to siphon royalties from the platform's pro-rata shared pool."*

### 2.5 The Five Public Detection Signals

Per HUMAN Security and corroborating industry research, the five public detection signals for artificial streaming are:

1. Listen spikes without promotional explanation
2. Abnormal listener geography (single-country concentration without targeting)
3. High stream-to-listener ratios on otherwise unknown artists
4. Repeat-streaming concentration (especially Family/Duo plan abuse)
5. Playlist stuffing (e.g., "Rainy Day Lo-Fi") with AI-generated tracks beside legitimate ones — explicitly named in HUMAN Security's research

Cadence operationalizes these signals as dbt models against synthetic data with embedded fraud scenarios, demonstrating the same warehouse handles both regulatory reporting and operational detection.

### 2.6 Why Solving Both Together Matters

Both workstreams flow from the same upstream events (stream events, user actions, moderation decisions, appeals). Both require the same downstream guarantees (auditability, lineage, validation, self-service). One unified dbt project that powers both is exactly the leverage an Analytics Engineer creates. The senior JD's emphasis on *"data ecosystems that power regulatory reporting, internal analytics, and self-service tools"* is literally this.


---

## 3. The Product — Three Surfaces, One Warehouse

### 3.1 Surface One — The Unified DSA Lakehouse

**The headline value proposition:** today, anyone wanting to compare moderation activity across Spotify Main vs Artists vs Authors vs Creators has to download four separate XLSX files, manually align column schemas, deduplicate categories, and rebuild totals. Cadence does this once, automatically, and surfaces the result through three interfaces:

- A **Looker Studio dashboard** (deployed, public URL) for executive-style consumption
- A **Next.js + TypeScript frontend** (deployed on Vercel) for the rich interactive product surfaces — recruiter-playable, no demo required
- The **dbt docs site** (deployed) for engineers who want to see lineage, tests, and documentation

The Lakehouse covers (V1):
- All four 2025 reports (Spotify's first harmonised template reports, Feb 2026 publication)
- All available 2024 reports (legacy template — for time-series continuity)
- Standardized cross-product metric definitions
- Quarter-over-quarter delta calculations
- Per-EU-Member-State breakdowns where reported
- Automated vs. human-in-the-loop decision split tracking
- Appeals lifecycle modeling (received → reviewed → upheld/reversed)

### 3.2 Surface Two — The Researcher API (DSA Article 40)

**Why this exists:** [DSA Article 40](https://digital-strategy.ec.europa.eu/en/policies/dsa-brings-transparency) creates a legal obligation for VLOPs to give vetted researchers access to publicly available platform data for studying systemic risks. The Commission adopted the [delegated act on data access](https://digital-strategy.ec.europa.eu/en/news/commission-harmonises-transparency-reporting-rules-under-digital-services-act) in July 2025. Most VLOPs are still figuring out the implementation. Cadence shows what good Article 40 implementation looks like for transparency-report-derived data.

**What it provides:**
- A FastAPI service deployed on Vercel (free tier)
- Public OpenAPI 3.1 spec at `/openapi.json` and Swagger UI at `/docs`
- Endpoints for filtered DSA data queries (by product, by reporting period, by category, by Member State)
- Researcher-key authentication (free, instantly issued via the website)
- Rate limiting (100 requests / 15 minutes per key)
- Audit logging (every query logged to BigQuery as a fact table — meta-auditability)
- Citation guidance — every response includes the dbt model + commit hash that generated the data

**Why this matters for the application:** the senior JD explicitly mentions *"structured escalation paths"* and *"validation frameworks that enable performance tracking, early detection of issues."* The audit logging on the researcher API demonstrates exactly this pattern.

### 3.3 Surface Three — The Artificial Streaming Detection Lab

**Why this exists:** the regulatory reporting side proves Cadence handles real, public, regulatory-grade data. The detection lab proves the same architecture handles operational, near-real-time T&S detection workloads — which is the other half of what a Spotify T&S Analytics Engineer touches.

**What it provides:**
- Synthetic stream-event data (~5M rows) generated deterministically via pydantic-validated generators
- Five fraud scenarios pre-embedded (one per HUMAN Security signal)
- All five detection signals modeled as dbt sources (`sig_listen_spike`, `sig_geo_anomaly`, `sig_stream_to_listener_ratio`, `sig_repeat_listener_concentration`, `sig_playlist_stuffing`)
- A composite suspicion-score model (`fct_artificial_streaming_flags`) with weights stored in `safety_metrics.yml` (rendered into the Methodology page from source)
- An LLM-verdict feed: pre-cached responses from Claude + GPT-4o + Gemini for each flagged track, ingested as a dbt source so agreement metrics, drift detection, cost analytics, and latency distributions become first-class measures in the semantic layer
- A `/detection-lab` route in the Next.js app showing the five scenarios with click-through to the data flow and the LLM verdicts

**Critical reframing from v2:** the multi-LLM piece is no longer a real-time orchestration UI. It's *modeled data*. The LLM verdicts are a SOURCE that flows through staging → marts and surfaces as analytics measures (agreement_rate, mean_latency_ms, total_cost_usd, drift_score). This is what an analytics engineer would actually build for an LLM-powered moderation pipeline.

### 3.4 What Ties the Three Together

All three surfaces query the same BigQuery dataset, transformed by the same dbt project, governed by the same semantic layer, refreshed by the same Airflow DAG, and tested by the same CI pipeline. Single source of truth. Three interfaces. That's the architectural promise.

---

## 4. Strategy: Personas, Stories, Success Metrics, Scope

### 4.1 Personas (Real Stakeholders + The Recruiter)

**Persona 1 — Priya, Spotify T&S Compliance Counsel (Legal)**
- *Job:* Sign off on DSA transparency reports before publication; respond to EU regulator inquiries; certify cross-product consistency.
- *Today's pain:* Four reports, four spreadsheets, manual reconciliation, no audit trail showing which dbt model produced which figure.
- *Cadence value:* Every figure on the Looker dashboard has a "view source" affordance opening the dbt model name, the SQL, the test status, the commit hash, and the timestamp. Audit trail by construction.

**Persona 2 — Miguel, Spotify Policy Manager**
- *Job:* Set and refine moderation policy across the four product lines. Notice trends. Recommend changes.
- *Today's pain:* Wants to know if Authors content moderation has different patterns from Main. Today, that's a manual spreadsheet exercise.
- *Cadence value:* Cross-product comparison dashboard. Click any metric → drill into product-by-product breakdowns + per-Member-State splits + automated-vs-human ratios.

**Persona 3 — Sam, Spotify T&S Engineer**
- *Job:* Operate the automated moderation systems; tune detection rules; investigate edge cases.
- *Today's pain:* Wants to validate detection logic against clean, well-modeled data — not raw event logs.
- *Cadence value:* dbt DAG view with all tests passing; the Detection Lab page showing five fraud scenarios with full lineage; the LLM verdict feed modeled into the warehouse with agreement rates and drift signals as first-class metrics.

**Persona 4 — Dr. Anders, Academic Researcher (DSA Article 40)**
- *Job:* Studying platform moderation patterns under the DSA framework for a peer-reviewed paper.
- *Today's pain:* Has to download Spotify's four PDFs, four XLSX files, parse manually, no way to track over time, no API access, has to email Spotify's legal team for any deeper data.
- *Cadence value:* Researcher API with one-click key issuance, OpenAPI spec, rate limits, audit logging. Can query DSA data programmatically with citation-ready references.

**Persona 5 — The Spotify Hiring Manager / Recruiter (the playable user)**
- *Job:* Decide if Ali can do this role.
- *Today's pain:* Most analytics engineering portfolios are toy CRUD apps. They want to see real data, real tools, real value, on day one.
- *Cadence value:* Lands on a homepage explaining a Spotify-specific problem with cited evidence. Clicks "View the Q4 2025 cross-product comparison" — sees a Looker Studio dashboard backed by BigQuery. Navigates the Next.js frontend — every page renders server-side with BigQuery data, every metric inspectable. Clicks "Try the Researcher API" — Swagger UI loads, query returns data with attribution. Clicks "Detection Lab" — sees five fraud scenarios with LLM verdict analytics. **No demo required. No setup required. The product just works.**

### 4.2 User Stories

> **As Spotify T&S Counsel,** I want to compare moderation activity across our four DSA-reported products in a single view, so I can certify that disclosed totals reconcile across reports before external publication.

> **As Spotify Policy Manager,** I want to see how the percentage of automated decisions has changed across products from H1 2024 → H1 2025, so I can identify which products need policy adjustments.

> **As Spotify Policy Manager,** I want to filter moderation actions by EU Member State + policy category + reporting period + product line, with the underlying SQL visible.

> **As a Spotify T&S Engineer,** I want every detection signal to be a tested dbt model with documented inputs/outputs, so I have confidence in the data layer powering enforcement decisions.

> **As an external researcher,** I want a programmatic API to query Spotify DSA data with rate limits, audit logs, and citation guidance — so my published research is reproducible.

> **As a Spotify Hiring Manager,** I want to evaluate this candidate's analytics engineering work without having to clone a repo or watch a demo video — the deployed product should speak for itself in under three minutes.

### 4.3 Success Metrics (each measurable in the deployed app)

| Metric | Target | Where it lives |
|---|---|---|
| dbt models built | **50+** | dbt docs site |
| dbt tests passing | **200+** | CI run + Tests panel |
| Spotify DSA reports ingested (real) | **8 minimum** (4 products × 2 reporting periods) | Lakehouse page |
| Cross-product reconciliations validated | **5+ assertions** | Custom tests |
| Looker Studio dashboards published | **3** (Cross-Product, Trend, Member State) | Live URLs in About page |
| Researcher API endpoints | **6** (data, schema, citations, time-series, member-state, audit) | Swagger UI |
| Researcher API documented in OpenAPI | **100% endpoints** | `/openapi.json` |
| LLM providers in verdict feed | **3+** (Anthropic, OpenAI, Google) | Detection Lab |
| Synthetic fraud scenarios pre-flagged | **5** | Detection Lab |
| Airflow DAG tasks | **8+** (extract → load → dbt deps → dbt build → dbt test → publish docs → refresh dashboards → notify) | Airflow UI screenshots in repo |
| BigQuery tables/views published | **20+** | BigQuery console |
| LookML files | **15+** (views, explores, models, dashboards as code) | `looker/` directory |
| Recruiter setup time | **0 seconds** (deployed) | Landing page links |
| Time-to-first-insight | **<60 seconds** | App design goal |
| GitHub Actions main branch CI | **green** | Repo badge |
| Citations rendered inline | **≥1 per data-driven UI section** | Throughout |

### 4.4 Scope (V1 — what we are building)

**In scope:**
- Real Spotify DSA report ingestion (4 products × 2+ reporting periods, Excel parsing pipeline, robust to schema variation)
- BigQuery dataset (free tier; project named `cadence-public`)
- dbt project with staging/intermediate/marts, sources, tests, exposures, documentation, snapshots for slowly-changing dimensions
- MetricFlow semantic layer + parallel LookML semantic layer (both genuinely deployed)
- Looker Studio dashboards (3, deployed publicly via Looker Studio's free tier, backed by BigQuery)
- Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui + Recharts frontend (deployed on Vercel)
- FastAPI researcher endpoint (deployed on Vercel)
- Airflow DAG (Astro CLI for local dev; Cloud Composer-ready manifest)
- Synthetic stream-event data generator with five fraud scenarios
- LLM verdict pre-cache (Claude + GPT-4o + Gemini, real API calls, persisted to BigQuery)
- Methodology page rendered from source
- BI governance documentation page
- GitHub Actions CI: dbt build + tests + sqlfluff + ruff + mypy on every PR
- Pre-commit hooks
- Single-command setup verified on a clean machine

**Out of scope (deliberately, to keep V1 shippable):**
- Real Spotify event-level data (synthetic only — clearly labeled)
- Production-scale (free tier limits respected; design supports scaling)
- Authentication beyond researcher API key (no OAuth, no user management)
- Real-time streaming ingestion (the DSA reports are biannual; the orchestration pattern supports incremental refreshes when new reports drop)
- Mobile-optimized layouts (verify mobile-readable but don't redesign for it)
- Multilingual UI (English only)

### 4.5 Anti-Goals

- ❌ No theatrical CI badges that aren't wired to real CI
- ❌ No "use BigQuery" claims that resolve to a SQLite database in disguise
- ❌ No Looker mockups built in the Next.js frontend — actually deploy Looker Studio dashboards backed by BigQuery
- ❌ No fake Airflow that's just a Python script — actual Airflow DAG, scheduled, with task dependencies
- ❌ No claim that Cadence uses real Spotify event data — only published DSA report data is real; event-level is synthetic
- ❌ No Spotify trade dress beyond a single accent color used sparingly
- ❌ No claim Cadence is a Spotify product, endorsed by Spotify, or representing Spotify's views
- ❌ No "log in to see more" walls


---

## 5. Senior Design: IA, Pages, Recruiter Path

### 5.1 Design Principles

1. **Real over rendered.** When the page says "BigQuery," it means a working BigQuery dataset behind the chart. When it says "Looker," it means a published Looker Studio dashboard URL.
2. **Context first, controls second.** Every page opens with one paragraph explaining what this view is and why a Spotify employee or external researcher would care.
3. **Citations live where the claim lives.** Inline chips, not a buried About page.
4. **Show your work.** Every chart, table, and metric has a "view source dbt model" affordance.
5. **Three-minute rule.** A reviewer who arrives cold should reach a meaningful insight within three minutes without setup, narration, or demo.
6. **Calm hierarchy.** Black, white, subtle Spotify-green accents. No animations, no scroll hijacking.
7. **Honest scope.** If something is synthetic, it's labeled synthetic. If a free-tier limit constrains scale, it's documented.

### 5.2 Visual Design System & Implementation

The frontend is **Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + Recharts**, deployed to Vercel. Same stack as [AgentRadar](https://agent-radar-one.vercel.app) and the rest of the candidate's deployed APM portfolio (`profound-ai-strategy`, `samsara-apm`, `stripe-apm`, `bumble-apm`, `promptplay-ai`, `ad-signal`).

**Design tokens** (defined as CSS custom properties in `web/src/styles/globals.css` and as Tailwind theme extensions in `web/tailwind.config.ts`):

```
--primary:         #1DB954  /* Spotify green — CTAs, accents only */
--background:      #FFFFFF
--ink:             #191414  /* Spotify black — primary text */
--ink-secondary:   #535353
--divider:         #E5E5E5
--success:         #1DB954
--warning:         #FFA42B
--danger:          #E22134
--info:            #1E40AF
--citation-chip:   #F3F4F6 / #1F2937  /* bg / fg */

Typography:        Geist Sans (body) + Geist Mono (code), system fallbacks
Heading scale:     H1 32 / H2 24 / H3 18 / Body 14 / Mono 13
Chart palette:     Black-and-green-led monochrome with one accent per chart
Spacing rhythm:    Tailwind 4-unit base, generous on landing, dense on data tables
Motion:            framer-motion only for purposeful transitions (no decorative animation)
```

**shadcn/ui components used** (installed via `pnpm dlx shadcn@latest add ...`): `button`, `card`, `dialog`, `table`, `accordion`, `badge`, `tabs`, `tooltip`, `popover`, `dropdown-menu`, `select`, `input`, `label`, `separator`, `skeleton`, `sheet`, `chart`. Each is a Radix primitive styled with Tailwind, owned in our codebase under `web/src/components/ui/` — no library lock-in, full customization.

**Charts:** Recharts for time-series + bar + composite, react-plotly.js for the choropleth, @xyflow/react for the dbt DAG visualization, mermaid for the lineage + governance diagrams, shiki for SQL code-block syntax highlighting.

**State + data fetching:** server components by default (Next.js App Router), TanStack Query for client-side cache where interactive (Detection Lab drilldowns), Zod for runtime validation at every boundary.

**Accessibility:** All shadcn/ui primitives are Radix-based (WAI-ARIA compliant by default). Color contrast verified WCAG AA. Keyboard navigation tested in Playwright. No information conveyed by color alone.

### 5.3 Information Architecture

```
HOME
├── 1. The Lakehouse — Cross-Product DSA Analytics
│   ├── 1A. Cross-Product Comparison (the headline)
│   ├── 1B. Quarter-over-Quarter Trends
│   ├── 1C. Per-Member-State Breakdown
│   └── 1D. Live Looker Studio Dashboards (3 deployed URLs)
├── 2. Detection Lab — Artificial Streaming
│   ├── 2A. Five Pre-Flagged Scenarios
│   ├── 2B. Detection Signal Drilldown
│   ├── 2C. LLM Verdict Analytics (modeled, not orchestrated)
│   └── 2D. Methodology Rendering
├── 3. Researcher API — DSA Article 40 in Practice
│   ├── 3A. API Documentation (OpenAPI)
│   ├── 3B. Get a Researcher Key
│   ├── 3C. Live Query Sandbox
│   └── 3D. Citation Guidance
├── 4. Self-Service Explorer
│   ├── 4A. MetricFlow Metrics Browser
│   ├── 4B. Dimension Picker
│   └── 4C. Saved Views
├── 5. Analyst Console
│   ├── 5A. dbt DAG (interactive)
│   ├── 5B. Test Results Panel (live)
│   ├── 5C. Model Catalogue
│   ├── 5D. Column Lineage
│   └── 5E. Airflow DAG visualization
├── 6. Methodology — Rendered from Source
│   ├── 6A. Detection Signal Weights
│   ├── 6B. Metric Definitions (from MetricFlow + LookML)
│   ├── 6C. dbt Model Inventory (from manifest.json)
│   └── 6D. What is NOT measured
├── 7. BI Governance
│   ├── 7A. Certified Metric Registry
│   ├── 7B. Owner Attribution
│   ├── 7C. Deprecation Policy
│   ├── 7D. Naming Conventions
│   └── 7E. Change Management Workflow
├── 8. Teardown — Strategic Landscape
│   ├── 8A. The Regulatory Cliff (DSA + harmonised template)
│   ├── 8B. Spotify's Stack vs. Cadence's Stack
│   ├── 8C. The Wedge — what Cadence does that nothing else does
│   └── 8D. Out of scope and why
└── 9. About
    ├── 9A. Problem context (cited)
    ├── 9B. Architecture diagram (Mermaid)
    ├── 9C. JD Mapping Table (explicit)
    ├── 9D. Author + role context
    └── 9E. All deployed URLs in one place
```

### 5.4 Page-by-Page Specifications

#### Home / Landing

**Above the fold:**
- App name "Cadence" + tagline: *"The analytics engineering layer Spotify's DSA reports deserve."*
- 4 quick-stat cards (live counts, refreshed from BigQuery):
  - "8 Spotify DSA reports ingested (Main, Artists, Authors, Creators × 2 reporting periods)"
  - "53 dbt models, 217 tests passing"
  - "3 Looker Studio dashboards live"
  - "Researcher API: 6 endpoints, 1.2k queries audited"
- Primary CTA: "View the cross-product DSA dashboard" (links to deployed Looker Studio)
- Secondary CTA: "Try the researcher API" (links to Swagger UI)
- Tertiary CTA: "Explore the Detection Lab" (`/detection-lab` route)

**Below the fold:**
- "Why this exists" — 3-paragraph problem statement with inline citations to HIIG, arxiv, Spotify's own DSA report
- "How it works" — 3-card explainer (Ingest → Model → Surface)
- "Tools used (each working, each clickable)" — BigQuery + dbt + Airflow + Looker Studio + Next.js + FastAPI badges, each linking to live evidence
- Footer: "Built by Ali Hasan as a Trust & Safety analytics engineering portfolio piece. Real DSA data sourced from Spotify's public publications. Synthetic streaming data clearly labeled. Source: github.com/AliHasan-786/cadence."

#### Page 1A — Cross-Product Comparison (the headline view)

**The killer view.** A single-page comparison no one currently provides for Spotify DSA data.

- Top: reporting period selector (default: 2025 H2 = the Feb 2026 publication, the first harmonised report)
- 4 columns side-by-side: Main / Artists / Authors / Creators
- Per column:
  - Total moderation actions
  - Automated vs human split (donut)
  - Top 3 policy categories (badge chips)
  - Appeals received → resolved → upheld/reversed (sankey-lite)
  - Median time to act (box plot)
  - EU Member State coverage (sparkline of top 5)
- At the bottom: a reconciliation panel showing whether totals across products satisfy expected invariants (e.g., appeals received ≥ appeals resolved)
- Every number has a 🔍 affordance opening dbt model + SQL + test status

#### Page 1B — Quarter-over-Quarter Trends

- Time-series chart: total moderation decisions across the four reporting periods we have data for
- Stacked area chart: automation rate trend per product
- Annotated callouts pointing at meaningful moments ("July 2025: EU harmonised template adopted")
- Period-over-period delta table

#### Page 1C — Per-Member-State Breakdown

- Choropleth of EU Member States colored by moderation activity (where Spotify reports it)
- Click a Member State → drilldown panel with category breakdown
- Note: Spotify's DSA reports vary in Member State granularity — Cadence transparently shows where data is available vs. not

#### Page 1D — Live Looker Studio Dashboards

A page listing the three published Looker Studio dashboards with embedded thumbnails and the public URLs. Each one is a working, free-tier-deployed dashboard backed by the same BigQuery dataset:

1. **Cross-Product Executive Summary** — for Counsel & VPs
2. **Operational Trends** — for Policy Managers
3. **Member-State Heatmap** — for EU regulator-facing inquiries

#### Page 2 — Detection Lab

Per the v2 design but with the multi-LLM piece reframed:

**2A. Five Pre-Flagged Scenarios** (cards):
- 🤖 Bot Ring
- 🎭 AI-Generated Fake Artists
- 👨‍👩‍👧‍👦 Family-Plan Abuse
- 🌍 Geographic Anomaly
- 📋 Playlist Stuffing — explicitly named in HUMAN Security's research as "Rainy Day Lo-Fi" and other lo-fi/focus playlists

**2B. Detection Signal Drilldown** — click a scenario, see:
- The signals that fired (badge chips with weights)
- The composite suspicion score (0–100)
- Time-series of streams with the embedded fraud event annotated
- The flagged tracks and their distributors
- The dbt models powering the detection (with view-source affordance)

**2C. LLM Verdict Analytics — Modeled as Data**

This is the reframing from v2. Instead of a real-time orchestration UI, this page shows what an analytics engineer would build on top of an LLM moderation pipeline:
- A dbt fact table `fct_llm_verdicts` storing every LLM call (timestamp, provider, prompt_hash, verdict, confidence, latency_ms, input_tokens, output_tokens, cost_usd)
- Surfaced metrics from the semantic layer:
  - Agreement rate across providers (per scenario, per signal)
  - Mean / p95 latency by provider
  - Cost per verdict by provider
  - Drift score (week-over-week verdict-distribution shift)
  - Provider availability uptime
- A "view a single track's verdict transcripts" affordance — opens a modal with all three providers' verbatim prompts and responses

This is what the JD's *"performance tracking, early detection of issues, and structured escalation paths"* actually looks like applied to LLM ops.

**2D. Methodology Rendering** — links to Page 6.

#### Page 3 — Researcher API

**3A. API Documentation** — embedded Swagger UI from the deployed FastAPI service. All endpoints documented, all schemas typed, all examples runnable in-browser.

**3B. Get a Researcher Key** — a form. Submit name + institutional affiliation + research purpose + email. Receive a key instantly (free, rate-limited at 100 req / 15 min). Real, not theatrical.

**3C. Live Query Sandbox** — a code playground showing example Python and curl invocations. Click "Run" → executes against the live API → shows real response.

**3D. Citation Guidance** — every API response includes a `citation` field with: dbt model name, manifest commit hash, data refresh timestamp, suggested BibTeX entry. Researchers can cite Cadence-served data with full provenance.

#### Page 4 — Self-Service Explorer

- MetricFlow metric picker (uses semantic layer)
- Dimension picker (multi-select)
- Filter pane (date range, product, Member State, category)
- Live chart + data table
- "Show compiled SQL" toggle revealing the SQL the semantic layer generated

#### Page 5 — Analyst Console

- 5 tabs: DAG / Tests / Models / Lineage / Airflow
- **DAG tab:** rendered from `target/manifest.json` as an interactive Mermaid diagram
- **Tests tab:** parsed from `target/run_results.json`; sortable, filterable
- **Models tab:** searchable catalogue with descriptions, columns, types, materialization
- **Lineage tab:** column-level lineage (via `dbt-column-lineage-extractor`)
- **Airflow tab:** screenshot of the live Airflow UI + the DAG file rendered as code

#### Page 6 — Methodology (Rendered from Source)

The architectural promise: this page's content is generated from machine-readable source. No hand-edits.

Source files read at render time:
- `models/semantic/safety_metrics.yml` (signal weights, thresholds)
- `target/manifest.json` (dbt model inventory)
- `target/run_results.json` (test status)
- `looker/cadence.model.lkml` (LookML metric definitions)
- `dbt_project.yml` (project config)
- Git HEAD (commit hash, timestamp)

Render four sections:
- **6A.** Detection Signal Weights table — every weight + threshold + current pass rate
- **6B.** Metric Definitions table — every MetricFlow + LookML metric with formula
- **6C.** dbt Model Inventory — every model with description, materialization, current test status
- **6D.** What is NOT measured — explicit list of intentional omissions

#### Page 7 — BI Governance

This is the page that addresses the senior JD's *"BI governance best practices"* requirement. It documents:

- **7A. Certified Metric Registry** — table of "blessed" metrics: name, definition, owner, certification date, downstream consumers, change-control workflow
- **7B. Owner Attribution** — every metric has a named owner (Compliance Counsel, Policy Manager, T&S Engineer, etc.) and a backup owner
- **7C. Deprecation Policy** — three-stage workflow (Deprecated → Sunset → Removed), with timelines
- **7D. Naming Conventions** — `dim_*`, `fct_*`, `rpt_*`, `sig_*`, `int_*`, `stg_*` patterns and their semantics
- **7E. Change Management Workflow** — how a Policy Manager requests a metric change, how the AE reviews, how downstream is notified, how the LookML and dbt model are versioned

#### Page 8 — Teardown

Strategic landscape argument.

- **8A. The Regulatory Cliff** — DSA Articles 15, 24, 40, 42 + the harmonised Implementing Regulation 2024/2835 + the Feb 2026 first-harmonised reports + what's coming next (cited)
- **8B. Spotify's Stack vs. Cadence's Stack** — public Spotify engineering posts confirm BigQuery + Flyte/Airflow + Looker (cited from senior JD); Cadence runs on the same stack at portfolio scale
- **8C. The Wedge** — three things Cadence does that nothing publicly available does today: cross-product DSA unification, Article 40 researcher API in practice, LLM-verdict-modeled-as-data
- **8D. Out of scope and why** — parallel to §14

#### Page 9 — About

- **9A.** Problem context (cited)
- **9B.** Architecture diagram (Mermaid)
- **9C.** Explicit JD Mapping Table — every requirement in both JDs mapped to a Cadence feature
- **9D.** Author + role context
- **9E.** All deployed URLs in one place: BigQuery dataset, Looker Studio (×3), Next.js app, FastAPI researcher API, dbt docs, GitHub repo, GH Actions

### 5.5 The Recruiter Path (the playable journey)

```
0:00  Land on Home. Read tagline. See 4 stat cards refreshing from BigQuery in real time.
0:15  Click "View the cross-product DSA dashboard"
0:18  Looker Studio dashboard loads. See Spotify Main vs Artists vs Authors vs Creators
      side-by-side for the Feb 2026 reporting period. Real numbers from real reports.
0:35  Click any number → drill panel showing the dbt model + SQL + test status.
0:55  Navigate back. Click "Try the researcher API."
1:00  Swagger UI loads. Click "Try it out" on `/dsa/cross-product` endpoint.
      Returns real JSON in <1 second.
1:20  Navigate to "Detection Lab."
1:25  Click "AI-Generated Fake Artists" scenario.
1:35  See 30 fake tracks flagged, weighted score = 87/100, signals firing.
1:45  Click "view LLM verdicts" for one track. See Claude + GPT-4o + Gemini
      verdicts side-by-side with verbatim transcripts.
2:00  Navigate to "Methodology." See every weight rendered from YAML.
2:15  Navigate to "BI Governance." See certified metric registry, owner attribution,
      deprecation policy.
2:35  Navigate to "Analyst Console" → click "Airflow tab" → see DAG diagram +
      live UI screenshot.
2:50  Navigate to "About" → JD Mapping Table — every JD requirement crossed off.
3:00  Reviewer has formed an opinion. They forward this URL to the hiring panel.
```

The bar: the Looker Studio dashboard, the Researcher API, and the dbt docs are all *links the recruiter can verify exist on the public internet, backed by real BigQuery data, refreshed by real Airflow DAGs.* Nothing theatrical.


---

## 6. Senior Engineering: Architecture, Tech Stack, Repo Structure

### 6.1 System Architecture

```
                                  ┌────────────────────────────────────┐
                                  │  Spotify's published DSA reports   │
                                  │  (4 products × 2+ periods, XLSX)   │
                                  │  fetched from spotify.com          │
                                  └─────────────┬──────────────────────┘
                                                │
                  ┌─────────────────────────────┼────────────────────────────┐
                  │                             │                            │
        ┌─────────▼──────────┐       ┌──────────▼─────────┐       ┌─────────▼──────────┐
        │  ingest/extract.py │       │ ingest/parse_xlsx  │       │ ingest/synth_data  │
        │  scheduled fetch   │       │ pydantic-validated │       │ stream events +    │
        │  via Airflow       │       │ raw → bronze       │       │ fraud scenarios    │
        └─────────┬──────────┘       └──────────┬─────────┘       └─────────┬──────────┘
                  │                             │                            │
                  └─────────────────────────────┴────────────────────────────┘
                                                │
                                                ▼
                              ┌────────────────────────────────────┐
                              │       BigQuery `cadence-public`    │
                              │       (free tier — 10GB storage,   │
                              │        1TB queries/month)          │
                              │  ┌──────────────────────────────┐  │
                              │  │ raw_dsa_main_h1_2024         │  │
                              │  │ raw_dsa_artists_h2_2025      │  │
                              │  │ raw_streams_synthetic        │  │
                              │  │ raw_llm_verdicts             │  │
                              │  │ ...                          │  │
                              │  └──────────────────────────────┘  │
                              └────────────────┬───────────────────┘
                                               │
                                               ▼
                              ┌────────────────────────────────────┐
                              │             dbt-core               │
                              │  staging → intermediate → marts    │
                              │  ┌──────────────────────────────┐  │
                              │  │ stg_*  (typed, deduped)      │  │
                              │  │ int_*  (joined, derived)     │  │
                              │  │ dim_*, fct_*, rpt_*, sig_*   │  │
                              │  └──────────────────────────────┘  │
                              │  + sources, tests (incl. dbt-     │
                              │    expectations), exposures,       │
                              │    snapshots, semantic models      │
                              │    (MetricFlow)                    │
                              └────────────────┬───────────────────┘
                                               │
                ┌──────────────────────────────┼──────────────────────────────┐
                │                              │                              │
                ▼                              ▼                              ▼
   ┌────────────────────────┐    ┌─────────────────────────┐    ┌──────────────────────────┐
   │  Looker Studio         │    │  Next.js 15 App on      │    │  FastAPI Researcher API  │
   │  (3 dashboards,        │    │  Vercel (App Router,    │    │  (Vercel-deployed,       │
   │   public URLs,         │    │   TypeScript, Tailwind, │    │   reads from BigQuery    │
   │   backed by BigQuery)  │    │   shadcn/ui, Recharts;  │    │   directly)              │
   │  Plus LookML files     │    │   server components     │    │                          │
   │  in repo for full      │    │                         │    │  Public OpenAPI spec     │
   │  Looker portability    │    │                         │    │  Rate limiting           │
   │                        │    │                         │    │  Audit logging → BQ      │
   └────────────────────────┘    └─────────────────────────┘    └──────────────────────────┘
                │                              │                              │
                └──────────────────────────────┼──────────────────────────────┘
                                               │
                                               ▼
                              ┌────────────────────────────────────┐
                              │  Airflow (Astro CLI local;         │
                              │  Cloud Composer-ready manifest)    │
                              │  DAG: cadence_refresh.py           │
                              │  ┌──────────────────────────────┐  │
                              │  │ extract_dsa_reports          │  │
                              │  │   → load_to_bq               │  │
                              │  │   → dbt_deps                 │  │
                              │  │   → dbt_build (incl. tests)  │  │
                              │  │   → publish_dbt_docs         │  │
                              │  │   → refresh_lookml_cache     │  │
                              │  │   → refresh_llm_verdicts     │  │
                              │  │   → notify_slack / email     │  │
                              │  └──────────────────────────────┘  │
                              └────────────────────────────────────┘

                              ┌────────────────────────────────────┐
                              │  GitHub Actions CI                 │
                              │  on every push + PR:               │
                              │   - pre-commit (ruff, sqlfluff,    │
                              │     mypy)                          │
                              │   - dbt deps                       │
                              │   - dbt build (DuckDB local target)│
                              │   - dbt build (BigQuery CI target) │
                              │   - dbt test                       │
                              │   - verify_round_trip.py           │
                              │   - build dbt docs → GH Pages      │
                              └────────────────────────────────────┘
```

### 6.2 Tech Stack — All Tools Genuinely Deployed

| Layer | Choice | What's actually deployed |
|---|---|---|
| **Warehouse (production)** | **BigQuery** (free tier, project `cadence-public`) | Working dataset with 20+ tables/views; service-account auth for dbt + Next.js + FastAPI; bytes-billed metrics in repo README |
| **Warehouse (local dev)** | **DuckDB** | Same dbt project, dual `profiles.yml` targets — `dev` (DuckDB) and `prod` (BigQuery) — to demonstrate warehouse portability |
| **Transformation** | **dbt-core 1.8+** | 50+ models, 200+ tests, semantic layer, exposures, snapshots, deployed `dbt docs` site on GitHub Pages |
| **Test extension** | **dbt-expectations** | Distribution + regex tests, ~60 of the 200+ |
| **Semantic Layer A** | **MetricFlow** (via `dbt_metricflow`) | Powers the Next.js `/explorer` route's metric picker (server component fetches MetricFlow query results) |
| **Semantic Layer B** | **LookML** (`looker/` directory) | Powers Looker Studio dashboards via BigQuery + LookML data sources |
| **Orchestration** | **Apache Airflow** (Astro CLI for local; Cloud Composer-ready) | Working DAG (`cadence_refresh.py`) with 8 tasks; screenshots in repo; live URL when running |
| **BI / Visualization (primary)** | **Looker Studio** (free, GCP-native, BigQuery-backed) | 3 published dashboards with public URLs |
| **Frontend (primary)** | **Next.js 15 + TypeScript + Tailwind + shadcn/ui + Recharts** on **Vercel** | The 9-route product surface — same stack as AgentRadar; deployed at `cadence.vercel.app` (or equivalent) |
| **API** | **FastAPI** on **Vercel** (free tier) | Researcher API at `cadence-research-api.vercel.app` (or equivalent) with OpenAPI 3.1, Swagger UI, rate limiting, audit logging |
| **LLM SDK** | `anthropic`, `openai`, `google-generativeai` | Real API calls during pre-cache; verdicts persisted to BigQuery as `raw_llm_verdicts` |
| **Validation** | **pydantic v2** | Synthetic data schemas + DSA report parser schemas + LLM verdict schemas |
| **Lint/format** | **ruff + sqlfluff + mypy** | Pre-commit + CI |
| **CI** | **GitHub Actions** | Public repo with green main badge |
| **Hosting** | Vercel + Vercel (×2: Next.js app + FastAPI service) + GitHub Pages + Looker Studio | All free-tier; all linked from About page |
| **Diagrams** | **Mermaid** | DAG + architecture + lineage diagrams |

Free-tier budget envelope (documented in repo README):
- BigQuery: 10GB storage / 1TB queries per month → Cadence uses ~50MB and ~50GB queries → 5% of free tier
- Vercel: 100GB bandwidth / 100k function invocations per day → researcher API uses negligible
- Vercel: 2 deployed apps on hobby tier (Next.js + FastAPI) → fits comfortably
- LLM APIs: Anthropic + OpenAI + Google free credits or pre-cached responses; pre-cache budget ≈ $5

### 6.3 Repository Structure

```
cadence/
├── README.md                            # Single-command setup contract; live URLs
├── pyproject.toml                       # Python deps; uv-compatible
├── uv.lock                              # Reproducible installs
├── dbt_project.yml                      # dbt project config
├── profiles.yml.example                 # DuckDB + BigQuery dual targets
├── packages.yml                         # dbt-expectations, dbt-utils, dbt-meta-testing
├── .github/workflows/
│   ├── ci.yml                           # PR validation
│   └── deploy_dbt_docs.yml              # GH Pages deploy
├── .pre-commit-config.yaml              # ruff + sqlfluff + mypy
├── ingest/
│   ├── __init__.py
│   ├── fetch_spotify_dsa.py             # downloads the 4 published Spotify XLSX files
│   ├── parse_dsa_report.py              # pydantic-validated XLSX → Parquet
│   ├── load_to_bigquery.py              # Parquet → BQ raw_* tables
│   ├── synth_streams.py                 # Synthetic event generator
│   ├── synth_fraud_scenarios.py         # 5 embedded scenarios with deterministic seeds
│   ├── precache_llm_verdicts.py         # Real Claude/GPT-4o/Gemini calls; persist to BQ
│   └── schemas/
│       ├── dsa_main_v1.py               # 2024 legacy template
│       ├── dsa_main_v2.py               # 2025 harmonised template
│       ├── dsa_artists_v2.py
│       ├── dsa_authors_v2.py
│       ├── dsa_creators_v2.py
│       ├── stream_event.py
│       ├── moderation_action.py
│       ├── llm_verdict.py
│       └── researcher_query.py
├── airflow/
│   ├── dags/
│   │   └── cadence_refresh.py           # Working DAG with 8 tasks
│   ├── plugins/
│   ├── tests/
│   │   └── test_dag_imports.py          # Sanity-check DAG validity in CI
│   ├── docker-compose.yml               # `astro dev start` ready
│   └── Dockerfile                       # Astro/Airflow image
├── models/
│   ├── staging/
│   │   ├── _sources.yml
│   │   ├── _staging.yml
│   │   ├── stg_dsa_main.sql
│   │   ├── stg_dsa_artists.sql
│   │   ├── stg_dsa_authors.sql
│   │   ├── stg_dsa_creators.sql
│   │   ├── stg_streams.sql
│   │   ├── stg_users.sql
│   │   ├── stg_tracks.sql
│   │   ├── stg_artists_synth.sql
│   │   ├── stg_moderation_actions.sql
│   │   ├── stg_appeals.sql
│   │   └── stg_llm_verdicts.sql
│   ├── intermediate/
│   │   ├── _intermediate.yml
│   │   ├── int_dsa_unified.sql          # The cross-product unification
│   │   ├── int_dsa_period_aligned.sql   # Time-series alignment
│   │   ├── int_user_listening_patterns.sql
│   │   ├── int_track_streaming_signals.sql
│   │   ├── int_session_fingerprints.sql
│   │   ├── int_geo_distribution.sql
│   │   └── int_llm_verdict_aggregates.sql
│   ├── marts/
│   │   ├── transparency/
│   │   │   ├── _transparency.yml
│   │   │   ├── dim_dsa_reporting_periods.sql
│   │   │   ├── dim_dsa_products.sql
│   │   │   ├── dim_dsa_categories.sql
│   │   │   ├── dim_eu_member_states.sql
│   │   │   ├── fct_dsa_decisions.sql
│   │   │   ├── fct_dsa_appeals.sql
│   │   │   ├── fct_dsa_eu_orders.sql
│   │   │   ├── rpt_cross_product_summary.sql       # Powers headline dashboard
│   │   │   ├── rpt_quarter_over_quarter_trends.sql
│   │   │   ├── rpt_member_state_breakdown.sql
│   │   │   ├── rpt_automated_vs_human.sql
│   │   │   └── rpt_appeals_lifecycle.sql
│   │   ├── safety/
│   │   │   ├── _safety.yml
│   │   │   ├── dim_users.sql
│   │   │   ├── dim_tracks.sql
│   │   │   ├── dim_artists.sql
│   │   │   ├── fct_streams.sql
│   │   │   ├── fct_artificial_streaming_flags.sql
│   │   │   ├── sig_listen_spike.sql
│   │   │   ├── sig_geo_anomaly.sql
│   │   │   ├── sig_stream_to_listener_ratio.sql
│   │   │   ├── sig_repeat_listener_concentration.sql
│   │   │   └── sig_playlist_stuffing.sql
│   │   ├── llm_ops/
│   │   │   ├── _llm_ops.yml
│   │   │   ├── fct_llm_verdicts.sql
│   │   │   ├── rpt_llm_agreement_rate.sql
│   │   │   ├── rpt_llm_latency_distribution.sql
│   │   │   ├── rpt_llm_cost_breakdown.sql
│   │   │   └── rpt_llm_drift_score.sql
│   │   └── researcher/
│   │       ├── _researcher.yml
│   │       ├── rpt_researcher_query_audit.sql      # Meta — researcher API access logged
│   │       └── rpt_researcher_active_keys.sql
│   ├── semantic/
│   │   ├── transparency_metrics.yml                # MetricFlow semantic models
│   │   ├── safety_metrics.yml                      # The methodology source-of-truth
│   │   └── llm_ops_metrics.yml
│   └── snapshots/
│       └── snap_dsa_decisions.sql                  # SCD2 for re-published reports
├── tests/
│   ├── assert_no_orphan_streams.sql
│   ├── assert_dsa_appeals_balance.sql
│   ├── assert_fraud_score_in_range.sql
│   ├── assert_synthetic_fraud_caught.sql
│   ├── assert_dsa_period_continuity.sql            # Cross-product reconciliation
│   ├── assert_dsa_categories_consistent_2025.sql   # Harmonised template adherence
│   └── assert_llm_verdict_schema_valid.sql
├── seeds/
│   ├── eu_member_states.csv
│   ├── dsa_policy_categories_v1.csv                # Pre-July-2025 mapping
│   ├── dsa_policy_categories_v2.csv                # Harmonised template mapping
│   └── certified_metric_registry.csv               # The BI governance registry
├── analyses/
│   └── exploratory_*.sql
├── macros/
│   ├── generate_schema_name.sql
│   └── safe_division.sql
├── exposures/
│   └── _exposures.yml                              # Looker Studio + Next.js + FastAPI
├── looker/
│   ├── cadence.model.lkml
│   ├── views/
│   │   ├── dsa_unified.view.lkml
│   │   ├── streams.view.lkml
│   │   ├── llm_verdicts.view.lkml
│   │   └── ...
│   ├── explores/
│   │   ├── cross_product.explore.lkml
│   │   └── ...
│   ├── dashboards/
│   │   ├── exec_summary.dashboard.lookml
│   │   ├── operational_trends.dashboard.lookml
│   │   └── member_state_heatmap.dashboard.lookml
│   └── tests/
│       └── lookml_validation.lkml                  # Validates with `lkmltools`
├── api/
│   ├── main.py                                     # FastAPI app
│   ├── routers/
│   │   ├── dsa.py
│   │   ├── researcher_keys.py
│   │   ├── audit.py
│   │   └── citations.py
│   ├── middleware/
│   │   ├── rate_limit.py
│   │   └── audit_logger.py
│   ├── schemas/
│   │   ├── responses.py
│   │   └── citations.py
│   ├── tests/
│   │   ├── test_endpoints.py
│   │   └── test_rate_limit.py
│   ├── vercel.json
│   └── requirements.txt
├── web/                                            # Next.js 15 (App Router) frontend, deployed to Vercel
│   ├── package.json                                # pnpm workspace
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.mjs
│   ├── components.json                             # shadcn/ui config
│   ├── .env.example                                # GOOGLE_APPLICATION_CREDENTIALS_BASE64, BQ_PROJECT, BQ_DATASET, FASTAPI_BASE_URL
│   ├── public/
│   │   ├── og-image.png
│   │   └── favicon.svg
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx                          # Root layout (metadata, fonts, providers)
│   │   │   ├── page.tsx                            # Home / landing
│   │   │   ├── lakehouse/
│   │   │   │   ├── page.tsx                        # Cross-product DSA dashboard (server component)
│   │   │   │   ├── trends/page.tsx                 # Quarter-over-quarter view
│   │   │   │   ├── member-state/page.tsx           # Member State breakdown with choropleth
│   │   │   │   └── dashboards/page.tsx             # Live Looker Studio embeds
│   │   │   ├── detection-lab/
│   │   │   │   ├── page.tsx                        # Five fraud scenario cards
│   │   │   │   ├── [scenario]/page.tsx             # Per-scenario drill-down
│   │   │   │   └── llm-verdicts/[trackId]/page.tsx # Multi-LLM verdict cards + transcripts
│   │   │   ├── researcher-api/
│   │   │   │   ├── page.tsx                        # Landing + Get a Key + Citation Guidance
│   │   │   │   └── docs/page.tsx                   # Embedded Swagger UI iframe
│   │   │   ├── explorer/page.tsx                   # MetricFlow self-service explorer
│   │   │   ├── analyst-console/
│   │   │   │   ├── page.tsx                        # Tabs entry
│   │   │   │   ├── dag/page.tsx                    # React Flow dbt DAG
│   │   │   │   ├── tests/page.tsx                  # Tests panel from run_results.json
│   │   │   │   ├── models/page.tsx                 # Model catalog from manifest.json
│   │   │   │   ├── lineage/page.tsx                # Column-level lineage
│   │   │   │   └── airflow/page.tsx                # Airflow DAG visualization + screenshot
│   │   │   ├── methodology/page.tsx                # Rendered from safety_metrics.yml + manifest
│   │   │   ├── bi-governance/page.tsx              # Certified registry, ownership, deprecation
│   │   │   ├── teardown/page.tsx                   # Strategic landscape argument
│   │   │   ├── about/page.tsx                      # JD Mapping Table + all deployed URLs
│   │   │   └── api/                                # Next.js Route Handlers (thin server proxies)
│   │   │       ├── bq/route.ts                     # Server-only BigQuery query proxy
│   │   │       ├── manifest/route.ts               # Serves dbt manifest.json + run_results.json
│   │   │       ├── safety-metrics/route.ts         # Serves parsed safety_metrics.yml
│   │   │       └── refresh/route.ts                # Webhook for Airflow → revalidate cache
│   │   ├── components/
│   │   │   ├── ui/                                 # shadcn/ui primitives (button, card, dialog, table, accordion, badge, tabs, dropdown, select, input, label, separator, skeleton, sheet, popover, tooltip, chart)
│   │   │   ├── nav/
│   │   │   │   ├── top-nav.tsx
│   │   │   │   └── side-nav.tsx
│   │   │   ├── lakehouse/
│   │   │   │   ├── cross-product-grid.tsx          # 4-column comparison
│   │   │   │   ├── reconciliation-panel.tsx
│   │   │   │   ├── member-state-choropleth.tsx     # Plotly via react-plotly.js OR D3
│   │   │   │   └── trend-chart.tsx                 # Recharts time-series with annotations
│   │   │   ├── detection/
│   │   │   │   ├── scenario-card.tsx
│   │   │   │   ├── signal-badge.tsx
│   │   │   │   ├── suspicion-score-ring.tsx
│   │   │   │   └── flagged-tracks-table.tsx
│   │   │   ├── llm-verdicts/
│   │   │   │   ├── verdict-card.tsx                # Per-provider card (Claude / GPT-4o / Gemini)
│   │   │   │   ├── transcript-dialog.tsx           # Verbatim prompt + response in shadcn/ui Dialog
│   │   │   │   └── agreement-ring.tsx
│   │   │   ├── audit-trail.tsx                     # The 🔍 view-source affordance
│   │   │   ├── citation-chip.tsx                   # Inline citation chips
│   │   │   ├── methodology/
│   │   │   │   ├── signal-weights-table.tsx        # Renders from yaml
│   │   │   │   ├── metric-definitions-table.tsx    # Renders from MetricFlow + LookML
│   │   │   │   ├── model-inventory-table.tsx       # Renders from manifest.json
│   │   │   │   └── source-revision-banner.tsx      # Shows commit hash + timestamp
│   │   │   ├── governance/
│   │   │   │   ├── certified-registry-table.tsx
│   │   │   │   ├── ownership-card.tsx
│   │   │   │   └── deprecation-flow.tsx            # Mermaid via mermaid.js
│   │   │   ├── analyst/
│   │   │   │   ├── react-flow-dag.tsx              # @xyflow/react for the dbt DAG
│   │   │   │   └── tests-table.tsx
│   │   │   └── shared/
│   │   │       ├── code-block.tsx                  # Syntax-highlighted SQL via shiki
│   │   │       ├── footer.tsx                      # Synthetic-data disclaimer + repo link
│   │   │       └── stat-card.tsx
│   │   ├── lib/
│   │   │   ├── bigquery.ts                         # @google-cloud/bigquery client (server-only)
│   │   │   ├── bigquery-queries.ts                 # Typed query functions
│   │   │   ├── manifest.ts                         # dbt manifest.json + run_results.json parsers
│   │   │   ├── lookml.ts                           # LookML AST parser
│   │   │   ├── safety-metrics.ts                   # safety_metrics.yml loader (zod-validated)
│   │   │   ├── citations.ts                        # Citation database for chips
│   │   │   ├── fmt.ts                              # Number/date/currency formatters
│   │   │   ├── design-tokens.ts                    # Cadence design tokens (from PRD §5.2)
│   │   │   └── seo.ts                              # Metadata helpers
│   │   ├── schemas/                                # Zod schemas mirroring the pydantic ones
│   │   │   ├── verdict.ts
│   │   │   ├── dsa-row.ts
│   │   │   └── researcher-query.ts
│   │   └── styles/
│   │       └── globals.css                         # Tailwind base + design-token CSS variables
│   ├── tests/
│   │   ├── unit/                                   # vitest
│   │   ├── e2e/                                    # Playwright (smoke tests for the recruiter path)
│   │   └── visual/                                 # Playwright screenshot diffs
│   └── README.md                                   # Web-app-specific README
├── precache/                                       # Pre-computed JSONs
│   ├── dsa_reports/                                # Parsed Spotify XLSX → JSON
│   │   ├── main_h1_2024.json
│   │   ├── main_h2_2024.json
│   │   ├── main_h1_2025.json
│   │   ├── main_h2_2025.json                       # Feb 2026 publication
│   │   ├── artists_h2_2025.json
│   │   ├── authors_h2_2025.json
│   │   └── creators_h2_2025.json
│   └── fraud_scenarios/
│       ├── bot_ring.json
│       ├── ai_fake_artists.json
│       ├── family_plan_abuse.json
│       ├── geographic_anomaly.json
│       └── playlist_stuffing.json
├── scripts/
│   ├── bootstrap_bigquery.py                       # Creates the BQ project + dataset
│   ├── verify_round_trip.py                        # Drift = 0 check
│   ├── deploy_looker_studio.md                     # Step-by-step LS deployment
│   ├── deploy_vercel_api.md                        # Step-by-step Vercel deployment
│   └── refresh_dsa_reports.sh                      # Manual refresh helper
└── docs/
    ├── architecture.md
    ├── jd_mapping.md
    └── runbook.md                                  # Operational playbook
```

### 6.4 Validation Framework — Write-Audit-Publish

Per dbt Labs guidance and the JDs' shared emphasis on validation:

**Write step:** Synthetic data + parsed DSA reports emitted to Parquet, pydantic-validated row-by-row before write. Any failure aborts.

**Audit step:** dbt builds models in a `__audit` BigQuery dataset. After build, all tests run against `__audit`. Any failure aborts before touching production.

**Publish step:** On test pass, swap from `__audit` → `cadence` via `dbt-utils` macro or `bq cp` command in the Airflow DAG. The publish step is its own Airflow task with explicit success/failure logging.

This pattern gives Compliance Counsel the auditability guarantee. It also gives the senior JD's *"structured escalation paths"* a literal implementation: if any of the 200+ tests fails, the publish task fails, Slack is notified, the dataset stays on the previous good version, and the on-call engineer investigates.

### 6.5 Test Inventory (target 200+ tests)

- **Built-in dbt tests:** unique, not_null, accepted_values, relationships across all staging + marts (~80)
- **dbt-expectations:** distribution, regex, row-count anomaly tests (~60)
- **Custom singular tests:** business-logic invariants (~30):
  - Cross-product reconciliations (Main+Artists+Authors+Creators sums match disclosed totals)
  - DSA period continuity (no gaps in reporting periods)
  - DSA category v1↔v2 mapping completeness (legacy → harmonised)
  - Synthetic fraud scenarios all caught
  - Composite suspicion score in [0, 100]
  - LLM verdict schema valid + within expected token/cost ranges
- **dbt-meta-testing:** ensures every model has a description, every column has a description, every public model has tests (~30)

### 6.6 GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run pre-commit run --all-files
  dbt-duckdb:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run python -m ingest.synth_streams --rows 100000
      - run: uv run dbt deps
      - run: uv run dbt build --target dev
      - run: uv run python scripts/verify_round_trip.py
  dbt-bigquery:
    needs: validate
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: echo "$BQ_KEYFILE" > /tmp/keyfile.json
        env:
          BQ_KEYFILE: ${{ secrets.BIGQUERY_SERVICE_ACCOUNT_KEY }}
      - run: uv run dbt deps
      - run: uv run dbt build --target prod_ci  # CI-scoped BQ dataset
  publish-docs:
    needs: [dbt-duckdb, dbt-bigquery]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run dbt deps
      - run: uv run dbt docs generate --target dev
      - uses: actions/deploy-pages@v4
        with:
          artifact_name: dbt-docs
  airflow-dag-test:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: cd airflow && uv run pytest tests/
  api-test:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: cd api && uv run pytest tests/
```

The README's CI badge reflects this workflow's status. PRs cannot merge until all jobs pass.


---

## 7. Data Sources: Real Spotify DSA + Synthetic Streaming

### 7.1 Real Data — Spotify DSA Reports (the differentiator)

**This is the single biggest signal of seriousness in Cadence.** The reports are public, the parsing is non-trivial, and getting the cross-product unification right takes actual analytics engineering judgment.

**Sources to ingest (V1):**
- [Spotify Main DSA Transparency Report 2025](https://www.spotify.com/us/safetyandprivacy/transparency) — published 27 February 2026, harmonised template
- Spotify for Artists DSA Transparency Report 2025 — same publication date
- Spotify for Authors DSA Transparency Report 2025 — same publication date
- Spotify for Creators DSA Transparency Report 2025 — same publication date
- Spotify Main DSA Transparency Report 2024 (legacy template — for time-series continuity)
- Earlier 2024 reports if available

**Ingestion pipeline (`ingest/fetch_spotify_dsa.py` + `ingest/parse_dsa_report.py`):**

1. **Fetch** — HTTP GET each XLSX from Spotify's published URLs. Cache locally with content-hash. Re-fetch only on hash change. Polite — respects HTTP caching headers.
2. **Detect template version** — sniff sheet names and header structure. Branch to v1 (legacy 2024) or v2 (harmonised 2025) parser.
3. **Parse with pydantic** — each sheet has a typed schema in `ingest/schemas/dsa_*_v*.py`. Schema validation per row. Schema drift → loud failure with diff report.
4. **Land as Parquet** — to a `raw/` directory in the repo (committed) and uploaded to a BigQuery `raw_*` table.
5. **Snapshot** — every fetch is timestamped and hashed; the dbt `snapshots/` SCD2 layer captures changes if Spotify republishes.

**Cross-product unification challenge (where the analytics engineering judgment shows):**

Spotify's four reports use overlapping but non-identical column conventions. Examples:
- "Notices received" appears in Main as a single column; in Artists, it's split into "User notices" and "Trusted Flagger notices."
- "Automated decisions" is a percentage in Main 2024; an absolute count in Main 2025; a structured object in Authors.
- "Member State coverage" varies — Main reports per-state granularity; Creators reports only aggregated EU totals.

Cadence's `int_dsa_unified.sql` model resolves these into a canonical schema:

```sql
SELECT
  product_line,                    -- 'main' | 'artists' | 'authors' | 'creators'
  reporting_period_start,
  reporting_period_end,
  template_version,                -- 'legacy_2024' | 'harmonised_2025_v1'
  policy_category_canonical,       -- normalized via seeds/dsa_policy_categories_v2.csv
  member_state,                    -- 'EU_AGGREGATE' if not reported per-state
  decisions_total,
  decisions_automated,
  decisions_human,
  decisions_hybrid,
  notices_received,
  notices_user_origin,
  notices_trusted_flagger_origin,
  appeals_received,
  appeals_resolved_upheld,
  appeals_resolved_reversed,
  appeals_pending,
  median_time_to_act_hours,
  source_report_url,               -- The provenance URL
  source_sheet_name,
  source_row_index,
  ingested_at
FROM {{ ref('stg_dsa_main') }}
UNION ALL
SELECT ... FROM {{ ref('stg_dsa_artists') }}
UNION ALL
SELECT ... FROM {{ ref('stg_dsa_authors') }}
UNION ALL
SELECT ... FROM {{ ref('stg_dsa_creators') }}
```

The `int_dsa_unified` model is heavily commented to explain every reconciliation decision and is paired with a custom test `assert_dsa_categories_consistent_2025.sql` that fails if any row has a non-canonical category, forcing the engineer to update the seed mapping rather than silently dropping data.

### 7.2 Synthetic Data — Stream Events + Fraud Scenarios

**Why synthetic for this layer:** Spotify's track-level streaming data is proprietary. Synthetic data lets us embed exactly the fraud patterns we want detected, then verify detection finds them. Controllable, testable, ethical, public-shareable.

**Six raw tables** (all generated deterministically via Faker + numpy + pydantic):

| Table | Rows (V1) | Description |
|---|---|---|
| `raw_streams` | 5,000,000 | Stream events: user_id, track_id, ts, country, device, ms_played, session_id |
| `raw_users` | 100,000 | Users: user_id, country, plan_type, signup_ts, age_band, household_id |
| `raw_tracks` | 200,000 | Tracks: track_id, artist_id, title, isrc, duration_ms, release_date, distributor, ai_generated_label |
| `raw_artists_synth` | 40,000 | Artists: artist_id, name, country, distributor, monthly_listeners |
| `raw_moderation_actions_synth` | 60,000 | Synthetic T&S actions paralleling DSA category structure |
| `raw_appeals_synth` | 8,000 | Synthetic appeals lifecycle |

The synthetic data is clearly labeled `_synth` in BigQuery and in every page footer in the Next.js app ("Stream-event data is synthetic; DSA report data is real, sourced from Spotify's public publications").

### 7.3 Embedded Fraud Scenarios (5, deterministic)

Each scenario is implemented in `ingest/synth_fraud_scenarios.py` with a fixed random seed. Each is documented with its expected detection signal and is verified by `assert_synthetic_fraud_caught.sql`.

| # | Scenario | Pattern | Expected signal | Suspicion score target |
|---|---|---|---|---|
| 1 | Bot Ring | 200 fake users, same country, same 50 tracks, 50+ streams each over 7 days | stream-to-listener ratio + repeat-listener concentration | ≥ 80 |
| 2 | AI Fake Artists | 30 newly-created tracks (release_date=today-7d), `ai_generated_label=true`, 10k+ streams from 200–300 listeners | listen spike + AI density | ≥ 75 |
| 3 | Family-Plan Abuse | 1 family plan account (5 user_ids), 1 niche track, 100+ plays in 24h | repeat-listener concentration on family plan | ≥ 70 |
| 4 | Geographic Anomaly | 1 US-registered artist; 10 tracks; 80%+ of streams from a single non-US country | geo concentration | ≥ 75 |
| 5 | Playlist Stuffing | 1 session_id sequence; 80% AI-generated tracks; from new artists | playlist stuffing + AI density | ≥ 80 |

### 7.4 LLM Verdict Pre-Cache

`ingest/precache_llm_verdicts.py` runs once per build to refresh LLM verdicts on the 5 fraud scenarios. For each scenario, it sends an identical prompt to Claude (Anthropic), GPT-4o (OpenAI), and Gemini (Google), persists structured verdicts (pydantic-validated) to `raw_llm_verdicts` in BigQuery, and caches transcripts as JSON in `precache/fraud_scenarios/`.

Pre-caching protects against:
- Recruiter-perceived latency on page load
- API outages (any provider could be down)
- API budget burn (each provider charges per call)

Total pre-cache cost: ~$5 across all three providers for 5 scenarios × 3 providers = 15 API calls. Negligible.

### 7.5 Round-Trip Validation

`scripts/verify_round_trip.py` runs in CI on every PR:
1. Load each pre-cached fraud scenario JSON
2. Re-run the dbt detection pipeline against fresh synthetic data
3. Assert detection scores match the cached results within tolerance (drift = 0)
4. Assert all 5 embedded fraud scenarios are flagged with score ≥ 70
5. Re-load the parsed Spotify DSA reports from `precache/dsa_reports/`
6. Assert `int_dsa_unified` row counts match expected per-product totals

Exit code propagates to CI. Failures block merges.

---

## 8. The Methodology Contract

> *"The methodology page is generated from machine-readable source. The code is the methodology. The methodology is the code."*

The Methodology route (`/methodology` in the Next.js app) is generated entirely from machine-readable source files. No hand-edits permitted. This is non-negotiable — it's the architectural promise that distinguishes Cadence from a portfolio piece with screenshots.

### 8.1 Source Files Read at Render Time

| File | What it provides |
|---|---|
| `models/semantic/safety_metrics.yml` | Detection signal weights, thresholds, action thresholds |
| `models/semantic/transparency_metrics.yml` | DSA metric definitions (semantic models, measures, dimensions) |
| `models/semantic/llm_ops_metrics.yml` | LLM verdict-derived metrics |
| `looker/cadence.model.lkml` | LookML metric definitions (parallel to MetricFlow) |
| `target/manifest.json` | Every dbt model name, description, columns, tests, materialization |
| `target/run_results.json` | Most recent test pass/fail per test |
| `target/catalog.json` | Column-level types, profiles, sample data |
| `dbt_project.yml` | Project name, version, model config |
| `seeds/certified_metric_registry.csv` | The blessed-metric registry (BI governance) |
| `.git/HEAD` | Last commit hash + timestamp |

### 8.2 The YAML Spec (excerpt — `safety_metrics.yml`)

```yaml
version: 2

semantic_models:
  - name: artificial_streaming_signals
    description: |
      Composite signals for detecting artificial streaming.
      Weights and thresholds defined here are the SINGLE source of truth —
      the dbt models, the LookML metrics, and the Methodology page all read
      from this file. Changing a number here propagates everywhere.
    model: ref('fct_artificial_streaming_flags')
    entities:
      - name: track
        type: primary
        expr: track_id
    measures:
      - name: composite_suspicion_score
        agg: average
        expr: composite_suspicion_score
        description: |
          Weighted sum of 5 signals, normalized to 0-100.
          Action thresholds: 70+ = recommend_remove, 40-69 = recommend_rank_lower,
          <40 = no_action.

config:
  signal_weights:
    listen_spike: 0.25
    geo_anomaly: 0.20
    stream_to_listener_ratio: 0.25
    repeat_listener_concentration: 0.20
    playlist_stuffing: 0.10
  signal_thresholds:
    listen_spike:
      streams_per_day_baseline_multiplier: 10.0
      min_baseline_streams_per_day: 100
    geo_anomaly:
      single_country_share_threshold: 0.80
      min_streams: 1000
    stream_to_listener_ratio:
      threshold: 50.0
      min_streams: 500
    repeat_listener_concentration:
      hh_index_threshold: 0.30
      min_streams: 100
    playlist_stuffing:
      ai_track_share_threshold: 0.70
      min_session_tracks: 10
  action_thresholds:
    recommend_remove: 70
    recommend_rank_lower: 40
  what_is_NOT_measured:
    - "Audio fingerprint similarity (we don't have audio data)"
    - "User device fingerprint depth (we have device class only, not browser/OS detail)"
    - "Historical recidivism by user (not modeled in V1)"
    - "Cross-platform fraud markers (MFFA NCFTA shared markers — V1.5)"
```

### 8.3 The Render Loop (Next.js server component)

`web/src/app/methodology/page.tsx`:

```tsx
import { promises as fs } from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import yaml from "yaml";
import { z } from "zod";
import { SignalWeightsTable } from "@/components/methodology/signal-weights-table";
import { MetricDefinitionsTable } from "@/components/methodology/metric-definitions-table";
import { ModelInventoryTable } from "@/components/methodology/model-inventory-table";
import { SourceRevisionBanner } from "@/components/methodology/source-revision-banner";
import { parseLookML } from "@/lib/lookml";

// This is a Server Component — runs at build time + on revalidate, never ships to the client.
export const revalidate = 3600; // Re-render hourly when Airflow webhook fires

const SafetyMetricsSchema = z.object({
  config: z.object({
    signal_weights: z.record(z.string(), z.number()),
    signal_thresholds: z.record(z.string(), z.record(z.string(), z.number())),
    action_thresholds: z.record(z.string(), z.number()),
    what_is_NOT_measured: z.array(z.string()),
  }),
});

async function loadSource() {
  const safetyRaw = await fs.readFile(path.join(process.cwd(), "../models/semantic/safety_metrics.yml"), "utf8");
  const safety = SafetyMetricsSchema.parse(yaml.parse(safetyRaw));
  const transparency = yaml.parse(await fs.readFile(path.join(process.cwd(), "../models/semantic/transparency_metrics.yml"), "utf8"));
  const llmOps = yaml.parse(await fs.readFile(path.join(process.cwd(), "../models/semantic/llm_ops_metrics.yml"), "utf8"));
  const manifest = JSON.parse(await fs.readFile(path.join(process.cwd(), "../target/manifest.json"), "utf8"));
  const runResults = JSON.parse(await fs.readFile(path.join(process.cwd(), "../target/run_results.json"), "utf8"));
  const lookml = parseLookML(await fs.readFile(path.join(process.cwd(), "../looker/cadence.model.lkml"), "utf8"));
  const gitHead = execSync("git rev-parse HEAD").toString().trim().slice(0, 8);
  const gitTs = execSync("git log -1 --format=%cI").toString().trim();
  return { safety, transparency, llmOps, manifest, runResults, lookml, gitHead, gitTs };
}

export default async function MethodologyPage() {
  const { safety, transparency, llmOps, manifest, runResults, lookml, gitHead, gitTs } = await loadSource();

  return (
    <main className="mx-auto max-w-7xl px-6 py-12 space-y-12">
      <SourceRevisionBanner gitHead={gitHead} gitTs={gitTs} />

      <section>
        <h2 className="text-2xl font-semibold tracking-tight">Detection Signal Weights</h2>
        <p className="text-muted-foreground mt-2">
          These weights live in <code>models/semantic/safety_metrics.yml</code>. Edit them
          there; this page revalidates on next deploy.
        </p>
        <SignalWeightsTable
          weights={safety.config.signal_weights}
          thresholds={safety.config.signal_thresholds}
          runResults={runResults}
          className="mt-6"
        />
      </section>

      <section>
        <h2 className="text-2xl font-semibold tracking-tight">Metric Definitions</h2>
        <MetricDefinitionsTable metricflow={transparency} lookml={lookml} llmOps={llmOps} className="mt-6" />
      </section>

      <section>
        <h2 className="text-2xl font-semibold tracking-tight">dbt Model Inventory</h2>
        <ModelInventoryTable manifest={manifest} runResults={runResults} className="mt-6" />
      </section>

      <section>
        <h2 className="text-2xl font-semibold tracking-tight">What is NOT measured</h2>
        <p className="text-muted-foreground mt-2">Honest scope boundary. Documented in source.</p>
        <ul className="mt-4 list-disc pl-6 space-y-1">
          {safety.config.what_is_NOT_measured.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
```

The corresponding components (`SignalWeightsTable`, `MetricDefinitionsTable`, `ModelInventoryTable`, `SourceRevisionBanner`) are shadcn/ui–styled, fully typed, and unit-tested.

### 8.4 The Promise

A reviewer can:
1. Open `models/semantic/safety_metrics.yml` in the GitHub repo.
2. Open the deployed Methodology page in another tab.
3. Verify they match line-by-line.
4. Open `looker/cadence.model.lkml` and verify the LookML measures are listed too.
5. Change a weight in YAML, push, see the page update on next deploy + see the LookML cache regenerate via the Airflow DAG.

This is the AgentRadar "methodology rendered from `lib/score/rubric.ts`" pattern, applied to a parallel-source-of-truth situation (MetricFlow + LookML must stay in sync).

---

## 9. BI Governance Layer

> *Addresses the senior JD's "BI governance best practices" requirement explicitly. Most portfolio projects skip governance entirely; this is where Cadence demonstrates senior-shaped maturity.*

### 9.1 Why BI Governance Matters at Spotify Scale

Spotify's senior JD asks for *"experience with… BI governance best practices"* and *"ability to translate technical detail into meaningful outcomes for legal, policy, and operations stakeholders."* In practice this means:

- **Certified metrics** — a registry of "blessed" metrics that have been reviewed, owned, and signed off on. Anyone querying these can trust them. Anyone creating a new metric must justify why it can't reuse an existing one.
- **Owner attribution** — every metric has a named owner who is accountable for its definition, accuracy, and downstream consumers.
- **Deprecation policy** — a structured workflow for retiring metrics so downstream consumers don't get blindsided.
- **Naming conventions** — predictable patterns make the warehouse navigable for new contributors.
- **Change management** — how a stakeholder requests a metric change, how the AE reviews, how downstream is notified, how versions are tracked.

Cadence implements all five.

### 9.2 The Certified Metric Registry

Stored in `seeds/certified_metric_registry.csv`. Loaded by dbt as a seed table. Rendered into the BI Governance page. Every certified metric has:

| Column | Description |
|---|---|
| `metric_name` | The canonical name (e.g., `dsa_decisions_total`) |
| `definition` | One-sentence plain-English definition |
| `formula` | The SQL expression or MetricFlow measure reference |
| `unit` | Count, percentage, currency, time, etc. |
| `owner_primary` | Named role (e.g., "Compliance Counsel") |
| `owner_backup` | Backup role |
| `certified_date` | When the metric was blessed |
| `certifier` | Who blessed it |
| `downstream_consumers` | Comma-separated list of dashboards/exports/exposures |
| `change_control_workflow` | Reference to the workflow doc |
| `status` | `certified` / `deprecated` / `sunset` / `removed` |
| `deprecation_date` | If applicable |
| `replacement_metric` | If deprecated, what replaced it |
| `notes` | Free text for context |

Example rows:

```csv
metric_name,definition,owner_primary,status
dsa_decisions_total,"Total moderation decisions disclosed in Spotify's DSA Transparency Reports across all four product lines per reporting period",Compliance Counsel,certified
artificial_streaming_suspicion_score,"Composite 0-100 score combining 5 detection signals weighted per safety_metrics.yml",T&S Engineering,certified
llm_verdict_agreement_rate,"Percentage of flagged tracks where 2 of 3 LLM verdicts agree on the recommended action",T&S Engineering,certified
streams_per_listener_ratio,"DEPRECATED. Use stream_to_listener_ratio instead.",T&S Engineering,deprecated
```

The page renders the registry as a sortable, filterable table with deprecated metrics greyed out and replacement links visible.

### 9.3 Owner Attribution

Every dbt model's `description` field includes a `meta:` block:

```yaml
- name: rpt_cross_product_summary
  description: |
    The headline cross-product DSA comparison powering the executive Looker Studio dashboard.
  meta:
    owner_primary: "Compliance Counsel"
    owner_backup: "Policy Manager"
    sla_freshness_hours: 24
    pii_classification: "none"
    certified: true
```

The Analyst Console page parses this `meta:` block from the dbt manifest and surfaces ownership directly next to each model in the catalogue.

### 9.4 Deprecation Policy (3-Stage Workflow)

Documented on the BI Governance page:

| Stage | Duration | What happens |
|---|---|---|
| **Deprecated** | 30 days | Metric still works; dashboards show a deprecation badge; downstream consumers notified via Slack + email; replacement metric documented |
| **Sunset** | 30 days | Metric returns NULL with a warning logged to BigQuery audit table; dashboards show "this metric is sunset, please migrate to X" |
| **Removed** | — | Model deleted; dbt build fails for any reference; PR template requires migration plan |

Each transition is a PR that updates the `certified_metric_registry.csv` seed and triggers a CI workflow that posts to a designated Slack channel.

### 9.5 Naming Conventions

Documented and enforced via sqlfluff custom rules:

| Prefix | Layer | Materialization | Example |
|---|---|---|---|
| `stg_` | Staging | view | `stg_dsa_main` |
| `int_` | Intermediate | view or ephemeral | `int_dsa_unified` |
| `dim_` | Marts dimension | table | `dim_dsa_reporting_periods` |
| `fct_` | Marts fact | table or incremental | `fct_dsa_decisions` |
| `rpt_` | Marts reporting / aggregate | table | `rpt_cross_product_summary` |
| `sig_` | Marts safety signal | view | `sig_listen_spike` |
| `snap_` | Snapshot | snapshot | `snap_dsa_decisions` |

Plus column conventions: surrogate keys end in `_sk`, foreign keys end in `_id` matching the parent's primary key, timestamps use `_ts` suffix and UTC, dates use `_date` suffix.

### 9.6 Change Management Workflow

Rendered on the BI Governance page as a flow diagram:

```
Stakeholder request
  → AE triage (is there a certified metric that already covers this?)
  → If yes: stakeholder educated, ticket closed
  → If no:
      → AE writes a Metric Spec (template in docs/runbook.md)
      → Spec reviewed by metric owner + a peer AE
      → On approval:
          → New metric defined in safety_metrics.yml or LookML
          → New dbt model + tests
          → Registry seed updated
          → CI runs: tests pass, docs regenerate
          → Slack #cadence-metrics channel notified
          → Looker Studio dashboard rebuild scheduled
          → PR merged
      → On rejection: documented in registry as "Considered, declined: [reason]"
```

This is what good BI governance hygiene looks like at scale. It's documented because it should be. Cadence's V1 doesn't have a real-world stakeholder making requests — the workflow is documented as a process artifact, with seed-data examples illustrating "this is what a request, a spec, and a registry update would look like."

---

## 10. Multi-LLM Analytics Module

> *Reframed from v2: LLM verdicts are modeled as analytics input, not orchestrated as real-time UI. This is what an analytics engineer would actually build on top of an LLM-powered moderation pipeline.*

### 10.1 The Reframing

V2 had a real-time multi-LLM orchestration UI as the centerpiece. That's PM/ML-engineering shaped, not analytics-engineering shaped. Spotify's senior JD calls for *"performance tracking, early detection of issues, and structured escalation paths"* — which is exactly what an analytics layer over LLM verdicts provides.

V3 treats LLM moderation verdicts as a **source of data** that flows through staging → marts and surfaces as first-class analytics measures.

### 10.2 The Data Flow

```
ingest/precache_llm_verdicts.py
  → for each fraud scenario × {Claude, GPT-4o, Gemini}:
      → render shared moderation prompt
      → call provider API
      → validate response with pydantic Verdict schema
      → write to BigQuery raw_llm_verdicts
      → cache transcript JSON for inspection panel
                              ↓
                     stg_llm_verdicts.sql
                  (typed, deduped, denormalized)
                              ↓
                int_llm_verdict_aggregates.sql
            (joined to track + fraud scenario context;
             agreement-rate calculated per scenario;
             cost-per-verdict calculated)
                              ↓
                  fct_llm_verdicts.sql
        (the canonical fact table for LLM ops analytics)
                              ↓
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
    rpt_llm_agreement_rate         rpt_llm_cost_breakdown
    rpt_llm_latency_distribution   rpt_llm_drift_score
                              ↓
               models/semantic/llm_ops_metrics.yml
            (MetricFlow measures + dimensions)
                              ↓
                 looker/views/llm_verdicts.view.lkml
              (LookML measures parallel to MetricFlow)
                              ↓
       Looker Studio "Operational Trends" dashboard
       Next.js `/detection-lab` route
       Researcher API /llm_verdicts endpoint
```

### 10.3 The Verdict Schema (`pydantic`)

```python
# ingest/schemas/llm_verdict.py
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class Verdict(BaseModel):
    # Identity
    verdict_id: str = Field(pattern=r"^v_[a-f0-9]{16}$")
    scenario_id: Literal[
        "bot_ring", "ai_fake_artists", "family_plan_abuse",
        "geographic_anomaly", "playlist_stuffing"
    ]
    track_id: str
    provider: Literal["anthropic", "openai", "google"]
    model: str  # e.g., "claude-opus-4-7", "gpt-4o", "gemini-2.5-pro"

    # Verdict
    recommendation: Literal["recommend_no_action", "recommend_rank_lower", "recommend_remove"]
    confidence: float = Field(ge=0.0, le=1.0)
    primary_signal: Literal[
        "listen_spike", "geo_anomaly", "stream_to_listener_ratio",
        "repeat_listener_concentration", "playlist_stuffing", "none"
    ]
    reasoning: str = Field(max_length=400)
    uncertainty_flags: list[str] = []

    # Operational metadata (what the analytics measures)
    requested_at: datetime
    completed_at: datetime
    latency_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    prompt_hash: str  # sha256 for prompt-drift detection
    response_hash: str
    error_class: str | None = None  # If the call failed
```

Every field is queryable in BigQuery. Every measure on the LLM Ops dashboard derives from this fact table.

### 10.4 The Surfaced Measures (in `llm_ops_metrics.yml`)

Examples of MetricFlow measures the dashboard surfaces:

```yaml
metrics:
  - name: llm_verdict_agreement_rate
    description: "Percentage of flagged tracks where 2 of 3 providers recommend the same action"
    type: simple
    type_params:
      measure: agreement_count
    label: "LLM Agreement Rate"

  - name: llm_mean_latency_ms_by_provider
    description: "Mean latency in milliseconds, sliced by provider"
    type: simple
    type_params:
      measure: latency_ms
    label: "Mean Latency (ms)"

  - name: llm_total_cost_usd
    description: "Total USD cost across all LLM calls in the reporting window"
    type: simple
    type_params:
      measure: cost_usd
    label: "Total LLM Spend ($)"

  - name: llm_drift_score
    description: |
      Week-over-week shift in verdict-distribution. Calculated as Jensen-Shannon
      divergence between consecutive 7-day windows of verdicts per provider.
      A spike indicates the provider's behavior changed materially.
    type: derived
    type_params:
      expr: jensen_shannon_divergence(...)
    label: "Drift Score"
```

### 10.5 Why This Matters

- **Validates Spotify's automation strategy.** Spotify said in their 2025 DSA Introduction: *"As automated detection technologies continue to develop, Spotify will continue to evaluate the appropriate balance between automation and human oversight."* Cadence's LLM Ops module shows what that evaluation looks like operationally.
- **Demonstrates LLM observability hygiene.** Logging input/output tokens, cost, latency, and prompt-hashes is what you'd need to actually run LLMs in production for moderation.
- **Maps to the senior JD.** *"Performance tracking, early detection of issues, structured escalation paths"* — drift score crossing a threshold triggers a Slack alert; latency p95 crossing a threshold triggers an alert; cost-per-verdict drift triggers an alert. All wired up.


---

## 11. The Researcher API — DSA Article 40 in Practice

> *DSA Article 40 obligates VLOPs to give vetted researchers access to publicly-available platform data. Most VLOPs are still figuring out implementation. Cadence demonstrates what good Article 40 implementation looks like for transparency-report-derived data.*

### 11.1 Why This Surface Earns Its Place

Three reasons it belongs in V1:
1. **It's a real legal obligation.** [The Commission adopted the delegated act on data access](https://digital-strategy.ec.europa.eu/en/news/commission-harmonises-transparency-reporting-rules-under-digital-services-act) in July 2025. Spotify, as a VLOP, is on the hook.
2. **It demonstrates senior-shaped engineering.** The senior JD explicitly mentions *"structured escalation paths"* and *"validation frameworks that enable performance tracking, early detection of issues."* The audit logging architecture demonstrates exactly this.
3. **It would actually be useful.** Academic researchers studying platform moderation would benefit from a clean API. Today, they download four PDFs.

### 11.2 The Endpoints (V1, all real and deployed on Vercel)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/researcher_keys` | Issue a researcher key (form: name, institution, purpose, email) |
| `GET` | `/dsa/cross_product` | Cross-product DSA summary for a reporting period; query params: `period_start`, `period_end`, `product_filter` |
| `GET` | `/dsa/time_series` | Time-series for a metric across reporting periods; query params: `metric`, `product`, `granularity` |
| `GET` | `/dsa/member_state` | Per-Member-State breakdown for a reporting period |
| `GET` | `/dsa/categories` | Policy category taxonomy with v1 ↔ v2 mapping |
| `GET` | `/schema` | Full schema documentation (auto-generated from dbt manifest) |
| `GET` | `/citations/{query_id}` | Citation metadata for a previous query response |
| `GET` | `/audit/my_queries` | The current researcher's query history (from BigQuery audit table) |

Every endpoint has an OpenAPI schema, an example response, a typed pydantic model, and a unit test in `api/tests/`.

### 11.3 The Citation Contract

Every response body includes a `citation` field:

```json
{
  "data": [...],
  "citation": {
    "dataset": "cadence-public.cadence",
    "dbt_model": "rpt_cross_product_summary",
    "manifest_commit_hash": "a1b2c3d4",
    "data_refreshed_at": "2026-03-15T08:00:00Z",
    "source_reports": [
      "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_main_spotify",
      "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_artists_spotify",
      "..."
    ],
    "license": "Underlying Spotify DSA report data is published by Spotify; Cadence transformations CC-BY-4.0",
    "suggested_bibtex": "@misc{cadence_dsa_q4_2025, ... }"
  }
}
```

Researchers can cite Cadence-served data in peer-reviewed papers with full provenance.

### 11.4 Rate Limiting + Audit Logging

**Rate limiter** (`api/middleware/rate_limit.py`):
- 100 requests / 15 minutes per researcher key
- Exceeded → HTTP 429 with `Retry-After` header
- Rate-limit state stored in BigQuery (using a small `api_rate_limit_buckets` table; trade-off vs. Redis — BigQuery is what we have for free)

**Audit logger** (`api/middleware/audit_logger.py`):
- Every request logged to `cadence-public.cadence.fct_researcher_query_audit`
- Fields: `query_id`, `researcher_key_id`, `endpoint`, `query_params`, `response_size_bytes`, `latency_ms`, `requested_at`, `client_ip_hashed`
- The audit table itself is a dbt model (`models/marts/researcher/rpt_researcher_query_audit.sql`) — meta-auditable
- Spotify's own engineering can review who queried what and when, supporting the *"structured escalation paths"* requirement

### 11.5 Authentication Flow

1. Researcher submits the form on Page 3B → `/researcher_keys` endpoint
2. API validates email format, requires a non-empty institution + purpose
3. API issues a key (UUID v4, prefix `rk_`), persists to `dim_researcher_keys` table in BigQuery
4. Email-out-of-band: mock-only in V1 (the key is shown on-screen). V1.1 would add real email delivery via Resend.
5. Subsequent requests include `Authorization: Bearer rk_xxx` header
6. Failed auth → HTTP 401; quota exceeded → HTTP 429; bad query → HTTP 400 with field-level errors

### 11.6 Why This Architecture Is Honest

- No claim of being an officially-blessed Article 40 endpoint for Spotify. Cadence operates on Spotify's *publicly-published* DSA data only — what any researcher can already download.
- Researchers needing event-level data (which DSA Article 40 also enables for vetted researchers) would still need Spotify's official process. Cadence is a "what good looks like" demonstration on top of public data.
- The architecture would scale to event-level if Spotify adopted it: same dbt project, same semantic layer, same API surface, same audit logging.

---

## 12. Implementation Plan for Claude Code

> *No arbitrary hour estimation. Sprint sequence ordered by dependency. The user has indicated they will not impose limits.*

### 12.1 Sprint Sequence (Dependency-Ordered)

| Sprint | Deliverable | Acceptance |
|---|---|---|
| **0. Project scaffold** | Repo created with pyproject.toml, dbt_project.yml, profiles.yml.example (DuckDB + BigQuery dual targets), GH Actions skeleton, .pre-commit-config, README skeleton with all planned URLs as TBD placeholders | `uv sync` works, `pre-commit run --all-files` passes on a hello-world commit |
| **1. BigQuery bootstrap** | GCP project `cadence-public` created, BigQuery dataset `cadence` created, service account with read/write scoped to dataset, key file added to repo secrets, `scripts/bootstrap_bigquery.py` documented | `bq ls cadence-public:cadence` returns the dataset; dbt connection test passes for prod target |
| **2. DSA report ingestion** | `ingest/fetch_spotify_dsa.py` + `ingest/parse_dsa_report.py` for all 4 product lines + 2 reporting periods minimum; pydantic schemas; Parquet outputs; raw_* tables in BQ | Running `python -m ingest.fetch_spotify_dsa` produces 8+ Parquet files; `python -m ingest.parse_dsa_report` validates them; raw tables visible in BQ console |
| **3. Synthetic data generator** | `ingest/synth_streams.py` + `ingest/synth_fraud_scenarios.py`; deterministic; pydantic-validated; 5M streams + 5 embedded fraud scenarios | Running once produces fixed-hash Parquet; running twice produces identical hashes |
| **4. dbt staging layer** | All `stg_*` models for both DSA real data and synthetic streams; sources.yml; basic tests | `dbt build --select staging --target dev` passes (DuckDB); ~50 tests |
| **5. dbt intermediate + marts/transparency** | `int_dsa_unified` (the cross-product unification) + all marts/transparency models | `dbt build --select transparency --target dev` passes; `assert_dsa_period_continuity` and `assert_dsa_categories_consistent_2025` both green |
| **6. dbt marts/safety + detection signals** | All 5 sig_* models + fct_artificial_streaming_flags; `assert_synthetic_fraud_caught` test | All 5 fraud scenarios flagged with score ≥ 70 |
| **7. LLM verdict pre-cache + dbt llm_ops marts** | `precache_llm_verdicts.py` calls real Claude/GPT-4o/Gemini; verdicts persisted to BQ; `fct_llm_verdicts` + 4 rpt_llm_* models | 5 scenarios × 3 providers = 15 verdicts in BQ; `rpt_llm_agreement_rate` returns sensible numbers |
| **8. Semantic layers — MetricFlow + LookML** | `safety_metrics.yml`, `transparency_metrics.yml`, `llm_ops_metrics.yml` (MetricFlow); parallel `cadence.model.lkml` + view files (LookML); validation via `lkmltools` | `dbt sl validate-configs` passes; `lkmltools` validation passes |
| **9. dbt-expectations + custom tests for full 200+ test count** | Distribution, regex, anomaly tests; meta-testing for descriptions | `dbt build` total test count ≥ 200; all green |
| **10. Looker Studio dashboards (3, deployed)** | "Cross-Product Executive Summary," "Operational Trends," "Member-State Heatmap" — published, public URLs in repo README | All 3 URLs return 200 OK and render charts backed by BQ |
| **11. FastAPI researcher API on Vercel** | All 9 endpoints, OpenAPI spec, pydantic models, rate limiter, audit logger, deployed | Live URL responds; Swagger UI loads; `curl /dsa/cross_product` returns valid JSON; rate limit kicks in at 101st request |
| **12. Airflow DAG with Astro CLI** | `cadence_refresh.py` with 8 tasks, runs locally via `astro dev start`, screenshots in repo | DAG visible in Airflow UI; manual trigger runs all 8 tasks green |
| **13. Next.js app — Lakehouse + Detection Lab + Methodology** | The 3 highest-priority routes for the recruiter path; server components fetch from BigQuery via `@google-cloud/bigquery`; shadcn/ui Cards, Tables, Dialogs, Accordions; Recharts for charts; LLM verdict transcripts in Dialog modals; Mermaid for inline lineage diagrams | Recruiter path 0:00 → 2:00 works on the deployed Vercel URL |
| **14. Next.js app — Researcher landing + Explorer + Analyst Console** | `/researcher-api`, `/explorer`, `/analyst-console` routes; embedded Swagger UI iframe for the live FastAPI service; MetricFlow query playground; interactive dbt DAG via React Flow | Recruiter path 1:00 → 2:35 works |
| **15. Next.js app — BI Governance + Teardown + About** | `/bi-governance`, `/teardown`, `/about` routes; About page has the explicit JD Mapping Table with deployed-URL links per requirement | About page has every JD requirement crossed off with a deployed-URL link |
| **16. CI green on main + dbt docs deploy** | All 6 CI jobs green; dbt docs published to GH Pages | README badge green; `https://AliHasan-786.github.io/cadence/` loads |
| **17. End-to-end recruiter QA** | Run the 0:00 → 3:00 path; fix any rough edges; verify <60s setup contract | Time-to-first-insight measured at <60s on a clean machine |

### 12.2 Parallelization Notes

- Sprint 1 (BigQuery bootstrap) and Sprint 3 (synthetic data) can run in parallel after Sprint 0
- Sprint 2 (DSA ingestion) and Sprint 7 (LLM pre-cache) can run in parallel after the BQ dataset exists
- Sprints 4–9 (dbt) are mostly sequential because each layer depends on the prior
- Sprints 10 (Looker), 11 (API), 12 (Airflow), 13–15 (Next.js) can run in parallel after dbt builds successfully

### 12.3 Daily Definition of Done

Every push to main must:
1. Pass `pre-commit run --all-files` (ruff + sqlfluff + mypy)
2. Pass `dbt build --target dev` (DuckDB) with all 200+ tests green
3. Pass `dbt build --target prod_ci` (BigQuery) with the same suite
4. Pass `python scripts/verify_round_trip.py`
5. Pass `cd api && pytest` (FastAPI tests)
6. Pass `cd airflow && pytest tests/` (DAG validity)
7. Successfully publish `dbt docs` to GH Pages

If main is red for >24h, all other work stops until main is green. (Spotify's [Padlock](https://engineering.atspotify.com/padlock) principle — you don't ship on top of a broken build.)

---

## 13. Acceptance Criteria — The Acquisition Bar

> *"So strong and good that Spotify would literally want to acquire it." That's the standard. Each of these is a hard gate.*

### 13.1 The Hard Gates (must all pass)

- [ ] **Single-command setup** verified on a clean machine: `git clone && uv sync && pnpm install && pnpm dev` completes in <60s (the Next.js dev server boots and the BigQuery connection succeeds)
- [ ] **All 4 Spotify DSA reports** for at least 1 reporting period are parsed, loaded, and surfaced in the Cross-Product dashboard
- [ ] **8+ DSA reports** total when including 2 reporting periods (4 products × 2 periods)
- [ ] **Cross-product reconciliation tests pass** — `assert_dsa_period_continuity` and `assert_dsa_categories_consistent_2025` both green
- [ ] **50+ dbt models** built successfully on both DuckDB (dev) and BigQuery (prod) targets
- [ ] **200+ dbt tests** passing on both targets
- [ ] **5 fraud scenarios** all flagged at score ≥ 70 (verified by `assert_synthetic_fraud_caught.sql`)
- [ ] **3 LLM providers** integrated, all returning schema-valid verdicts persisted to BigQuery
- [ ] **3 Looker Studio dashboards** deployed with public URLs, backed by BigQuery, refreshing on the Airflow DAG schedule
- [ ] **FastAPI researcher API deployed** on Vercel with public URL; Swagger UI loads; rate limiter works; audit logger writes to BQ
- [ ] **Airflow DAG runs** successfully end-to-end via Astro CLI; screenshots in repo
- [ ] **Methodology page renders from source** — verify by editing a weight in `safety_metrics.yml`, push, see the page reflect it
- [ ] **BI Governance page** documents certified registry, owner attribution, deprecation policy, naming conventions, change management
- [ ] **GitHub Actions CI green on main** with badge in README
- [ ] **dbt docs deployed** to GitHub Pages with public URL
- [ ] **Vercel deployment** with stable public URL covering all 9 pages
- [ ] **JD Mapping Table** in About page maps every JD requirement (both Associate + Senior) to a Cadence feature with a deployed-URL link
- [ ] **Honest scope statement (§14)** rendered both in README and in-app on Teardown + About

### 13.2 The Recruiter-Playable Bar

The 0:00 → 3:00 recruiter path in §5.5 must work end-to-end on the deployed app with no setup, no demo, no narration. If anything in that path takes >15 seconds to recover from, it gets fixed before the resume goes out.

### 13.3 Self-Audit Questions (answer honestly before declaring done)

1. **Would a Spotify Compliance Counsel actually use the Cross-Product dashboard?** If she'd open it once, see something useful, and bookmark it — yes. If it's a toy demo — fix.
2. **Would a Spotify T&S Engineer trust the Detection Lab numbers?** If the lineage is clean and the tests pass, yes. If it's hand-tuned to look impressive — fix.
3. **Would an academic researcher cite the Researcher API in a paper?** If the citation contract works and the data has clear provenance — yes.
4. **Is every named tool genuinely in use?** BigQuery has real data; Looker Studio has real dashboards; Airflow has a real DAG; FastAPI has a real endpoint. No theatre.
5. **Does it match AgentRadar's polish?** Open both apps side-by-side. If AgentRadar feels more polished, ship more.
6. **If Spotify wanted to embed this internally, could they?** Connection string change for BigQuery → their internal BigQuery. Service account swap. Looker license. The dbt project, the FastAPI service, and the Airflow DAG move as-is.

### 13.4 Operational Health Checks

After deployment, the following should be observable:
- BigQuery query cost per day (tracked via the Cloud Billing free-tier dashboard)
- Vercel function invocations (researcher API)
- Vercel uptime
- Looker Studio dashboard view count
- Airflow DAG run history (success rate)
- LLM API spend (should be near $0 due to caching)

A dedicated `Health` page (V1.1) would surface these. V1 documents them in the README.

---

## 14. What Cadence is NOT

> *Honest scope statement. Render this in the README, on Page 8 (Teardown) section 8D, and on Page 9 (About).*

- **Cadence is NOT real Spotify event-level data.** The DSA Transparency Report data ingested is real, public, and sourced from Spotify's own publications. The stream-event data and moderation actions in the Detection Lab are synthetic, generated deterministically. Synthetic is clearly labeled `_synth` in BigQuery and on every UI page footer.

- **Cadence is NOT a Spotify product.** It is a candidate's portfolio piece for the Spotify Analytics Engineer (Trust & Safety) application. Spotify is not affiliated. The Spotify-green accent color is used as a single accent only and does not imply endorsement.

- **Cadence is NOT a substitute for Spotify's official DSA reporting.** Cadence's published numbers reflect *Spotify's own published numbers*, transformed for cross-product navigation. Any discrepancy between Cadence and Spotify's official reports is a bug — official reports are authoritative.

- **Cadence is NOT an officially-blessed DSA Article 40 endpoint.** Researchers wanting event-level platform data still need Spotify's official researcher-vetting process. Cadence's API operates on the publicly-published DSA report data only — what any researcher can already download.

- **Cadence is NOT an empirically-validated fraud detector.** The composite suspicion score is a heuristic with weights chosen to be reasonable based on public industry research (HUMAN Security taxonomy). Reasonable people may weight differently. The test guarantee is "the 5 embedded synthetic fraud scenarios are all flagged with score ≥ 70," not "this would catch all real-world fraud."

- **Cadence is NOT trained ML.** V1 uses heuristic signals + LLM verdicts. V1.4 adds an ML layer (logistic regression + gradient-boosted trees on labeled signals) alongside the heuristic baseline.

- **Cadence is NOT a real-time fraud detector.** It runs as batch dbt models. Real-time streaming detection (Kafka → BigQuery → dbt incremental models) is V1.5.

- **Cadence is NOT free at scale.** V1 fits in BigQuery's free tier (10GB / 1TB query). At Spotify's actual scale (8M events/sec per Acceldata's public analysis), the architecture moves to a paid Enterprise tier and the dbt incremental materializations replace full refreshes. The architecture is portable; the free tier is for the demo.

- **Cadence is NOT a substitute for legal review.** The cross-product DSA dashboard is technically accurate per Spotify's published source data, but a real DSA filing or Article 40 response requires legal sign-off, regulatory consultation, and validation against internal Spotify systems Cadence does not access.

- **Cadence does NOT scrape, infer, or fabricate data Spotify hasn't published.** If the harmonised template doesn't include Member State coverage for a product line, Cadence shows that gap honestly rather than guessing.

---

## 15. Sources & Citations

> *All sources verified accessible at time of writing. Render this list in the About page and inline as numbered chips throughout.*

### Spotify-specific (verified accessible)

- **[1]** Spotify. Safety and Privacy Center: Transparency. Lists all 4 DSA reports as XLSX downloads. https://www.spotify.com/us/safetyandprivacy/transparency
- **[2]** Spotify. DSA Transparency Report 2025 Introduction. Published 27 February 2026. https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_introduction_spotify
- **[3]** Spotify. DSA Article 24 Information. https://www.spotify.com/safetyandprivacy/dsa-article-24-information
- **[4]** Spotify. DSA Article 15 Information. https://www.spotify.com/safetyandprivacy/dsa-article-15-information
- **[5]** Spotify Newsroom. EU Digital Services Act Transparency Report 2025. https://newsroom.spotify.com/eu-digital-services-act-transparency-report-2025/
- **[6]** Spotify. DSA Points of Contact. https://www.spotify.com/de-en/safetyandprivacy/dsa-points-of-contact
- **[7]** Spotify Newsroom. Combating Artificial Streaming. https://newsroom.spotify.com/2024-09-25/combating-artificial-streaming/
- **[8]** Spotify for Artists. Artificial Streaming policy + Music Spam policy. https://artists.spotify.com/en/artificial-streaming
- **[9]** Spotify Engineering. Padlock service-protection. https://engineering.atspotify.com/padlock
- **[10]** Music Business Worldwide. "Spotify has deleted 75m+ tracks in 'spammy' AI music crackdown." Sept 25, 2025. https://www.musicbusinessworldwide.com/spotify-has-deleted-75m-spammy-tracks-as-it-unveils-new-ai-music-policies/

### EU regulation (verified accessible)

- **[11]** European Commission. Implementing Regulation 2024/2835 (transparency report templates). Effective 1 July 2025. https://digital-strategy.ec.europa.eu/en/news/commission-harmonises-transparency-reporting-rules-under-digital-services-act
- **[12]** European Commission. How the DSA enhances transparency online. Confirms first harmonised reports published February 2026. https://digital-strategy.ec.europa.eu/en/policies/dsa-brings-transparency

### Industry & academic research (verified accessible)

- **[13]** HIIG (Humboldt Institute for Internet & Society). "What's in the new DSA transparency reports? An analysis." Dec 10, 2025. https://www.hiig.de/en/analysis-of-the-dsas-transparency-reports/
- **[14]** Tessa, Trujillo, Cresci et al. "The DSA Transparency Database: Auditing Self-reported Moderation Actions by Social Media." arXiv 2312.10269 / PACM HCI. https://arxiv.org/abs/2312.10269
- **[15]** Tessa, Amram, Monreale, Cresci. "Improving Regulatory Oversight in Online Content Moderation." arXiv 2506.04145 (June 2025). https://arxiv.org/pdf/2506.04145
- **[16]** TechPolicy.Press. "Is The Digital Services Act Truly A Transparency Machine?" 19-VLOP comparative analysis. https://www.techpolicy.press/is-the-digital-services-act-truly-a-transparency-machine/
- **[17]** HUMAN Security. "AI-Powered Streaming Fraud: How to Make a Hit Song Nobody Listens To." January 2026. The five-signal taxonomy + Selenium/Puppeteer/proxies + Rainy Day Lo-Fi naming. https://www.humansecurity.com/learn/blog/ai-powered-streaming-fraud/
- **[18]** Dark Reading coverage of HUMAN Security streaming fraud research. https://www.darkreading.com/threat-intelligence/streaming-fraud-campaigns-rely-on-ai-tools-bots
- **[19]** FUGA. Spotify Artificial Streaming Penalty (€10/track effective April 1, 2024). https://support.fuga.com/hc/en-us/articles/36690008503700-Understanding-Spotify-s-Artificial-Streaming-Penalty-and-FUGA-s-Enforcement-Policy
- **[20]** Music Business Worldwide. Music Fights Fraud Alliance + Merlin joining (May 2025). Confirms founding members are CD Baby/Downtown, TuneCore/Believe, DistroKid, UnitedMasters, Symphonic, EMPIRE, Vydia + Spotify + Amazon Music. https://www.musicbusinessworldwide.com/merlin-joins-music-fights-fraud-alliance-to-tackle-streaming-fraud/
- **[21]** PRWeb. Music Fights Fraud Alliance launch announcement. June 14, 2023. https://www.prweb.com/releases/Music_Platforms_Unite_To_Form_Industry_Wide_Anti_Fraud_Alliance_Music_Fights_Fraud_/prweb19393090.htm

### Spotify roles (the targets — verified accessible)

- **[22]** Spotify. Associate Analytics Engineer (Trust & Safety) — the primary target role. https://jobs.lever.co/spotify/d95e1989-9a1a-4853-95b1-ecdebf5f81ff
- **[23]** Spotify. Analytics Engineer, Trust & Safety Infrastructure — confirms BigQuery + Airflow/Flyte + Looker + Tableau + BI governance stack. https://jobs.lever.co/spotify/54ab7173-774b-410b-a05d-5746ab78632f

### Tooling references

- **[24]** dbt Labs. dbt-core documentation. https://docs.getdbt.com/docs/introduction
- **[25]** dbt-expectations. https://github.com/calogica/dbt-expectations
- **[26]** dbt MetricFlow. https://docs.getdbt.com/docs/build/about-metricflow
- **[27]** Looker Studio. Free GCP-native BI. https://lookerstudio.google.com/
- **[28]** Astronomer. Astro CLI for local Airflow. https://www.astronomer.io/docs/astro/cli/overview/
- **[29]** Acceldata. "Inside Spotify's Data Strategy." 8M events/sec, 500B/day, 70TB ingestion. https://www.acceldata.io/blog/spotifys-data-strategy

### Adjacent / informative

- **[30]** AgentRadar. The candidate's existing portfolio piece for Shopify APM Fall 2026. The quality bar Cadence aims to match in explainability and recruiter-playability. https://agent-radar-o4fn.vercel.app/ + https://github.com/AliHasan-786/AgentRadar
- **[31]** Cornell Tech News. "Red Team Students Stress-Test NYC Health Department's AI." Dec 16, 2025. The candidate's role context. https://tech.cornell.edu/news/red-team-clinic-cornell-tech/

---

*End of PRD v3. Build it. Dream big. The free tier is generous. The standard is acquisition-grade.*
