"""Cadence Researcher API — DSA Article 40 in practice.

A FastAPI service exposing Spotify's published DSA Transparency Report data
through a programmatic, citation-aware API. Per PRD §11.

Architecture:
    - 9 endpoints (health, researcher_keys POST, dsa/cross_product,
      dsa/time_series, dsa/member_state, dsa/categories, schema,
      citations/{query_id}, audit/my_queries)
    - Rate limit: 100 req / 15 min per key (BigQuery-backed bucket count)
    - Audit log: every request → cadence_raw.raw_researcher_queries
    - Citation contract: every response carries dbt_model + manifest_commit_hash
      + data_refreshed_at + source_reports[] + suggested_bibtex

Single-file FastAPI app to keep Vercel function size under 50 MB.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from google.cloud import bigquery
from google.oauth2 import service_account
from pydantic import BaseModel, EmailStr, Field

# ─── Config ─────────────────────────────────────────────────────────────────

PROJECT_ID = "spry-smithy-489221-p4"
DATASET = "cadence"
DATASET_MARTS_TRANSPARENCY = "cadence_marts_transparency"
DATASET_MARTS_RESEARCHER = "cadence_marts_researcher"
RAW_DATASET = "cadence_raw"
LOCATION = "US"

RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW_MIN = 15

MANIFEST_COMMIT_HASH = os.environ.get("CADENCE_COMMIT_SHA", "unknown")

# DSA source URLs (PRD §15) — included in every response's citation block
SOURCE_REPORTS_2025 = [
    "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_main",
    "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_artists",
    "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_authors",
    "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_creators",
]

CADENCE_LICENSE = (
    "Underlying Spotify DSA report data is published by Spotify under its "
    "site terms; Cadence transformations are CC-BY-4.0."
)

# ─── BigQuery client (lazy) ─────────────────────────────────────────────────

_bq_client: bigquery.Client | None = None


def get_bq() -> bigquery.Client:
    """Return a singleton BQ client. Vercel-side auth via base64-encoded SA JSON env var."""
    global _bq_client
    if _bq_client is not None:
        return _bq_client

    key_json_b64 = os.environ.get("GCP_SA_KEY_JSON_B64")
    if key_json_b64:
        info = json.loads(base64.b64decode(key_json_b64))
        creds = service_account.Credentials.from_service_account_info(info)
    else:
        # Local fallback
        keyfile = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not keyfile:
            raise RuntimeError(
                "No GCP credentials — set GCP_SA_KEY_JSON_B64 (Vercel) "
                "or GOOGLE_APPLICATION_CREDENTIALS (local)."
            )
        creds = service_account.Credentials.from_service_account_file(keyfile)

    _bq_client = bigquery.Client(project=PROJECT_ID, credentials=creds, location=LOCATION)
    return _bq_client


# ─── FastAPI app ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Cadence Researcher API",
    description=(
        "DSA Article 40-style researcher access to Spotify's published "
        "Transparency Report data. Every response carries a citation block "
        "with the dbt model, manifest commit hash, source reports, and a "
        "suggested BibTeX entry — peer-review-ready provenance.\n\n"
        "**Authentication.** Most endpoints require a researcher key. "
        "POST `/researcher_keys` to issue one (free, instant). "
        "Then pass it as `Authorization: Bearer rk_<key>` on subsequent "
        "requests.\n\n"
        "**Rate limit.** 100 requests per 15 minutes per key. "
        "Exceeded → HTTP 429.\n\n"
        "**Audit.** Every request is logged to BigQuery with a SHA-256 "
        "of the client IP (never the raw IP). The `/audit/my_queries` "
        "endpoint returns the caller's own audit trail."
    ),
    version="1.0.0",
    contact={"name": "Ali Hasan", "url": "https://github.com/AliHasan-786/Cadence"},
    license_info={"name": "CC-BY-4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
)


# ─── Citation block ─────────────────────────────────────────────────────────


class Citation(BaseModel):
    dataset: str = f"{PROJECT_ID}.{DATASET}"
    dbt_model: str
    manifest_commit_hash: str = MANIFEST_COMMIT_HASH
    data_refreshed_at: str
    source_reports: list[str] = SOURCE_REPORTS_2025
    license: str = CADENCE_LICENSE
    suggested_bibtex: str


def _bibtex_for(dbt_model: str, period: str) -> str:
    return (
        f"@misc{{cadence_{period}_{dbt_model}, "
        f"author={{Cadence}}, "
        f"title={{Spotify DSA Transparency Data via Cadence ({dbt_model})}}, "
        f"year={{2026}}, "
        f"howpublished={{\\url{{https://github.com/AliHasan-786/Cadence}}}}}}"
    )


def make_citation(dbt_model: str, period: str = "annual_2025") -> Citation:
    return Citation(
        dbt_model=dbt_model,
        data_refreshed_at=datetime.now(UTC).isoformat(),
        suggested_bibtex=_bibtex_for(dbt_model, period),
    )


# ─── Authentication + rate limiting + audit ─────────────────────────────────


def _hash_ip(ip: str) -> str:
    return "sha256:" + hashlib.sha256(ip.encode()).hexdigest()[:16]


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return fwd or (request.client.host if request.client else "unknown")


async def require_key(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Validate the researcher key + apply rate limit + audit-log the request."""
    if not authorization or not authorization.startswith("Bearer rk_"):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Missing or malformed Authorization header. Use 'Bearer rk_<key>'.",
        )
    key = authorization.removeprefix("Bearer ").strip()

    bq = get_bq()

    # Existence check
    rows = list(
        bq.query(
            f"SELECT key_id, researcher_name, institution, status "
            f"FROM `{PROJECT_ID}.{RAW_DATASET}.raw_researcher_keys` "
            f"WHERE key_id = @key LIMIT 1",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("key", "STRING", key)]
            ),
        ).result()
    )
    if not rows:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid researcher key.")
    row = rows[0]
    if row.status not in (None, "active"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Key status: {row.status}")

    # Rate limit: count recent requests for this key
    window_start = datetime.now(UTC) - timedelta(minutes=RATE_LIMIT_WINDOW_MIN)
    count_rows = list(
        bq.query(
            f"SELECT COUNT(*) AS n "
            f"FROM `{PROJECT_ID}.{RAW_DATASET}.raw_researcher_queries` "
            f"WHERE key_id = @key AND requested_at >= @since",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("key", "STRING", key),
                    bigquery.ScalarQueryParameter("since", "TIMESTAMP", window_start),
                ]
            ),
        ).result()
    )
    n_recent = int(count_rows[0].n) if count_rows else 0
    if n_recent >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Rate limit exceeded ({RATE_LIMIT_REQUESTS} requests / "
            f"{RATE_LIMIT_WINDOW_MIN} min). Try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_MIN * 60)},
        )

    return {
        "key_id": row.key_id,
        "researcher_name": row.researcher_name,
        "institution": row.institution,
        "request_started_at": time.perf_counter(),
        "client_ip_hash": _hash_ip(_client_ip(request)),
    }


