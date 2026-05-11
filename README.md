# Cadence

> The analytics engineering layer Spotify's DSA reports deserve.

A unified analytics engineering platform that ingests Spotify's four DSA Transparency Reports (Main, Artists, Authors, Creators), normalizes them through dbt on BigQuery, and surfaces them via Looker Studio, a Next.js frontend, and a DSA Article 40 researcher API.

## Live URLs

- **🔬 Researcher API:** https://cadence-ashen.vercel.app
- **📖 API Swagger UI:** https://cadence-ashen.vercel.app/docs
- **📊 Looker Studio — Cross-Product Executive Summary:** _(TBD — Sprint 10 dashboard build)_
- **📈 Looker Studio — Operational Trends:** _(TBD — Sprint 10 dashboard build)_
- **🗺️ Looker Studio — Member-State Heatmap:** _(TBD — Sprint 10 dashboard build)_
- **🔧 dbt docs:** _(TBD — Sprint 16 GH Pages deploy)_

## Status

**Sprints 0–11 deployed.** Real Spotify DSA data ingested + dbt marts + LLM verdicts + semantic layers + live researcher API.

## Stack (in flight)

- **Warehouse:** BigQuery (project `spry-smithy-489221-p4`, datasets `cadence_raw` + `cadence`); DuckDB for local dev
- **Transformation:** dbt-core 1.8 (staging → intermediate → marts)
- **Orchestration:** Airflow via Astro CLI
- **BI:** Looker Studio
- **Frontend:** Next.js 15 + TypeScript + Tailwind + shadcn/ui (Vercel)
- **API:** FastAPI + OpenAPI 3.1 (Vercel)
- **CI:** GitHub Actions (ruff + sqlfluff + mypy + dbt build + dbt test)

## Setup

```bash
# Install Python deps
uv sync

# Copy and edit profile
cp profiles.yml.example ~/.dbt/profiles.yml

# Point at your BigQuery service-account key (see scripts/bootstrap_bigquery.md)
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/cadence-sa.json

# Bootstrap BigQuery datasets
uv run python scripts/bootstrap_bigquery.py

# Pull dbt deps (once models exist)
uv run dbt deps

# Verify connection
uv run dbt debug --target prod
```

## Running the DSA ingestion (Sprints 1–2)

```bash
# Fetch the four Spotify 2025 H2 XLSX annexes
uv run python -m ingest.fetch_spotify_dsa --period 2025H2

# Parse → pydantic validate → Parquet under precache/dsa_reports/
uv run python -m ingest.parse_dsa_report --period 2025H2

# Load Parquet → BigQuery raw_* tables in cadence_raw
uv run python -m ingest.load_to_bigquery --period 2025H2
```

## Repo layout (sprint 0–2 footprint)

```
cadence/
├── pyproject.toml
├── dbt_project.yml
├── profiles.yml.example
├── packages.yml
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml         # CI skeleton (jobs filled in later sprints)
├── ingest/
│   ├── fetch_spotify_dsa.py         # Downloads 4 XLSX annexes
│   ├── parse_dsa_report.py          # XLSX → pydantic → Parquet
│   ├── load_to_bigquery.py          # Parquet → BQ raw_* tables
│   └── schemas/
│       ├── dsa_main_v2.py
│       ├── dsa_artists_v2.py
│       ├── dsa_authors_v2.py
│       └── dsa_creators_v2.py
├── scripts/
│   ├── bootstrap_bigquery.py        # Creates cadence_raw + cadence datasets
│   └── bootstrap_bigquery.md        # SA setup instructions
└── precache/
    └── dsa_reports/                 # Parquet outputs (committed)
```

## Scope honesty

Cadence ingests **real** Spotify DSA report data. Synthetic stream-event data (sprint 3+) will be clearly labeled `_synth`. Cadence is not affiliated with Spotify; the Spotify-green accent is used as a single accent color only. See §14 of the PRD for the full "what Cadence is NOT" statement.

## License

Code: MIT. Underlying Spotify DSA report data is published by Spotify; Cadence transformations: CC-BY-4.0.
