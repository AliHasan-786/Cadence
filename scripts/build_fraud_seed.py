"""Derive seeds/fraud_scenario_expectations.csv from precache/fraud_scenarios/*.json.

The JSONs are the ground truth produced by ingest/synth_generate.py.
The seed they produce is what `assert_synthetic_fraud_caught.sql` joins
against — for each (scenario, track), what composite score does the fraud
catch test expect?

Re-run whenever you regenerate synthetic data.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAUD_DIR = REPO_ROOT / "precache" / "fraud_scenarios"
OUT = REPO_ROOT / "seeds" / "fraud_scenario_expectations.csv"


def main() -> int:
    rows: list[dict[str, object]] = []
    for json_path in sorted(FRAUD_DIR.glob("*.json")):
        scenario = json.loads(json_path.read_text())
        sid = scenario["scenario_id"]
        min_score = scenario["expected_score_min"]
        track_ids = scenario.get("track_ids") or []
        for tid in track_ids:
            rows.append(
                {
                    "scenario_id": sid,
                    "track_id": tid,
                    "expected_min_score": min_score,
                }
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "track_id", "expected_min_score"])
        w.writeheader()
        w.writerows(rows)

    print(
        f"Wrote {len(rows)} expectation rows across "
        f"{len(set(r['scenario_id'] for r in rows))} scenarios → {OUT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
