"""Load precache/synth/raw_llm_verdicts.parquet → cadence_raw.raw_llm_verdicts."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq
from google.cloud import bigquery
from google.oauth2 import service_account

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET = REPO_ROOT / "precache" / "synth" / "raw_llm_verdicts.parquet"

PROJECT_ID = "spry-smithy-489221-p4"
DATASET_RAW = "cadence_raw"
LOCATION = "US"
TABLE = "raw_llm_verdicts"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not PARQUET.exists():
        print(f"ERROR: {PARQUET} missing — run precache_llm_verdicts first", file=sys.stderr)
        return 1

    keyfile = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    creds = service_account.Credentials.from_service_account_file(keyfile)
    client = bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)

    meta = pq.read_metadata(PARQUET)
    print(
        f"Loading {meta.num_rows} verdicts ({PARQUET.stat().st_size / 1024:.1f} KB) → "
        f"{PROJECT_ID}.{DATASET_RAW}.{TABLE}"
    )
    if args.dry_run:
        return 0

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )
    with PARQUET.open("rb") as fh:
        job = client.load_table_from_file(
            fh,
            destination=f"{PROJECT_ID}.{DATASET_RAW}.{TABLE}",
            job_config=job_config,
            location=LOCATION,
        )
    job.result()
    print(f"  ✓ loaded {job.output_rows} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
