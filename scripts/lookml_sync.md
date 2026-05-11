# Methodology contract — keeping MetricFlow and LookML in sync

Cadence has TWO semantic-layer implementations:

1. **MetricFlow** under `models/semantic/*.yml`
2. **LookML** under `looker/cadence.model.lkml` + `looker/views/*.view.lkml`

Both consume the same `fct_*` tables. Every metric exposed in one MUST be
exposed under the same name in the other — or the Methodology page renders
one set of numbers while the Looker Studio dashboard shows another, and
the methodology contract collapses.

## The sync rule

For every `metrics:` entry in `models/semantic/<scope>_metrics.yml`, there
must be a sibling `measure:` (or `dimension:`) in `looker/views/<scope>.view.lkml`
with:

- the **same name** (snake_case),
- a description that references the MetricFlow metric name,
- semantically equivalent SQL.

## How to check

Run the validator script:

```bash
uv run python scripts/lookml_validate.py
```

This script:

1. Parses every `.lkml` file in `looker/` via the `lkml` package.
2. Loads every `metrics:` entry from `models/semantic/*.yml`.
3. Reports any name that exists in one source but not the other.
4. Exits non-zero on mismatch.

## How to regenerate (V1.1)

Today the LookML is hand-written and the validator catches drift. Sprint 9
adds `scripts/sync_lookml_from_yaml.py` which generates the LookML from
the semantic YAML directly. Until then: edit YAML first, then mirror to LookML,
then run the validator.

## Why two parallel sources at all

LookML is consumed by Looker Studio's native LookML data sources (some
Spotify teams use Looker for embedded analytics). MetricFlow is consumed
by dbt Cloud's semantic layer, the Next.js Explorer page, and the Researcher
API. The two consumer ecosystems aren't compatible — hence the parallel
implementations + the contract that keeps them aligned.