def audit_log(
    key_ctx: dict,
    endpoint: str,
    query_params: dict,
    response_size_bytes: int,
    response_status_code: int,
) -> None:
    """Streaming-insert one audit row. Best-effort: failures don't break the response."""
    try:
        bq = get_bq()
        latency_ms = int((time.perf_counter() - key_ctx["request_started_at"]) * 1000)
        row = {
            "query_id": "q_" + uuid.uuid4().hex[:16],
            "key_id": key_ctx["key_id"],
            "endpoint": endpoint,
            "query_params_json": json.dumps(query_params, default=str),
            "response_size_bytes": response_size_bytes,
            "response_status_code": response_status_code,
            "latency_ms": latency_ms,
            "requested_at": datetime.now(UTC).isoformat(),
            "client_ip_hash": key_ctx["client_ip_hash"],
        }
        bq.insert_rows_json(f"{PROJECT_ID}.{RAW_DATASET}.raw_researcher_queries", [row])
    except Exception as e:  # pragma: no cover — best-effort
        print(f"audit_log_failed: {e}")  # surfaces in Vercel logs


# ─── Response envelopes ─────────────────────────────────────────────────────


class CrossProductRow(BaseModel):
    product_line: str
    reporting_period_canonical: str
    notices_received: int | None = None
    items_in_notices: int | None = None
    total_decisions: int | None = None
    automated_decisions: int | None = None
    automated_share_pct: float | None = None
    median_time_to_take_action_hours: float | None = None
    complaints_submitted: int | None = None
    automated_accuracy_pct: float | None = None
    automated_precision_pct: float | None = None
    automated_recall_pct: float | None = None


