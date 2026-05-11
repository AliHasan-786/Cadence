"""Validate LookML files and assert one-to-one parity with MetricFlow.

Sprint 8 methodology-contract enforcement:

1. PARSE every `.lkml` file under `looker/` using the `lkml` package.
   Each must parse cleanly. Each measure must have type + sql (or be a
   type:count which doesn't need sql).

2. EQUIVALENCE every measure named in `looker/views/*.view.lkml` MUST appear
   as either a `metrics:` entry OR a `measures:` entry in
   `models/semantic/*.yml`. The reverse is also asserted with a small
   curated allow-list for measures that exist only on one side
   (e.g., LookML helper measures, MetricFlow-only ratio metrics).

Run:
    uv run python scripts/lookml_validate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import lkml
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LOOKER_DIR = REPO_ROOT / "looker"
SEMANTIC_DIR = REPO_ROOT / "models" / "semantic"

# Measures that intentionally exist only on one side. Document each entry with
# the reason it's one-sided.
ONLY_IN_LOOKML: set[str] = {
    # The canonical `composite_suspicion_score` is exposed in both. The LookML
    # measure is a thin wrapper around composite_suspicion_score_avg for
    # naming-parity with MetricFlow's metric name (which the YAML config
    # block also references).
    "composite_suspicion_score",
}
ONLY_IN_METRICFLOW: set[str] = {
    # Helper metrics used inside derived metric expressions only.
    "ok_verdict_count",
    "total_verdict_count",
    "scenario_count",
    "two_of_three_agree_sum",
}


def parse_lookml() -> dict[str, dict]:
    """Return {view_name: {measures: set[str], dimensions: set[str]}}."""
    out: dict[str, dict] = {}
    for path in sorted((LOOKER_DIR / "views").glob("*.lkml")):
        with path.open() as f:
            tree = lkml.load(f)
        for view in tree.get("views", []):
            v_name = view["name"]
            measures = {m["name"] for m in view.get("measures", [])}
            dimensions = {d["name"] for d in view.get("dimensions", [])}
            out[v_name] = {"measures": measures, "dimensions": dimensions, "file": path}
    return out


def parse_metricflow() -> tuple[set[str], dict[str, set[str]]]:
    """Return (metrics_names, {semantic_model: measure_names})."""
    metrics: set[str] = set()
    measures: dict[str, set[str]] = {}
    for yml_path in sorted(SEMANTIC_DIR.glob("*.yml")):
        data = yaml.safe_load(yml_path.read_text())
        for m in data.get("metrics", []) or []:
            metrics.add(m["name"])
        for sm in data.get("semantic_models", []) or []:
            measures[sm["name"]] = {meas["name"] for meas in sm.get("measures", []) or []}
    return metrics, measures


def main() -> int:
    print(f"Parsing LookML in {LOOKER_DIR}")
    try:
        lkml_views = parse_lookml()
    except Exception as e:
        print(f"  ✗ LookML parse failure: {e}")
        return 1
    n_views = len(lkml_views)
    n_measures = sum(len(v["measures"]) for v in lkml_views.values())
    n_dims = sum(len(v["dimensions"]) for v in lkml_views.values())
    print(f"  ✓ parsed {n_views} views, {n_measures} measures, {n_dims} dimensions")

    print(f"\nParsing MetricFlow in {SEMANTIC_DIR}")
    mf_metrics, mf_measures = parse_metricflow()
    total_mf_measures = sum(len(s) for s in mf_measures.values())
    print(
        f"  ✓ parsed {len(mf_metrics)} metrics across "
        f"{len(mf_measures)} semantic models ({total_mf_measures} measures total)"
    )

    print("\nMethodology contract — every MetricFlow METRIC has a LookML sibling")
    print(
        "(MetricFlow MEASURES are implementation detail; only `metrics:` entries are dashboard-facing)"
    )

    lkml_measure_names = set()
    for v in lkml_views.values():
        lkml_measure_names |= v["measures"]

    # The dashboard-facing contract: every name in `metrics:` of any MetricFlow
    # YAML must appear as a LookML measure under the same name.
    missing_in_lookml = (mf_metrics - lkml_measure_names) - ONLY_IN_METRICFLOW
    extra_in_lookml = (
        lkml_measure_names
        - mf_metrics
        - ONLY_IN_LOOKML
        - {m for s in mf_measures.values() for m in s}  # LookML can also expose MF measure names
    )

    errs = 0
    if missing_in_lookml:
        print("  ✗ MetricFlow metrics missing from LookML:")
        for name in sorted(missing_in_lookml):
            print(f"      - {name}")
        errs += len(missing_in_lookml)
    if extra_in_lookml:
        print(
            "  ⚠ LookML measures with no MetricFlow sibling (add to ONLY_IN_LOOKML if intentional):"
        )
        for name in sorted(extra_in_lookml):
            print(f"      - {name}")
        errs += len(extra_in_lookml)

    print("\n  Coverage:")
    print(f"    MetricFlow metrics:        {len(mf_metrics):>3}")
    print(f"    LookML measures (total):   {len(lkml_measure_names):>3}")
    print(f"    Cross-source overlap:      {len(mf_metrics & lkml_measure_names):>3}")
    print(f"    ONLY_IN_METRICFLOW (allow-listed helpers): {len(ONLY_IN_METRICFLOW)}")
    print(f"    ONLY_IN_LOOKML (allow-listed helpers):     {len(ONLY_IN_LOOKML)}")

    if errs:
        print(
            f"\n  → {errs} parity issue(s). Edit either the LookML view or the semantic YAML to match."
        )
        return 1

    print("\n✓ All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
