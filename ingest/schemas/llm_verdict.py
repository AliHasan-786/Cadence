"""Pydantic schema for LLM moderation verdicts.

One row per (scenario, provider, prompt_hash) — every API call we make,
plus every skip we record. Cached transcripts live in
precache/fraud_scenarios/llm_verdicts/<scenario>_<provider>.json; the
structured slice loads into BigQuery as `raw_llm_verdicts`.

The `error_class` discriminates between successful verdicts, skipped calls
(missing key), and real errors. dbt staging coerces the entire row through
the same path; rpt_llm_* models filter on `status` accordingly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Provider = Literal["anthropic", "openai", "google"]
Recommendation = Literal["recommend_no_action", "recommend_rank_lower", "recommend_remove"]
PrimarySignal = Literal[
    "listen_spike",
    "geo_anomaly",
    "stream_to_listener_ratio",
    "repeat_listener_concentration",
    "playlist_stuffing",
    "none",
]
ScenarioId = Literal[
    "bot_ring",
    "ai_fake_artists",
    "family_plan_abuse",
    "geographic_anomaly",
    "playlist_stuffing",
]
Status = Literal["ok", "skipped_no_key", "malformed_response", "api_error"]


class Verdict(BaseModel):
    """Either a successful LLM verdict OR a record that we tried and skipped."""

    model_config = ConfigDict(extra="forbid")

    # ─── Identity ──────────────────────────────────────────────────────────
    verdict_id: str = Field(pattern=r"^v_[a-f0-9]{16}$")
    scenario_id: ScenarioId
    track_id: str
    provider: Provider
    model: str

    # ─── Verdict body (NULL for non-OK rows) ──────────────────────────────
    recommendation: Recommendation | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    primary_signal: PrimarySignal | None = None
    reasoning: str | None = Field(default=None, max_length=1000)
    uncertainty_flags: list[str] = []

    # ─── Operational telemetry ────────────────────────────────────────────
    requested_at: datetime
    completed_at: datetime
    latency_ms: int = Field(ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)

    # ─── Provenance ───────────────────────────────────────────────────────
    prompt_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    response_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    status: Status = "ok"
    error_class: str | None = None

    @field_validator("recommendation", "primary_signal", "reasoning", "confidence")
    @classmethod
    def _verdict_fields_only_on_ok(cls, v, info):
        # We don't enforce this at the model level (skipped rows have NULLs);
        # the validator stays here as a documentation aid for the contract.
        return v