class CrossProductResponse(BaseModel):
    data: list[dict]
    citation: Citation


# ─── Routes ─────────────────────────────────────────────────────────────────


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "commit": MANIFEST_COMMIT_HASH}


class KeyRequest(BaseModel):
    researcher_name: str = Field(min_length=1, max_length=200)
    institution: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=10, max_length=500)
    email: EmailStr


class KeyResponse(BaseModel):
    key_id: str
    issued_at: str
    rate_limit: str
    note: str


@app.post("/researcher_keys", response_model=KeyResponse, tags=["researcher"])
async def issue_key(body: KeyRequest):
    """Issue a researcher API key. Free, instant. V1 returns the key inline;
    V1.1 will deliver via email."""
    key_id = "rk_" + uuid.uuid4().hex[:24]
    email_hash = "sha256:" + hashlib.sha256(body.email.encode()).hexdigest()[:16]
    bq = get_bq()
    bq.insert_rows_json(
        f"{PROJECT_ID}.{RAW_DATASET}.raw_researcher_keys",
        [
            {
                "key_id": key_id,
                "researcher_name": body.researcher_name,
                "institution": body.institution,
                "purpose": body.purpose,
                "email_hash": email_hash,
                "created_at": datetime.now(UTC).isoformat(),
                "status": "active",
            }
        ],
    )
    return KeyResponse(
        key_id=key_id,
        issued_at=datetime.now(UTC).isoformat(),
        rate_limit=f"{RATE_LIMIT_REQUESTS} requests / {RATE_LIMIT_WINDOW_MIN} min",
        note="V1 returns the key inline. Save it — there's no recovery flow. V1.1 will add email delivery.",
    )


@app.get("/dsa/cross_product", tags=["dsa"])
async def dsa_cross_product(
    request: Request,
    product_line: str | None = None,
    key_ctx: dict = Depends(require_key),
):
    bq = get_bq()
    where = ""
    params: list[Any] = []
    if product_line:
        where = "WHERE product_line = @product_line"
        params.append(bigquery.ScalarQueryParameter("product_line", "STRING", product_line))
    rows = list(
        bq.query(
            f"SELECT * FROM `{PROJECT_ID}.{DATASET_MARTS_TRANSPARENCY}.rpt_cross_product_summary` "
            f"{where} ORDER BY product_line",
            job_config=bigquery.QueryJobConfig(query_parameters=params),
        ).result()
    )
    data = [dict(r.items()) for r in rows]
    payload = {"data": data, "citation": make_citation("rpt_cross_product_summary").model_dump()}
    audit_log(
        key_ctx,
        "/dsa/cross_product",
        {"product_line": product_line},
        len(json.dumps(payload, default=str)),
        200,
    )
    return JSONResponse(content=json.loads(json.dumps(payload, default=str)))


