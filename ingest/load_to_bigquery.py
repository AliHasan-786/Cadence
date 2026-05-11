"""Load parsed Parquet files into BigQuery raw_* tables.

For each of the 9 sheets in the harmonised template, this loads all 4 product
Parquet files for a given period as a single union into one BigQuery table
in dataset `cadence_raw`. Naming convention: `raw_dsa_<sheet_slug>`.

Tables are CREATE_IF_NEEDED + WRITE_TRUNCATE for the matching period — safe
to re-run.

Usage:
    uv run python -m ingest.load_to_bigquery --period 2025H2
    uv run python -m ingest.load_to_bigquery --period 2025H2 --dry-run   # validate only
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
from google.api_core import exceptions as gax
from google.cloud import bigquery
from google.oauth2 import service_account

from ingest.schemas.dsa_harmonised_v2 import SHEET_REGISTRY

REPO_ROOT = Path(__file__).resolve().parent.parent
PARQUET_DIR = REPO_ROOT / "precache" / "dsa_reports" / "parquet"

PROJECT_ID = "spry-smithy-489221-p4"
DATASET_RAW = "cadence_raw"
LOCATION = "US"
PRODUCTS = ("main", "artists", "authors", "creators")


@dataclass
class LoadResult:
    sheet_slug: str
    table_id: str
    rows_loaded: int
    bytes_loaded: int


def _client() -> bigquery.Client:
    keyfile = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if keyfile and Path(keyfile).expanduser().exists():
        creds = service_account.Credentials.from_service_account_file(
            str(Path(keyfile).expanduser()),
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def _load_sheet(
    client: bigquery.Client,
    sheet_slug: str,
    period: str,
    dry_run: bool,
) -> LoadResult:
    # Concatenate the 4 product Parquet files for this sheet
    parquet_paths = [
        PARQUET_DIR / f"{prod}_{period}" / f"{sheet_slug}.parquet"
        for prod in PRODUCTS
    ]
    missing = [p for p in parquet_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"missing Parquet inputs for sheet {sheet_slug}: "
            + ", ".join(str(p.relative_to(REPO_ROOT)) for p in missing)
        )

    table_id = f"{PROJECT_ID}.{DATASET_RAW}.raw_dsa_{sheet_slug}"

    # Verify all 4 inputs share the same arrow schema (defense-in-depth)
    schemas = [pq.read_table(p).schema for p in parquet_paths]
    canonical = schemas[0]
    for path, schema in zip(parquet_paths, schemas, strict=True):
        if not schema.equals(canonical):
            raise RuntimeError(
                f"schema mismatch between {path.name} and {parquet_paths[0].name} "
                f"for sheet {sheet_slug}"
            )

    total_rows = sum(pq.read_metadata(p).num_rows for p in parquet_paths)
    total_bytes = sum(p.stat().st_size for p in parquet_paths)

    if dry_run:
        return LoadResult(
            sheet_slug=sheet_slug,
            table_id=table_id,
            rows_loaded=total_rows,
            bytes_loaded=total_bytes,
        )

    # Truncate + reload the table per period. (For multi-period loads later
    # we'd switch to incremental MERGE on (source_product, source_period).)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )

    rows_loaded = 0
    for i, path in enumerate(parquet_paths):
        # First file truncates, subsequent files append
        if i > 0:
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.PARQUET,
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
            )
        with path.open("rb") as fh:
            job = client.load_table_from_file(
                fh,
                destination=table_id,
                job_config=job_config,
                location=LOCATION,
            )
        job.result()  # wait for completion; raises on failure
        rows_loaded += job.output_rows or 0

    return LoadResult(
        sheet_slug=sheet_slug,
        table_id=table_id,
        rows_loaded=rows_loaded,
        bytes_loaded=total_bytes,
    )


def load_period(period: str, dry_run: bool = False) -> list[LoadResult]:
    client = _client()
    # Sanity check: dataset exists
    try:
        client.get_dataset(f"{PROJECT_ID}.{DATASET_RAW}")
    except gax.NotFound as e:
        raise RuntimeError(
            f"Dataset {PROJECT_ID}.{DATASET_RAW} not found. "
            f"Run `uv run python scripts/bootstrap_bigquery.py` first."
        ) from e

    results: list[LoadResult] = []
    for sheet_name, (sheet_slug, _, _) in SHEET_REGISTRY.items():
        verb = "Validating" if dry_run else "Loading"
        print(f"{verb} sheet {sheet_name} → raw_dsa_{sheet_slug}")
        result = _load_sheet(client, sheet_slug, period, dry_run)
        marker = "(dry-run)" if dry_run else "loaded"
        print(
            f"  ✓ {result.table_id} — {result.rows_loaded} rows from "
            f"{result.bytes_loaded / 1024:.1f} KB across 4 product files {marker}"
        )
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", default="2025H2")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate Parquet inputs and check dataset access without loading.",
    )
    args = parser.parse_args(argv)
    results = load_period(args.period, dry_run=args.dry_run)

    print("\n" + "=" * 80)
    print(f"{'DRY-RUN' if args.dry_run else 'LOAD'} SUMMARY")
    print("=" * 80)
    total_rows = sum(r.rows_loaded for r in results)
    print(f"  {len(results)} tables in {PROJECT_ID}.{DATASET_RAW}")
    print(f"  {total_rows} total rows")
    if not args.dry_run:
        print(f"\n  Verify in BQ console:")
        print(
            f"  https://console.cloud.google.com/bigquery?project={PROJECT_ID}"
            f"&d={DATASET_RAW}&p={PROJECT_ID}&page=dataset"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
