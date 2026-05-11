"""Pydantic schemas for synthetic Cadence data.

All six bronze synthetic tables. Schemas are kept permissive (Bronze = source
fidelity); strict typing happens in dbt staging.

These are validation contracts — bulk generation goes through numpy/pandas
for throughput (5M streams in Python loops would be slow). The schemas
validate a sample of rows + all fraud-scenario rows before each Parquet write
to catch generator bugs early. See `ingest/synth_generate.py:VALIDATION_SAMPLE`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Reference enums — kept aligned with what dbt staging will canonicalise
# ---------------------------------------------------------------------------

PlanType = Literal["free", "individual", "duo", "family", "student"]
AgeBand = Literal["13-17", "18-24", "25-34", "35-44", "45-54", "55+"]
Device = Literal["web", "ios", "android", "desktop", "tv", "speaker"]
ModerationCategory = Literal[
    "ANIMAL_WELFARE",
    "CONSUMER_INFORMATION",
    "CYBER_VIOLENCE",
    "DATA_PROTECTION",
    "ILLEGAL_OR_HARMFUL_SPEECH",
    "INTELLECTUAL_PROPERTY_INFRINGEMENTS",
    "NEGATIVE_EFFECTS_CIVIC_DISCOURSE",
    "NON_CONSENSUAL_BEHAVIOUR",
    "PORNOGRAPHY",
    "PROTECTION_OF_MINORS",
    "RISK_FOR_PUBLIC_SECURITY",
    "SCAMS_AND_FRAUD",
    "SELF_HARM",
    "SCOPE_OF_PLATFORM_SERVICE",
    "UNSAFE_OR_PROHIBITED_PRODUCTS",
    "VIOLENCE",
]
DecisionBasis = Literal["automated", "manual", "hybrid"]
DecisionType = Literal[
    "no_action", "remove", "demote", "restrict", "label", "age_gate", "suspend_account"
]
AppealStatus = Literal["upheld", "reversed", "pending"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserRow(_Base):
    user_id: str = Field(pattern=r"^u_\d{8}$")
    country: str = Field(min_length=2, max_length=2)
    plan_type: PlanType
    signup_ts: datetime
    age_band: AgeBand
    household_id: str = Field(pattern=r"^h_\d{8}$")


class ArtistRow(_Base):
    artist_id: str = Field(pattern=r"^a_\d{8}$")
    name: str
    country: str = Field(min_length=2, max_length=2)
    distributor: str
    monthly_listeners: int = Field(ge=0)


class TrackRow(_Base):
    track_id: str = Field(pattern=r"^t_\d{8}$")
    artist_id: str = Field(pattern=r"^a_\d{8}$")
    title: str
    isrc: str = Field(pattern=r"^[A-Z]{2}-[A-Z0-9]{3}-\d{2}-\d{5}$")
    duration_ms: int = Field(ge=15000, le=3_600_000)  # 15s to 60min
    release_date: date
    distributor: str
    ai_generated_label: bool


class StreamRow(_Base):
    stream_id: str = Field(pattern=r"^s_\d{10}$")
    user_id: str = Field(pattern=r"^u_\d{8}$")
    track_id: str = Field(pattern=r"^t_\d{8}$")
    ts: datetime
    country: str = Field(min_length=2, max_length=2)
    device: Device
    ms_played: int = Field(ge=0)
    session_id: str = Field(pattern=r"^se_[a-f0-9]{12}$")


class ModerationActionRow(_Base):
    action_id: str = Field(pattern=r"^m_\d{8}$")
    subject_type: Literal["track", "user", "artist"]
    subject_id: str
    category: ModerationCategory
    decision_type: DecisionType
    decision_basis: DecisionBasis
    ts: datetime
    notice_origin: Literal["user_notice", "trusted_flagger", "authority_order", "own_initiative"]


class AppealRow(_Base):
    appeal_id: str = Field(pattern=r"^ap_\d{6}$")
    action_id: str = Field(pattern=r"^m_\d{8}$")
    ts_filed: datetime
    ts_resolved: datetime | None
    status: AppealStatus
    reviewer_type: Literal["human", "automated"] | None


__all__ = [
    "AgeBand",
    "AppealRow",
    "AppealStatus",
    "ArtistRow",
    "DecisionBasis",
    "DecisionType",
    "Device",
    "ModerationActionRow",
    "ModerationCategory",
    "PlanType",
    "StreamRow",
    "TrackRow",
    "UserRow",
]