@app.get("/dsa/time_series", tags=["dsa"])
async def dsa_time_series(
    request: Request,
    metric: str = "total_decisions",
    product_line: str | None = None,
    key_ctx: dict = Depends(require_key),
):
    allowed = {
        "total_decisions",
        "automated_decisions",
        "automated_share_pct",
        "notices_received",
        "complaints_submitted",
    }
    if metric not in allowed:
        raise HTTPException(400, f"metric must be one of {sorted(allowed)}")
    bq = get_bq()
    where = ""
    params: list[Any] = []
    if product_line:
        where = "WHERE product_line = @product_line"
        params.append(bigquery.ScalarQueryParameter("product_line", "STRING", product_line))
    rows = list(
        bq.query(
            f"SELECT product_line, reporting_period_canonical, reporting_period_start, "
            f"reporting_period_end, period_seq, n_periods_available, {metric} AS value "
            f"FROM `{PROJECT_ID}.{DATASET_MARTS_TRANSPARENCY}.rpt_quarter_over_quarter_trends` "
            f"{where} ORDER BY product_line, period_seq",
            job_config=bigquery.QueryJobConfig(query_parameters=params),
        ).result()
    )
    data = [dict(r.items()) for r in rows]
    payload = {
        "metric": metric,
        "data": data,
        "citation": make_citation("rpt_quarter_over_quarter_trends").model_dump(),
    }
    audit_log(
        key_ctx,
        "/dsa/time_series",
        {"metric": metric, "product_line": product_line},
        len(json.dumps(payload, default=str)),
        200,
    )
    return JSONResponse(content=json.loads(json.dumps(payload, default=str)))


@app.get("/dsa/member_state", tags=["dsa"])
async def dsa_member_state(
    request: Request,
    product_line: str | None = None,
    key_ctx: dict = Depends(require_key),
):
    bq = get_bq()
    where = ""
    params: list[Any] = []
    if product_line:
        where = "WHERE product_line = @product_line"
        params.append(bigquery.ScalarQueryParameter("product_line", "STRING", product_line))
    rows = list(
        bq.query(
            f"SELECT * FROM `{PROJECT_ID}.{DATASET_MARTS_TRANSPARENCY}.rpt_member_state_breakdown` "
            f"{where} ORDER BY product_line, member_state_id",
            job_config=bigquery.QueryJobConfig(query_parameters=params),
        ).result()
    )
    data = [dict(r.items()) for r in rows]
    payload = {
        "data": data,
        "note": (
            "Spotify's 2025 DSA reports disclose only EU-AGGREGATE rather than "
            "per-Member-State granularity. Cadence shows the gap honestly rather "
            "than fabricating distribution."
        ),
        "citation": make_citation("rpt_member_state_breakdown").model_dump(),
    }
    audit_log(
        key_ctx,
        "/dsa/member_state",
        {"product_line": product_line},
        len(json.dumps(payload, default=str)),
        200,
    )
    return JSONResponse(content=json.loads(json.dumps(payload, default=str)))


@app.get("/dsa/categories", tags=["dsa"])
async def dsa_categories(request: Request, key_ctx: dict = Depends(require_key)):
    bq = get_bq()
    rows = list(
        bq.query(
            f"SELECT category_label, category_description, category_code, category_level "
            f"FROM `{PROJECT_ID}.{DATASET_MARTS_TRANSPARENCY}.dim_dsa_categories` "
            f"ORDER BY category_label"
        ).result()
    )
    data = [dict(r.items()) for r in rows]
    payload = {"data": data, "citation": make_citation("dim_dsa_categories").model_dump()}
    audit_log(
        key_ctx,
        "/dsa/categories",
        {},
        len(json.dumps(payload, default=str)),
        200,
    )
    return JSONResponse(content=json.loads(json.dumps(payload, default=str)))


