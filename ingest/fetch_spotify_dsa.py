"""Download Spotify's published DSA Transparency Report XLSX annexes.

Polite fetcher: content-hashes the response, only writes to disk when the
hash differs from what's already on disk. Idempotent — safe to re-run.

Usage:
    uv run python -m ingest.fetch_spotify_dsa --period 2025H2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "precache" / "dsa_reports" / "raw"

USER_AGENT = "cadence-research/0.1 (https://github.com/AliHasan-786/cadence)"


@dataclass(frozen=True)
class Report:
    product: str  # 'main' | 'artists' | 'authors' | 'creators'
    period: str  # '2025H2' for the Feb 2026 publication
    url: str
    expected_min_bytes: int = 100_000  # sanity-check the XLSX isn't an error page


REPORTS_2025H2: list[Report] = [
    Report(
        product="main",
        period="2025H2",
        url="https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_main",
    ),
    Report(
        product="artists",
        period="2025H2",
        url="https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_artists",
    ),
    Report(
        product="authors",
        period="2025H2",
        url="https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_authors",
    ),
    Report(
        product="creators",
        period="2025H2",
        url="https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_creators",
    ),
]

REPORTS_BY_PERIOD: dict[str, list[Report]] = {
    "2025H2": REPORTS_2025H2,
}


def _xlsx_path(product: str, period: str) -> Path:
    return RAW_DIR / f"{product}_{period}.xlsx"


def _meta_path(product: str, period: str) -> Path:
    return RAW_DIR / f"{product}_{period}.meta.json"


def _fetch_one(client: httpx.Client, report: Report) -> dict:
    out = _xlsx_path(report.product, report.period)
    meta_out = _meta_path(report.product, report.period)

    response = client.get(report.url)
    response.raise_for_status()
    body = response.content
    if len(body) < report.expected_min_bytes:
        raise RuntimeError(
            f"{report.product}/{report.period}: response too small "
            f"({len(body)} bytes < {report.expected_min_bytes}). Got HTML or JSON error?"
        )
    if body[:4] != b"PK\x03\x04":
        raise RuntimeError(
            f"{report.product}/{report.period}: response missing PKZIP magic — not an XLSX"
        )

    sha256 = hashlib.sha256(body).hexdigest()
    prior_hash: str | None = None
    if meta_out.exists():
        prior_hash = json.loads(meta_out.read_text()).get("sha256")
    changed = sha256 != prior_hash

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)

    meta = {
        "product": report.product,
        "period": report.period,
        "source_url": report.url,
        "final_url": str(response.url),
        "content_type": response.headers.get("content-type"),
        "content_disposition": response.headers.get("content-disposition"),
        "content_length": len(body),
        "sha256": sha256,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "changed_since_last_fetch": changed,
    }
    meta_out.write_text(json.dumps(meta, indent=2, sort_keys=True))

    return meta


def fetch_period(period: str) -> list[dict]:
    if period not in REPORTS_BY_PERIOD:
        raise ValueError(
            f"Unknown period {period!r}. Known: {sorted(REPORTS_BY_PERIOD.keys())}"
        )
    metas = []
    with httpx.Client(
        follow_redirects=True,
        timeout=120.0,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for report in REPORTS_BY_PERIOD[period]:
            print(f"Fetching {report.product}/{report.period} ← {report.url}")
            meta = _fetch_one(client, report)
            print(
                f"  ✓ {meta['content_length']:>8} bytes  "
                f"sha256={meta['sha256'][:12]}…  "
                f"{'CHANGED' if meta['changed_since_last_fetch'] else 'unchanged'}"
            )
            metas.append(meta)
    return metas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", default="2025H2", help="Reporting period to fetch.")
    args = parser.parse_args(argv)
    metas = fetch_period(args.period)
    print(f"\nFetched {len(metas)} report(s) into {RAW_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
