"""Load synthetic Parquet files into BigQuery cadence_raw.

Six Parquet → six tables, named with the canonical `raw_<entity>_synth` suffix
so downstream consumers can never mistake synthetic for real:

    raw_users_synth.parquet              → cadence_raw.raw_users_synth
    raw_artists_synth.parquet            → cadence_raw.raw_artists_synth
    raw_tracks_synth.parquet             → cadence_raw.raw_tracks_synth
    raw_streams_synth.parquet            → cadence_raw.raw_streams_synth
    raw_moderation_actions_synth.parquet → cadence_raw.raw_moderation_actions_synth
    raw_appeals_synth.parquet            → cadence_raw.raw_appeals_synth

Streams load chunks Parquet upload at 10MB increments — the load API handles
this transparently. Reload is WRITE_TRUNCATE — safe to re-run after a fresh
synth_generate.

Usage:
    uv run python -m ingest.load_synth_to_bigquery
    uv run python -m ingest.load_synth_to_bigquery --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq
from google.api_core import exceptions as gax
from google.cloud import bigquery
from google.oauth2 import service_account

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNTH_DIR = REPO_ROOT / "precache" / "synth"

PROJECT_ID = "spry-smithy-489221-p4"
DATASET_RAW = "cadence_raw"
LOCATION = "US"

TABLES = [
    "raw_users_synth",
    "raw_artists_synth",
    "raw_tracks_synth",
    "raw_streams_synth",
    "raw_moderation_actions_synth",
    "raw_appeals_synth",
]


def _client() -> bigquery.Client:
    keyfile = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if keyfile and Path(keyfile).expanduser().exists():
        creds = service_account.Credentials.from_service_account_file(
            str(Path(keyfile).expanduser()),
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def load_synth(dry_run: bool = False) -> list[dict]:
    client = _client()
    try:
        client.get_dataset(f"{PROJECT_ID}.{DATASET_RAW}")
    except gax.NotFound as e:
        raise RuntimeError(
            f"Dataset {PROJECT_ID}.{DATASET_RAW} not found. "
            f"Run `uv run python scripts/bootstrap_bigquery.py` first."
        ) from e

    results = []
    for table_name in TABLES:
        parquet_path = SYNTH_DIR / f"{table_name}.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(
                f"{parquet_path} missing — run `uv run python -m ingest.synth_generate` first"
            )

        meta = pq.read_metadata(parquet_path)
        rows = meta.num_rows
        size_mb = parquet_path.stat().st_size / (1024 * 1024)
        table_id = f"{PROJECT_ID}.{DATASET_RAW}.{table_name}"

        verb = "Validating" if dry_run else "Loading"
        print(f"{verb} {table_name}  ({rows:,} rows, {size_mb:.2f} MB) → {table_id}")

        if dry_run:
            results.append({"table_id": table_id, "rows": rows, "bytes_mb": size_mb})
            continue

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        )
        with parquet_path.open("rb") as fh:
            job = client.load_table_from_file(
                fh,
                destination=table_id,
                job_config=job_config,
                location=LOCATION,
            )
        job.result()
        print(f"  ✓ loaded {job.output_rows:,} rows")
        results.append(
            {
                "table_id": table_id,
                "rows": job.output_rows,
                "bytes_mb": size_mb,
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    results = load_synth(dry_run=args.dry_run)

    print("\n" + "=" * 80)
    print(f"{'DRY-RUN' if args.dry_run else 'LOAD'} SUMMARY")
    print("=" * 80)
    total_rows = sum(r["rows"] for r in results)
    total_mb = sum(r["bytes_mb"] for r in results)
    print(f"  {len(results)} synth tables in {PROJECT_ID}.{DATASET_RAW}")
    print(f"  {total_rows:,} total rows, {total_mb:.1f} MB on disk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