@app.get("/schema", tags=["meta"])
async def schema(request: Request, key_ctx: dict = Depends(require_key)):
    """Return the full schema documentation for the marts the API exposes."""
    bq = get_bq()
    tables = [
        "rpt_cross_product_summary",
        "rpt_quarter_over_quarter_trends",
        "rpt_member_state_breakdown",
        "dim_dsa_categories",
    ]
    schemas = {}
    for t in tables:
        tbl = bq.get_table(f"{PROJECT_ID}.{DATASET_MARTS_TRANSPARENCY}.{t}")
        schemas[t] = [
            {"name": f.name, "type": f.field_type, "mode": f.mode, "description": f.description}
            for f in tbl.schema
        ]
    payload = {
        "tables": schemas,
        "citation": make_citation("rpt_cross_product_summary").model_dump(),
    }
    audit_log(
        key_ctx,
        "/schema",
        {},
        len(json.dumps(payload, default=str)),
        200,
    )
    return JSONResponse(content=json.loads(json.dumps(payload, default=str)))


@app.get("/citations/{query_id}", tags=["meta"])
async def get_citation(query_id: str, request: Request, key_ctx: dict = Depends(require_key)):
    """Return the citation metadata for a previously-audited query."""
    bq = get_bq()
    rows = list(
        bq.query(
            f"SELECT endpoint, requested_at FROM "
            f"`{PROJECT_ID}.{DATASET_MARTS_RESEARCHER}.fct_researcher_queries` "
            f"WHERE query_id = @qid AND key_id = @kid LIMIT 1",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("qid", "STRING", query_id),
                    bigquery.ScalarQueryParameter("kid", "STRING", key_ctx["key_id"]),
                ]
            ),
        ).result()
    )
    if not rows:
        raise HTTPException(404, "Query not found in audit log (or not yours).")
    row = rows[0]
    # Derive the dbt_model from the endpoint
    endpoint_to_model = {
        "/dsa/cross_product": "rpt_cross_product_summary",
        "/dsa/time_series": "rpt_quarter_over_quarter_trends",
        "/dsa/member_state": "rpt_member_state_breakdown",
        "/dsa/categories": "dim_dsa_categories",
    }
    payload = {
        "query_id": query_id,
        "endpoint": row.endpoint,
        "queried_at": row.requested_at.isoformat() if row.requested_at else None,
        "citation": make_citation(endpoint_to_model.get(row.endpoint, "unknown")).model_dump(),
    }
    audit_log(
        key_ctx,
        "/citations/{query_id}",
        {"query_id": query_id},
        len(json.dumps(payload, default=str)),
        200,
    )
    return JSONResponse(content=json.loads(json.dumps(payload, default=str)))


@app.get("/audit/my_queries", tags=["audit"])
async def audit_my_queries(request: Request, limit: int = 50, key_ctx: dict = Depends(require_key)):
    """Return the caller's own query history (BigQuery streaming insert visibility
    delay applies — recent calls may take up to ~90s to appear)."""
    if limit > 500:
        limit = 500
    bq = get_bq()
    rows = list(
        bq.query(
            f"SELECT query_id, endpoint, requested_at, response_status_code, latency_ms "
            f"FROM `{PROJECT_ID}.{RAW_DATASET}.raw_researcher_queries` "
            f"WHERE key_id = @kid ORDER BY requested_at DESC LIMIT @lim",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("kid", "STRING", key_ctx["key_id"]),
                    bigquery.ScalarQueryParameter("lim", "INT64", limit),
                ]
            ),
        ).result()
    )
    data = [dict(r.items()) for r in rows]
    payload = {
        "key_id": key_ctx["key_id"],
        "researcher_name": key_ctx["researcher_name"],
        "data": data,
        "citation": make_citation("raw_researcher_queries").model_dump(),
        "note": "Best-effort — BQ streaming insert visibility delay can be up to ~90s.",
    }
    audit_log(
        key_ctx,
        "/audit/my_queries",
        {"limit": limit},
        len(json.dumps(payload, default=str)),
        200,
    )
    return JSONResponse(content=json.loads(json.dumps(payload, default=str)))


# Vercel entry point — exports `app` as the ASGI handler.
