connection: "cadence_bigquery"

include: "views/*.view.lkml"
include: "explores/*.explore.lkml"

# Cadence LookML model.
# Mirrors the MetricFlow semantic layer in models/semantic/. Every measure
# named in this file MUST have a sibling under the same name in
# models/semantic/<safety|transparency|llm_ops>_metrics.yml's `metrics:` or
# `measures:` block. scripts/lookml_sync.md documents the equivalence check.

label: "Cadence — Spotify DSA + Detection Lab"
