"""Create the BigQuery datasets Cadence depends on.

Idempotent. Run once after the service-account key is in place
(see scripts/bootstrap_bigquery.md).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from google.api_core import exceptions as gax
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "spry-smithy-489221-p4"
LOCATION = "US"
DATASETS = [
    ("cadence_raw", "Raw bronze tables — direct loads from ingest pipeline."),
    ("cadence", "Production dataset — dbt-built staging, intermediate, marts."),
    ("cadence_ci", "CI dataset — isolated dbt build target for PRs."),
    ("cadence_audit", "Audit dataset — write-audit-publish staging."),
]


def _client(keyfile: Path | None) -> bigquery.Client:
    if keyfile and keyfile.exists():
        creds = service_account.Credentials.from_service_account_file(
            str(keyfile),
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)
    # Falls back to GOOGLE_APPLICATION_CREDENTIALS or ADC.
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def _ensure_dataset(client: bigquery.Client, dataset_id: str, description: str) -> None:
    ref = bigquery.DatasetReference(PROJECT_ID, dataset_id)
    try:
        existing = client.get_dataset(ref)
        if existing.location != LOCATION:
            raise RuntimeError(
                f"Dataset {dataset_id} exists in location {existing.location!r}; "
                f"expected {LOCATION!r}."
            )
        print(f"  - {dataset_id}: already exists (location={existing.location})")
        return
    except gax.NotFound:
        pass

    ds = bigquery.Dataset(ref)
    ds.location = LOCATION
    ds.description = description
    client.create_dataset(ds)
    print(f"  - {dataset_id}: created (location={LOCATION})")


def cmd_create(client: bigquery.Client) -> None:
    print(f"Project: {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print("Datasets:")
    for dataset_id, description in DATASETS:
        _ensure_dataset(client, dataset_id, description)


def cmd_verify(client: bigquery.Client) -> int:
    print(f"Project: {client.project}")
    sa_email = "unknown"
    keyfile_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if keyfile_env and Path(keyfile_env).exists():
        import json

        with open(keyfile_env) as fh:
            sa_email = json.load(fh).get("client_email", "unknown")
    print(f"Auth identity: {sa_email}")

    present = []
    for dataset_id, _ in DATASETS:
        try:
            client.get_dataset(f"{PROJECT_ID}.{dataset_id}")
            present.append(dataset_id)
        except gax.NotFound:
            print(f"  ! missing: {dataset_id}")
            return 1

    print(f"Datasets present: {', '.join(present)} (location={LOCATION})")
    # Round-trip a trivial query so we know the credentials actually run jobs.
    row = next(iter(client.query("SELECT 1 AS ok").result()))
    if row.ok != 1:  # pragma: no cover
        print("Round-trip query failed.")
        return 1
    print("BQ connection OK.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify mode: don't create, just check datasets exist and credentials run jobs.",
    )
    parser.add_argument(
        "--keyfile",
        type=Path,
        default=None,
        help="Path to service-account JSON. Defaults to GOOGLE_APPLICATION_CREDENTIALS.",
    )
    args = parser.parse_args(argv)

    keyfile = args.keyfile
    if keyfile is None:
        env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if env:
            keyfile = Path(env)
    if keyfile is None or not keyfile.exists():
        print(
            "ERROR: no service-account key found.\n"
            "Set GOOGLE_APPLICATION_CREDENTIALS or pass --keyfile.\n"
            "See scripts/bootstrap_bigquery.md.",
            file=sys.stderr,
        )
        return 2

    client = _client(keyfile)
    if args.verify:
        return cmd_verify(client)
    cmd_create(client)
    return cmd_verify(client)


if __name__ == "__main__":
    sys.exit(main())
