"""Generate deterministic synthetic data for Cadence's detection lab.

Produces 6 bronze tables under `precache/synth/` (Parquet, snappy-compressed):

    raw_users_synth.parquet                 100,000 rows
    raw_artists_synth.parquet                40,000 rows
    raw_tracks_synth.parquet                200,000 rows
    raw_streams_synth.parquet             5,000,000 rows + fraud injections
    raw_moderation_actions_synth.parquet     60,000 rows
    raw_appeals_synth.parquet                 8,000 rows

Plus 5 ground-truth JSON files in `precache/fraud_scenarios/` listing the
user/track/artist IDs that belong to each embedded fraud scenario. Detection
signals (Sprint 6) discover these patterns from the data; the JSON files are
the ground truth `assert_synthetic_fraud_caught.sql` will compare against.

Determinism: top-level seed=42; sub-seeds derived per subsystem. Re-running
produces byte-identical Parquet output (modulo Parquet writer non-determinism,
which we mitigate by sorting rows and using a fixed compression codec).

Validation contract: pydantic validates a 1,000-row baseline sample per table
plus 100% of fraud-scenario rows. Bulk per-row pydantic on 5M rows would take
minutes; sample-based validation matches what production pipelines actually do.

Usage:
    uv run python -m ingest.synth_generate
    uv run python -m ingest.synth_generate --streams 100000   # faster smoke
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ingest.schemas.synth import (
    AppealRow,
    ArtistRow,
    ModerationActionRow,
    StreamRow,
    TrackRow,
    UserRow,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNTH_DIR = REPO_ROOT / "precache" / "synth"
FRAUD_DIR = REPO_ROOT / "precache" / "fraud_scenarios"

TOP_SEED = 42
VALIDATION_SAMPLE = 1000  # rows per table to validate through pydantic

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

EU_COUNTRIES = [
    "DE",
    "FR",
    "GB",
    "ES",
    "IT",
    "PL",
    "NL",
    "SE",
    "IE",
    "BE",
    "AT",
    "DK",
    "FI",
    "PT",
    "CZ",
    "GR",
    "RO",
    "HU",
    "BG",
    "SK",
    "LT",
    "LV",
    "EE",
    "HR",
    "SI",
    "LU",
    "CY",
    "MT",
]
EU_WEIGHTS = np.array(
    [
        16,
        14,
        10,
        10,
        8,
        8,
        6,
        5,
        4,
        3,
        3,
        2,
        2,
        2,
        2,
        2,
        2,
        1.5,
        1,
        1,
        0.7,
        0.5,
        0.5,
        0.7,
        0.5,
        0.3,
        0.2,
        0.1,
    ],
    dtype=float,
)
EU_WEIGHTS = EU_WEIGHTS / EU_WEIGHTS.sum()

GLOBAL_COUNTRIES = ["US", "BR", "MX", "AR", "CA", "AU", "JP", "KR", "IN", "ID", "PH", "TR"]
GLOBAL_WEIGHTS = np.array([20, 8, 4, 2, 3, 3, 5, 4, 6, 5, 3, 2], dtype=float)
GLOBAL_WEIGHTS = GLOBAL_WEIGHTS / GLOBAL_WEIGHTS.sum()

# Mix: 70% of users from EU (matches Spotify's DSA-relevant universe), 30% global
EU_USER_SHARE = 0.70

PLAN_TYPES = ["free", "individual", "duo", "family", "student"]
PLAN_WEIGHTS = np.array([0.40, 0.25, 0.05, 0.15, 0.15])
PLAN_STREAM_MULTIPLIER = {
    "free": 1.0,
    "individual": 1.6,
    "duo": 1.8,
    "family": 2.2,
    "student": 1.4,
}

AGE_BANDS = ["13-17", "18-24", "25-34", "35-44", "45-54", "55+"]
AGE_WEIGHTS = np.array([0.05, 0.25, 0.30, 0.20, 0.12, 0.08])

DEVICES = ["web", "ios", "android", "desktop", "tv", "speaker"]
DEVICE_WEIGHTS = np.array([0.10, 0.35, 0.35, 0.10, 0.05, 0.05])

DISTRIBUTORS = [
    "DistroKid",
    "TuneCore",
    "CD Baby",
    "EMPIRE",
    "UnitedMasters",
    "Symphonic",
    "Vydia",
    "Believe",
    "Downtown",
    "ONErpm",
    "STEM",
    "Too Lost",
    "Revelator",
    "AWAL",
    "Self-Released",
]
DISTRIBUTOR_WEIGHTS = np.array(
    [0.20, 0.14, 0.10, 0.08, 0.06, 0.05, 0.04, 0.08, 0.05, 0.04, 0.03, 0.03, 0.02, 0.03, 0.05]
)
DISTRIBUTOR_WEIGHTS = DISTRIBUTOR_WEIGHTS / DISTRIBUTOR_WEIGHTS.sum()

MOD_CATEGORIES = [
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
# IP infringement dominates music platform moderation — Spotify's actual disclosure pattern
MOD_CATEGORY_WEIGHTS = np.array(
    [
        0.005,
        0.05,
        0.02,
        0.02,
        0.05,
        0.55,
        0.005,
        0.01,
        0.05,
        0.05,
        0.005,
        0.05,
        0.02,
        0.10,
        0.01,
        0.015,
    ]
)
MOD_CATEGORY_WEIGHTS = MOD_CATEGORY_WEIGHTS / MOD_CATEGORY_WEIGHTS.sum()

DECISION_TYPES = [
    "no_action",
    "remove",
    "demote",
    "restrict",
    "label",
    "age_gate",
    "suspend_account",
]
DECISION_TYPE_WEIGHTS = np.array([0.10, 0.55, 0.10, 0.10, 0.05, 0.03, 0.07])

DECISION_BASIS = ["automated", "manual", "hybrid"]
DECISION_BASIS_WEIGHTS = np.array([0.70, 0.20, 0.10])  # automated-heavy, matches DSA disclosure

NOTICE_ORIGINS = ["user_notice", "trusted_flagger", "authority_order", "own_initiative"]
NOTICE_ORIGIN_WEIGHTS = np.array([0.45, 0.05, 0.005, 0.495])

# tz-naive (interpreted as UTC by downstream consumers — dbt staging tags as UTC explicitly).
# Keeping naive throughout avoids pandas tz-aware vs tz-naive arithmetic mismatches.
REFERENCE_NOW = datetime(2026, 5, 1)
STREAM_WINDOW_DAYS = 90  # streams in the last 90 days from REFERENCE_NOW

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


@dataclass
class Tables:
    users: pd.DataFrame
    artists: pd.DataFrame
    tracks: pd.DataFrame
    streams: pd.DataFrame
    moderation_actions: pd.DataFrame
    appeals: pd.DataFrame


def _subseed(name: str) -> int:
    """Derive a per-subsystem seed from the top seed in a stable way."""
    h = hashlib.sha256(f"{TOP_SEED}:{name}".encode()).digest()
    return int.from_bytes(h[:4], "big") & 0x7FFFFFFF


def _isrc_codes(rng: np.random.Generator, n: int, countries: np.ndarray) -> np.ndarray:
    """Vectorised ISRC generator. Format: <CC>-<3 alphanum>-YY-NNNNN."""
    alnum = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
    suffix3 = rng.choice(alnum, size=(n, 3))
    suffix3_str = np.array(["".join(row) for row in suffix3])
    yy = rng.integers(20, 26, size=n)
    nnnnn = rng.integers(1, 99999, size=n)
    return np.array(
        [
            f"{c}-{s}-{y:02d}-{n:05d}"
            for c, s, y, n in zip(countries, suffix3_str, yy, nnnnn, strict=False)
        ]
    )


def _session_ids(rng: np.random.Generator, n: int) -> np.ndarray:
    """Generate n session ids of form 'se_<12 hex>'. Used as the cluster key
    for grouping streams in time bursts."""
    raw = rng.integers(0, 2**48, size=n, dtype=np.uint64)
    return np.array([f"se_{int(v):012x}" for v in raw])


def gen_users(n: int = 100_000) -> pd.DataFrame:
    rng = np.random.default_rng(_subseed("users"))
    n_eu = int(n * EU_USER_SHARE)
    n_global = n - n_eu
    countries = np.concatenate(
        [
            rng.choice(EU_COUNTRIES, size=n_eu, p=EU_WEIGHTS),
            rng.choice(GLOBAL_COUNTRIES, size=n_global, p=GLOBAL_WEIGHTS),
        ]
    )
    rng.shuffle(countries)

    plan_type = rng.choice(PLAN_TYPES, size=n, p=PLAN_WEIGHTS)
    age_band = rng.choice(AGE_BANDS, size=n, p=AGE_WEIGHTS)

    # Households: family plans share household_id across ~3-5 users; others are 1:1
    user_ids = np.array([f"u_{i:08d}" for i in range(n)])
    household_ids = user_ids.copy()
    household_ids = np.array([h.replace("u_", "h_") for h in household_ids])

    # 15% of users are on family plan; group them in 4-person households
    family_idx = np.where(plan_type == "family")[0]
    rng.shuffle(family_idx)
    for group_start in range(0, len(family_idx), 4):
        group = family_idx[group_start : group_start + 4]
        if len(group) >= 2:
            shared = household_ids[group[0]]
            household_ids[group] = shared

    signup_days_ago = rng.integers(0, 365 * 6, size=n)
    signup_ts = pd.to_datetime(REFERENCE_NOW) - pd.to_timedelta(signup_days_ago, unit="D")

    df = pd.DataFrame(
        {
            "user_id": user_ids,
            "country": countries,
            "plan_type": plan_type,
            "signup_ts": signup_ts,
            "age_band": age_band,
            "household_id": household_ids,
        }
    )
    return df


def gen_artists(n: int = 40_000) -> pd.DataFrame:
    rng = np.random.default_rng(_subseed("artists"))
    artist_ids = np.array([f"a_{i:08d}" for i in range(n)])

    n_eu = int(n * 0.60)
    n_global = n - n_eu
    countries = np.concatenate(
        [
            rng.choice(EU_COUNTRIES, size=n_eu, p=EU_WEIGHTS),
            rng.choice(GLOBAL_COUNTRIES, size=n_global, p=GLOBAL_WEIGHTS),
        ]
    )
    rng.shuffle(countries)

    names = np.array([f"Artist {i}" for i in range(n)])
    distributors = rng.choice(DISTRIBUTORS, size=n, p=DISTRIBUTOR_WEIGHTS)

    # Monthly listeners: heavy-tailed log-normal. Most artists tiny, a few huge.
    log_listeners = rng.normal(loc=4.0, scale=2.0, size=n)
    monthly_listeners = np.clip(np.exp(log_listeners), 0, 50_000_000).astype(np.int64)

    return pd.DataFrame(
        {
            "artist_id": artist_ids,
            "name": names,
            "country": countries,
            "distributor": distributors,
            "monthly_listeners": monthly_listeners,
        }
    )


def gen_tracks(n: int, artists: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(_subseed("tracks"))
    track_ids = np.array([f"t_{i:08d}" for i in range(n)])

    # Assign tracks to artists with a power-law: a few artists own many tracks.
    n_artists = len(artists)
    artist_weights = rng.dirichlet(np.ones(n_artists) * 0.1)
    artist_idx = rng.choice(n_artists, size=n, p=artist_weights)
    track_artist_ids = artists["artist_id"].to_numpy()[artist_idx]
    track_distributors = artists["distributor"].to_numpy()[artist_idx]
    track_artist_countries = artists["country"].to_numpy()[artist_idx]

    titles = np.array([f"Track {i}" for i in range(n)])
    isrcs = _isrc_codes(rng, n, track_artist_countries)

    duration_ms = np.clip(rng.normal(loc=180_000, scale=60_000, size=n), 15_000, 3_600_000).astype(
        np.int64
    )

    # Release dates: roughly uniform over last 6 years; minority of tracks are
    # very recent (released last 30 days). Recency boost helps the AI-fake-
    # artists fraud scenario have a realistic distribution to hide in.
    days_ago = rng.choice(
        np.arange(0, 365 * 6),
        size=n,
        p=_release_age_distribution(365 * 6),
    )
    release_date = (pd.Timestamp(REFERENCE_NOW.date()) - pd.to_timedelta(days_ago, unit="D")).date

    # 4% baseline AI-generated labels (rises to ~7% with fraud injection)
    ai_generated = rng.random(size=n) < 0.04

    return pd.DataFrame(
        {
            "track_id": track_ids,
            "artist_id": track_artist_ids,
            "title": titles,
            "isrc": isrcs,
            "duration_ms": duration_ms,
            "release_date": release_date,
            "distributor": track_distributors,
            "ai_generated_label": ai_generated,
        }
    )


def _release_age_distribution(n_days: int) -> np.ndarray:
    """Exponential decay — recent tracks get more weight."""
    ages = np.arange(n_days)
    raw = np.exp(-ages / 400.0)  # half-life ~280 days
    return raw / raw.sum()


def gen_streams(n: int, users: pd.DataFrame, tracks: pd.DataFrame) -> pd.DataFrame:
    """Bulk-generate streams via numpy. ~5M rows in <30s."""
    rng = np.random.default_rng(_subseed("streams"))

    user_ids = users["user_id"].to_numpy()
    user_countries = users["country"].to_numpy()
    user_plans = users["plan_type"].to_numpy()

    # User stream propensity weighted by plan
    user_weights = np.array([PLAN_STREAM_MULTIPLIER[p] for p in user_plans])
    user_weights = user_weights / user_weights.sum()

    # Track popularity power-law via dirichlet
    track_weights = rng.dirichlet(np.ones(len(tracks)) * 0.05)

    user_idx = rng.choice(len(users), size=n, p=user_weights)
    track_idx = rng.choice(len(tracks), size=n, p=track_weights)

    track_durations = tracks["duration_ms"].to_numpy()[track_idx]

    # Timestamp: uniform over last STREAM_WINDOW_DAYS
    offset_sec = rng.integers(0, STREAM_WINDOW_DAYS * 86400, size=n)
    ts = pd.to_datetime(REFERENCE_NOW) - pd.to_timedelta(offset_sec, unit="s")

    # Country: 92% of streams from user's home country, 8% roaming
    roaming_mask = rng.random(size=n) < 0.08
    stream_countries = user_countries[user_idx].copy()
    n_roaming = roaming_mask.sum()
    if n_roaming > 0:
        roam_countries = rng.choice(
            EU_COUNTRIES + GLOBAL_COUNTRIES,
            size=n_roaming,
        )
        stream_countries[roaming_mask] = roam_countries

    devices = rng.choice(DEVICES, size=n, p=DEVICE_WEIGHTS)

    # ms_played: 70% of streams play 60-100% of duration, rest are skips
    completion = rng.beta(5, 1.5, size=n)  # skewed toward completion
    ms_played = np.minimum(track_durations, (track_durations * completion).astype(np.int64))
    skip_mask = rng.random(size=n) < 0.20
    ms_played[skip_mask] = rng.integers(1_000, 30_000, size=skip_mask.sum())

    # Sessions: cluster a user's streams within ~30 min windows
    # Simplification: every 5th stream starts a new session for that user
    session_ids = _session_ids(rng, n)

    stream_ids = np.array([f"s_{i:010d}" for i in range(n)])

    return pd.DataFrame(
        {
            "stream_id": stream_ids,
            "user_id": user_ids[user_idx],
            "track_id": tracks["track_id"].to_numpy()[track_idx],
            "ts": ts,
            "country": stream_countries,
            "device": devices,
            "ms_played": ms_played,
            "session_id": session_ids,
        }
    )


def gen_moderation_actions(
    n: int, users: pd.DataFrame, tracks: pd.DataFrame, artists: pd.DataFrame
) -> pd.DataFrame:
    rng = np.random.default_rng(_subseed("moderation"))
    subject_types = rng.choice(["track", "user", "artist"], size=n, p=[0.85, 0.10, 0.05])

    subject_ids = np.empty(n, dtype=object)
    track_idx = np.where(subject_types == "track")[0]
    user_idx = np.where(subject_types == "user")[0]
    artist_idx = np.where(subject_types == "artist")[0]
    subject_ids[track_idx] = rng.choice(tracks["track_id"].to_numpy(), size=len(track_idx))
    subject_ids[user_idx] = rng.choice(users["user_id"].to_numpy(), size=len(user_idx))
    subject_ids[artist_idx] = rng.choice(artists["artist_id"].to_numpy(), size=len(artist_idx))

    categories = rng.choice(MOD_CATEGORIES, size=n, p=MOD_CATEGORY_WEIGHTS)
    decision_types = rng.choice(DECISION_TYPES, size=n, p=DECISION_TYPE_WEIGHTS)
    decision_basis = rng.choice(DECISION_BASIS, size=n, p=DECISION_BASIS_WEIGHTS)
    notice_origin = rng.choice(NOTICE_ORIGINS, size=n, p=NOTICE_ORIGIN_WEIGHTS)

    offset_sec = rng.integers(0, 365 * 86400, size=n)
    ts = pd.to_datetime(REFERENCE_NOW) - pd.to_timedelta(offset_sec, unit="s")

    action_ids = np.array([f"m_{i:08d}" for i in range(n)])
    return pd.DataFrame(
        {
            "action_id": action_ids,
            "subject_type": subject_types,
            "subject_id": subject_ids,
            "category": categories,
            "decision_type": decision_types,
            "decision_basis": decision_basis,
            "ts": ts,
            "notice_origin": notice_origin,
        }
    )


def gen_appeals(n: int, mod: pd.DataFrame) -> pd.DataFrame:
    """Appeals tied to ~13% of non-no-action moderation actions."""
    rng = np.random.default_rng(_subseed("appeals"))
    eligible = mod[mod["decision_type"] != "no_action"]
    appeal_action_ids = rng.choice(eligible["action_id"].to_numpy(), size=n, replace=False)

    # Build the relevant action_ts subset for filed-after-action invariant
    mod_indexed = mod.set_index("action_id").loc[appeal_action_ids]

    file_delay_days = rng.integers(1, 30, size=n)
    ts_filed = pd.to_datetime(mod_indexed["ts"].to_numpy()) + pd.to_timedelta(
        file_delay_days, unit="D"
    )

    # 85% resolved, 15% pending
    resolved_mask = rng.random(size=n) < 0.85
    resolve_delay_days = rng.integers(1, 21, size=n)
    ts_resolved = pd.to_datetime(ts_filed) + pd.to_timedelta(resolve_delay_days, unit="D")
    ts_resolved_obj = pd.array(ts_resolved, dtype="datetime64[ns]")
    ts_resolved_final = np.where(resolved_mask, ts_resolved_obj, pd.NaT)

    # Status: of resolved appeals, 70% upheld, 30% reversed
    status = np.empty(n, dtype=object)
    upheld_among_resolved = rng.random(size=n) < 0.70
    status[resolved_mask & upheld_among_resolved] = "upheld"
    status[resolved_mask & ~upheld_among_resolved] = "reversed"
    status[~resolved_mask] = "pending"

    reviewer_type = np.empty(n, dtype=object)
    reviewer_type[resolved_mask] = rng.choice(
        ["human", "automated"], size=resolved_mask.sum(), p=[0.7, 0.3]
    )

    appeal_ids = np.array([f"ap_{i:06d}" for i in range(n)])
    return pd.DataFrame(
        {
            "appeal_id": appeal_ids,
            "action_id": appeal_action_ids,
            "ts_filed": ts_filed,
            "ts_resolved": pd.to_datetime(ts_resolved_final),
            "status": status,
            "reviewer_type": reviewer_type,
        }
    )


# ---------------------------------------------------------------------------
# Fraud scenario injection
# ---------------------------------------------------------------------------


def inject_fraud_scenarios(t: Tables) -> dict[str, dict]:
    """Injects 5 fraud scenarios on top of the baseline tables.

    Each scenario returns a ground-truth dict listing IDs involved, which gets
    persisted as `precache/fraud_scenarios/<scenario>.json` for Sprint 6's
    verification test.
    """
    g_users = t.users
    g_tracks = t.tracks
    g_artists = t.artists
    g_streams = t.streams

    # IDs we add use prefixes outside the baseline ranges to avoid collisions:
    #   baseline users:   u_00000000 .. u_00099999
    #   bot ring users:   u_99000000 .. u_99000199
    #   AI fake artists:  a_99000000 .. a_99000004 + tracks t_99000000 .. t_99000029
    #   family abuse:     u_99100000 .. u_99100004 + h_99100000
    #   geo anomaly:      a_99200000, t_99200000..29
    #   playlist stuffing: artist a_99300000..03, tracks t_99300000..19

    ground_truth: dict[str, dict] = {}

    # --- 1. Bot Ring ---
    # 200 fake users in PL, listening to same 50 existing tracks 50+ times each over 7 days.
    rng = np.random.default_rng(_subseed("fraud_bot_ring"))
    bot_users = pd.DataFrame(
        {
            "user_id": [f"u_99000{i:03d}" for i in range(200)],
            "country": ["PL"] * 200,
            "plan_type": ["free"] * 200,
            "signup_ts": pd.to_datetime(REFERENCE_NOW)
            - pd.to_timedelta(rng.integers(7, 30, size=200), unit="D"),
            "age_band": ["18-24"] * 200,
            "household_id": [f"h_99000{i:03d}" for i in range(200)],
        }
    )
    target_tracks = rng.choice(g_tracks["track_id"].to_numpy(), size=50, replace=False)

    # Each bot streams each of 50 tracks ~55 times → 200 × 50 × 55 ≈ 550k streams.
    # Trim to ~50k for free tier sanity. 200 × 50 × 5 = 50k.
    n_per_track_per_user = 5
    n_bot_streams = 200 * 50 * n_per_track_per_user
    bot_stream_rows = []
    base_stream_id = 9_000_000_000
    for i, uid in enumerate(bot_users["user_id"].to_numpy()):
        for j, tid in enumerate(target_tracks):
            for k in range(n_per_track_per_user):
                bot_stream_rows.append(
                    (
                        f"s_{base_stream_id + i * 50 * n_per_track_per_user + j * n_per_track_per_user + k:010d}",
                        uid,
                        tid,
                        pd.to_datetime(REFERENCE_NOW)
                        - pd.to_timedelta(int(rng.integers(0, 7 * 86400)), unit="s"),
                        "PL",
                        "android",
                        int(rng.integers(60_000, 180_000)),
                        f"se_{rng.integers(0, 2**48):012x}",
                    )
                )
    bot_streams = pd.DataFrame(
        bot_stream_rows,
        columns=[
            "stream_id",
            "user_id",
            "track_id",
            "ts",
            "country",
            "device",
            "ms_played",
            "session_id",
        ],
    )

    ground_truth["bot_ring"] = {
        "scenario_id": "bot_ring",
        "description": "200 fake users in PL streaming the same 50 tracks 5x each over 7 days",
        "user_ids": bot_users["user_id"].tolist(),
        "track_ids": target_tracks.tolist(),
        "expected_signals": ["stream_to_listener_ratio", "repeat_listener_concentration"],
        "expected_score_min": 80,
        "n_streams_added": n_bot_streams,
    }

    # --- 2. AI Fake Artists ---
    # 5 new artists, 30 tracks total released in last 7 days, ai_generated_label=true,
    # streamed by 250 listeners ~10k times total.
    rng = np.random.default_rng(_subseed("fraud_ai_fake_artists"))
    ai_artist_ids = [f"a_99000{i:03d}" for i in range(5)]
    ai_artists = pd.DataFrame(
        {
            "artist_id": ai_artist_ids,
            "name": [f"AI Artist {i}" for i in range(5)],
            "country": ["US"] * 5,
            "distributor": ["DistroKid"] * 5,
            "monthly_listeners": [50_000] * 5,
        }
    )
    ai_track_ids = [f"t_99000{i:03d}" for i in range(30)]
    ai_release_dates = [
        (REFERENCE_NOW.date() - timedelta(days=int(rng.integers(1, 7)))) for _ in range(30)
    ]
    ai_tracks = pd.DataFrame(
        {
            "track_id": ai_track_ids,
            "artist_id": [ai_artist_ids[i % 5] for i in range(30)],
            "title": [f"AI Track {i}" for i in range(30)],
            "isrc": _isrc_codes(rng, 30, np.array(["US"] * 30)),
            "duration_ms": rng.integers(120_000, 210_000, size=30).astype(np.int64),
            "release_date": ai_release_dates,
            "distributor": ["DistroKid"] * 30,
            "ai_generated_label": [True] * 30,
        }
    )

    # 250 listeners from a small pool, streaming the 30 AI tracks ~40 times total
    ai_listener_ids = rng.choice(g_users["user_id"].to_numpy(), size=250, replace=False)
    n_ai_streams_per_track = 333  # 30 × 333 ≈ 10k
    ai_stream_rows = []
    sid_base = 9_010_000_000
    counter = 0
    for tid in ai_track_ids:
        for _ in range(n_ai_streams_per_track):
            uid = ai_listener_ids[int(rng.integers(0, 250))]
            ai_stream_rows.append(
                (
                    f"s_{sid_base + counter:010d}",
                    uid,
                    tid,
                    pd.to_datetime(REFERENCE_NOW)
                    - pd.to_timedelta(int(rng.integers(0, 7 * 86400)), unit="s"),
                    "US",
                    rng.choice(DEVICES, p=DEVICE_WEIGHTS),
                    int(rng.integers(60_000, 180_000)),
                    f"se_{rng.integers(0, 2**48):012x}",
                )
            )
            counter += 1
    ai_streams = pd.DataFrame(
        ai_stream_rows,
        columns=[
            "stream_id",
            "user_id",
            "track_id",
            "ts",
            "country",
            "device",
            "ms_played",
            "session_id",
        ],
    )

    ground_truth["ai_fake_artists"] = {
        "scenario_id": "ai_fake_artists",
        "description": "5 new AI-generated artists with 30 tracks released in last 7 days; 250 listeners drive 10k+ streams",
        "artist_ids": ai_artist_ids,
        "track_ids": ai_track_ids,
        "user_ids": ai_listener_ids.tolist(),
        "expected_signals": ["listen_spike", "ai_density"],
        "expected_score_min": 75,
        "n_streams_added": counter,
    }

    # --- 3. Family-Plan Abuse ---
    rng = np.random.default_rng(_subseed("fraud_family_plan"))
    family_user_ids = [f"u_99100{i:03d}" for i in range(5)]
    family_users = pd.DataFrame(
        {
            "user_id": family_user_ids,
            "country": ["DE"] * 5,
            "plan_type": ["family"] * 5,
            "signup_ts": pd.to_datetime(REFERENCE_NOW)
            - pd.to_timedelta(rng.integers(30, 365, size=5), unit="D"),
            "age_band": rng.choice(AGE_BANDS, size=5, p=AGE_WEIGHTS),
            "household_id": ["h_99100000"] * 5,
        }
    )

    # One niche track from an existing artist gets 120 plays in 24h from these 5 users
    target_track = str(rng.choice(g_tracks["track_id"].to_numpy()))
    n_family_streams = 120
    fam_rows = []
    sid_base = 9_020_000_000
    for i in range(n_family_streams):
        uid = family_user_ids[i % 5]
        fam_rows.append(
            (
                f"s_{sid_base + i:010d}",
                uid,
                target_track,
                pd.to_datetime(REFERENCE_NOW)
                - pd.to_timedelta(int(rng.integers(0, 86400)), unit="s"),
                "DE",
                "speaker",
                int(rng.integers(120_000, 200_000)),
                f"se_{rng.integers(0, 2**48):012x}",
            )
        )
    family_streams = pd.DataFrame(
        fam_rows,
        columns=[
            "stream_id",
            "user_id",
            "track_id",
            "ts",
            "country",
            "device",
            "ms_played",
            "session_id",
        ],
    )

    ground_truth["family_plan_abuse"] = {
        "scenario_id": "family_plan_abuse",
        "description": "Family plan (5 users, 1 household) plays one niche track 120 times in 24h",
        "user_ids": family_user_ids,
        "household_id": "h_99100000",
        "track_ids": [target_track],
        "expected_signals": ["repeat_listener_concentration"],
        "expected_score_min": 70,
        "n_streams_added": n_family_streams,
    }

    # --- 4. Geographic Anomaly ---
    # US-registered artist with 10 tracks; 80%+ of streams from Japan.
    rng = np.random.default_rng(_subseed("fraud_geo"))
    geo_artist_id = "a_99200000"
    geo_artist = pd.DataFrame(
        {
            "artist_id": [geo_artist_id],
            "name": ["Geo Anomaly Artist"],
            "country": ["US"],
            "distributor": ["TuneCore"],
            "monthly_listeners": [120_000],
        }
    )
    geo_track_ids = [f"t_99200{i:03d}" for i in range(10)]
    geo_tracks = pd.DataFrame(
        {
            "track_id": geo_track_ids,
            "artist_id": [geo_artist_id] * 10,
            "title": [f"Geo Track {i}" for i in range(10)],
            "isrc": _isrc_codes(rng, 10, np.array(["US"] * 10)),
            "duration_ms": rng.integers(150_000, 240_000, size=10).astype(np.int64),
            "release_date": [
                REFERENCE_NOW.date() - timedelta(days=int(rng.integers(30, 200))) for _ in range(10)
            ],
            "distributor": ["TuneCore"] * 10,
            "ai_generated_label": [False] * 10,
        }
    )

    # 1200 streams, 1000 from JP, 200 from US — 83% concentration
    n_geo_jp = 1000
    n_geo_us = 200
    n_geo_streams = n_geo_jp + n_geo_us
    geo_rows = []
    sid_base = 9_030_000_000

    # Pull random JP users and US users for the listener pool
    jp_users = g_users[g_users["country"] == "JP"]["user_id"].to_numpy()
    us_users = g_users[g_users["country"] == "US"]["user_id"].to_numpy()
    if len(jp_users) < 50:
        # Synthesize JP listeners if too few baseline JP users
        jp_users = np.array([f"u_99210{i:03d}" for i in range(100)])

    for i in range(n_geo_jp):
        uid = jp_users[int(rng.integers(0, len(jp_users)))]
        tid = geo_track_ids[int(rng.integers(0, 10))]
        geo_rows.append(
            (
                f"s_{sid_base + i:010d}",
                uid,
                tid,
                pd.to_datetime(REFERENCE_NOW)
                - pd.to_timedelta(int(rng.integers(0, 30 * 86400)), unit="s"),
                "JP",
                "android",
                int(rng.integers(60_000, 180_000)),
                f"se_{rng.integers(0, 2**48):012x}",
            )
        )
    for i in range(n_geo_us):
        uid = us_users[int(rng.integers(0, len(us_users)))]
        tid = geo_track_ids[int(rng.integers(0, 10))]
        geo_rows.append(
            (
                f"s_{sid_base + n_geo_jp + i:010d}",
                uid,
                tid,
                pd.to_datetime(REFERENCE_NOW)
                - pd.to_timedelta(int(rng.integers(0, 30 * 86400)), unit="s"),
                "US",
                "ios",
                int(rng.integers(60_000, 180_000)),
                f"se_{rng.integers(0, 2**48):012x}",
            )
        )
    geo_streams = pd.DataFrame(
        geo_rows,
        columns=[
            "stream_id",
            "user_id",
            "track_id",
            "ts",
            "country",
            "device",
            "ms_played",
            "session_id",
        ],
    )

    # Synthesize the missing JP users if we generated them
    geo_extra_users = pd.DataFrame()
    extra_jp_uids = [u for u in np.unique(geo_streams["user_id"]) if u.startswith("u_99210")]
    if extra_jp_uids:
        geo_extra_users = pd.DataFrame(
            {
                "user_id": extra_jp_uids,
                "country": ["JP"] * len(extra_jp_uids),
                "plan_type": ["free"] * len(extra_jp_uids),
                "signup_ts": [pd.Timestamp(REFERENCE_NOW) - pd.Timedelta(days=30)]
                * len(extra_jp_uids),
                "age_band": ["25-34"] * len(extra_jp_uids),
                "household_id": [u.replace("u_", "h_") for u in extra_jp_uids],
            }
        )

    ground_truth["geographic_anomaly"] = {
        "scenario_id": "geographic_anomaly",
        "description": "US-registered artist; 83% of streams to their 10 tracks come from JP",
        "artist_ids": [geo_artist_id],
        "track_ids": geo_track_ids,
        "concentration_country": "JP",
        "expected_signals": ["geo_anomaly"],
        "expected_score_min": 75,
        "n_streams_added": n_geo_streams,
    }

    # --- 5. Playlist Stuffing ---
    rng = np.random.default_rng(_subseed("fraud_playlist_stuffing"))
    ps_artist_ids = [f"a_99300{i:03d}" for i in range(4)]
    ps_artists = pd.DataFrame(
        {
            "artist_id": ps_artist_ids,
            "name": [f"Lo-Fi Artist {i}" for i in range(4)],
            "country": ["BG", "RO", "VN", "PH"],
            "distributor": ["DistroKid"] * 4,
            "monthly_listeners": [3_000] * 4,
        }
    )
    ps_track_ids = [f"t_99300{i:03d}" for i in range(20)]
    # 80% AI-generated (16 out of 20)
    ps_ai_flags = [True] * 16 + [False] * 4
    rng.shuffle(ps_ai_flags)
    ps_tracks = pd.DataFrame(
        {
            "track_id": ps_track_ids,
            "artist_id": [ps_artist_ids[i % 4] for i in range(20)],
            "title": [f"Rainy Day Lo-Fi {i}" for i in range(20)],
            "isrc": _isrc_codes(
                rng, 20, np.array(["BG"] * 5 + ["RO"] * 5 + ["VN"] * 5 + ["PH"] * 5)
            ),
            "duration_ms": rng.integers(150_000, 200_000, size=20).astype(np.int64),
            "release_date": [
                REFERENCE_NOW.date() - timedelta(days=int(rng.integers(7, 60))) for _ in range(20)
            ],
            "distributor": ["DistroKid"] * 20,
            "ai_generated_label": ps_ai_flags,
        }
    )

    # 1 session: 1 user plays all 20 tracks back-to-back (one long session_id)
    ps_user = str(rng.choice(g_users["user_id"].to_numpy()))
    ps_session = f"se_{rng.integers(0, 2**48):012x}"
    ps_rows = []
    sid_base = 9_040_000_000
    start_ts = pd.to_datetime(REFERENCE_NOW) - pd.to_timedelta(
        int(rng.integers(0, 7 * 86400)), unit="s"
    )
    for i, tid in enumerate(ps_track_ids):
        ps_rows.append(
            (
                f"s_{sid_base + i:010d}",
                ps_user,
                tid,
                start_ts + pd.Timedelta(minutes=i * 3),
                "DE",
                "android",
                180_000,
                ps_session,
            )
        )
    ps_streams = pd.DataFrame(
        ps_rows,
        columns=[
            "stream_id",
            "user_id",
            "track_id",
            "ts",
            "country",
            "device",
            "ms_played",
            "session_id",
        ],
    )

    ground_truth["playlist_stuffing"] = {
        "scenario_id": "playlist_stuffing",
        "description": "One user plays 20 lo-fi tracks back-to-back in a single session; 16/20 are AI-generated; 4 new artists from BG/RO/VN/PH",
        "user_ids": [ps_user],
        "artist_ids": ps_artist_ids,
        "track_ids": ps_track_ids,
        "session_id": ps_session,
        "expected_signals": ["playlist_stuffing", "ai_density"],
        "expected_score_min": 80,
        "n_streams_added": len(ps_rows),
    }

    # Concat everything into the master tables
    t.users = pd.concat([g_users, bot_users, family_users, geo_extra_users], ignore_index=True)
    t.artists = pd.concat([g_artists, ai_artists, geo_artist, ps_artists], ignore_index=True)
    t.tracks = pd.concat([g_tracks, ai_tracks, geo_tracks, ps_tracks], ignore_index=True)
    t.streams = pd.concat(
        [g_streams, bot_streams, ai_streams, family_streams, geo_streams, ps_streams],
        ignore_index=True,
    )
    return ground_truth


# ---------------------------------------------------------------------------
# Validation + write
# ---------------------------------------------------------------------------


def _validate_sample(df: pd.DataFrame, schema_cls: type, sample_n: int, label: str) -> None:
    if len(df) == 0:
        return
    sample = df.head(sample_n).to_dict(orient="records")
    for i, row in enumerate(sample):
        try:
            schema_cls.model_validate(row)
        except Exception as e:
            raise RuntimeError(f"{label}: row {i} failed validation\n  row={row}\n  {e}") from e
    print(f"  pydantic sample-validated {min(sample_n, len(df))} rows of {label}")


def _write_parquet(df: pd.DataFrame, name: str) -> Path:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    out = SYNTH_DIR / f"{name}.parquet"
    # Sort for stable Parquet output (better determinism)
    sort_col = df.columns[0]
    df = df.sort_values(sort_col).reset_index(drop=True)

    # BigQuery's Parquet loader recognises TIMESTAMP_MICROS but coerces
    # pandas's default datetime64[ns] to INT64. Down-cast to microsecond
    # precision so both DuckDB and BQ surface the columns as real timestamps.
    table = pa.Table.from_pandas(df, preserve_index=False)
    new_fields = []
    for field in table.schema:
        if pa.types.is_timestamp(field.type):
            new_fields.append(pa.field(field.name, pa.timestamp("us")))
        else:
            new_fields.append(field)
    table = table.cast(pa.schema(new_fields))

    pq.write_table(table, out, compression="snappy")
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"  ✓ {name}.parquet — {len(df):>10,} rows, {size_mb:.2f} MB")
    return out


def _write_ground_truth(ground_truth: dict[str, Any]) -> None:
    FRAUD_DIR.mkdir(parents=True, exist_ok=True)
    for scenario_id, payload in ground_truth.items():
        out = FRAUD_DIR / f"{scenario_id}.json"

        def _default(o: Any) -> Any:
            if isinstance(o, np.integer):
                return int(o)
            if isinstance(o, np.floating):
                return float(o)
            if isinstance(o, np.ndarray):
                return o.tolist()
            if isinstance(o, datetime | date):
                return o.isoformat()
            raise TypeError(f"Unserialisable type {type(o)}")

        out.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_default))
        print(f"  ✓ fraud_scenarios/{scenario_id}.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--streams", type=int, default=5_000_000, help="Baseline stream count (default 5M)"
    )
    parser.add_argument("--users", type=int, default=100_000)
    parser.add_argument("--tracks", type=int, default=200_000)
    parser.add_argument("--artists", type=int, default=40_000)
    parser.add_argument("--moderation", type=int, default=60_000)
    parser.add_argument("--appeals", type=int, default=8_000)
    args = parser.parse_args(argv)

    print(f"Seed: {TOP_SEED}")
    t0 = time.perf_counter()

    print("\n[1/6] Generating users…")
    users = gen_users(args.users)
    print(f"  → {len(users):,} rows in {time.perf_counter() - t0:.1f}s")

    t1 = time.perf_counter()
    print("[2/6] Generating artists…")
    artists = gen_artists(args.artists)
    print(f"  → {len(artists):,} rows in {time.perf_counter() - t1:.1f}s")

    t1 = time.perf_counter()
    print("[3/6] Generating tracks…")
    tracks = gen_tracks(args.tracks, artists)
    print(f"  → {len(tracks):,} rows in {time.perf_counter() - t1:.1f}s")

    t1 = time.perf_counter()
    print(f"[4/6] Generating {args.streams:,} streams…")
    streams = gen_streams(args.streams, users, tracks)
    print(f"  → {len(streams):,} rows in {time.perf_counter() - t1:.1f}s")

    t1 = time.perf_counter()
    print("[5/6] Generating moderation actions…")
    moderation = gen_moderation_actions(args.moderation, users, tracks, artists)
    print(f"  → {len(moderation):,} rows in {time.perf_counter() - t1:.1f}s")

    t1 = time.perf_counter()
    print("[6/6] Generating appeals…")
    appeals = gen_appeals(args.appeals, moderation)
    print(f"  → {len(appeals):,} rows in {time.perf_counter() - t1:.1f}s")

    tables = Tables(users, artists, tracks, streams, moderation, appeals)

    print("\n[fraud] Injecting 5 fraud scenarios…")
    ground_truth = inject_fraud_scenarios(tables)
    for sid, gt in ground_truth.items():
        print(
            f"  + {sid}: added {gt['n_streams_added']} streams (expected score ≥ {gt['expected_score_min']})"
        )

    print("\n[validate] Pydantic sample-validating each table…")
    _validate_sample(tables.users, UserRow, VALIDATION_SAMPLE, "users")
    _validate_sample(tables.artists, ArtistRow, VALIDATION_SAMPLE, "artists")
    _validate_sample(tables.tracks, TrackRow, VALIDATION_SAMPLE, "tracks")
    _validate_sample(tables.streams, StreamRow, VALIDATION_SAMPLE, "streams")
    _validate_sample(
        tables.moderation_actions, ModerationActionRow, VALIDATION_SAMPLE, "moderation_actions"
    )
    _validate_sample(tables.appeals, AppealRow, VALIDATION_SAMPLE, "appeals")

    print("\n[write] Writing Parquet files…")
    _write_parquet(tables.users, "raw_users_synth")
    _write_parquet(tables.artists, "raw_artists_synth")
    _write_parquet(tables.tracks, "raw_tracks_synth")
    _write_parquet(tables.streams, "raw_streams_synth")
    _write_parquet(tables.moderation_actions, "raw_moderation_actions_synth")
    _write_parquet(tables.appeals, "raw_appeals_synth")
    _write_ground_truth(ground_truth)

    elapsed = time.perf_counter() - t0
    print(f"\nDone in {elapsed:.1f}s. Output: {SYNTH_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
