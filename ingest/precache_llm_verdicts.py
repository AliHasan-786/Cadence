"""Pre-cache LLM moderation verdicts for each of the 5 fraud scenarios.

For each scenario × provider (Anthropic / OpenAI / Google) we:
    1. Render a SHARED moderation prompt with that scenario's evidence
       (same input string sent verbatim to all 3 providers — reviewability)
    2. Compute prompt_hash and check the per-(scenario, provider) cache
       under precache/fraud_scenarios/llm_verdicts/. Hit → use cached.
    3. Miss → call the provider's SDK. If the API key isn't in env, persist
       a skip stub with status='skipped_no_key' (don't fail, don't fabricate)
    4. Validate the response against the Verdict pydantic schema
    5. Persist verbatim transcript JSON + structured row.

After the loop, all rows are written to precache/synth/raw_llm_verdicts.parquet
ready for `ingest.load_llm_verdicts_to_bigquery`.

Budget gate: aborts if the running total exceeds $10. The expected total for
all 15 calls is well under $0.10 with mid-tier models.

Usage:
    source ~/.config/cadence-llm-keys.env  # or export keys directly
    uv run python -m ingest.precache_llm_verdicts
    uv run python -m ingest.precache_llm_verdicts --force        # bypass cache
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from ingest.schemas.llm_verdict import Verdict

REPO_ROOT = Path(__file__).resolve().parent.parent
FRAUD_DIR = REPO_ROOT / "precache" / "fraud_scenarios"
VERDICTS_DIR = FRAUD_DIR / "llm_verdicts"
OUT_PARQUET = REPO_ROOT / "precache" / "synth" / "raw_llm_verdicts.parquet"

BUDGET_USD = 10.0
MAX_RETRIES = 2  # per-call retry cap

# Models + per-MTok pricing (USD). Mid-tier picks across providers — meaningful
# but cheap. Pricing tables are from each provider's public pricing as of 2026.
PROVIDERS: dict[str, dict[str, Any]] = {
    "anthropic": {
        "model": "claude-sonnet-4-6",
        "price_input_per_mtok": 3.00,
        "price_output_per_mtok": 15.00,
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "model": "gpt-4o-2024-08-06",
        "price_input_per_mtok": 2.50,
        "price_output_per_mtok": 10.00,
        "env_key": "OPENAI_API_KEY",
    },
    "google": {
        # gemini-2.5-pro is paid-tier-only; the free-tier API key we have access
        # to runs gemini-2.5-flash. Pricing reflects flash's published rates.
        "model": "gemini-2.5-flash",
        "price_input_per_mtok": 0.30,
        "price_output_per_mtok": 2.50,
        "env_key": "GOOGLE_API_KEY",
    },
}


# ============================================================================
# Shared prompt — rendered ONCE per scenario, sent verbatim to all 3 providers
# ============================================================================

PROMPT_TEMPLATE = """You are a content-moderation reviewer for Spotify's Trust & Safety analytics team.
Your job is to recommend an action for a TRACK that has been flagged for
potential artificial streaming by Spotify's automated detection signals.

Below is the evidence Spotify's heuristic system produced. You may disagree
with the heuristic — but your verdict is what gets queued for human review.

== EVIDENCE ==

Track ID:         {track_id}
Artist country:   {artist_country}
Track AI label:   {ai_generated_label}
Release date:     {release_date}
Total streams (90d): {total_streams}
Top stream country:  {top_country} ({top_country_share_pct}% of streams)

Detection signals:
  listen_spike                  fires={ls_fires}  severity={ls_sev:.2f}  spike_ratio={ls_ratio:.1f}x
  geo_anomaly                   fires={ga_fires}  severity={ga_sev:.2f}  top_country_share={ga_share:.2f}
  stream_to_listener_ratio      fires={s2l_fires} severity={s2l_sev:.2f} ratio={s2l_ratio:.2f}
  repeat_listener_concentration fires={rlc_fires} severity={rlc_sev:.2f} hhi={rlc_hhi:.3f}
  playlist_stuffing             fires={ps_fires}  severity={ps_sev:.2f}  session_ai_share={ps_share}

Heuristic composite suspicion score (0-100): {composite_score:.1f}
Heuristic recommendation: {heuristic_action}

== TASK ==

Output ONLY a single JSON object (no prose, no markdown fences) matching
this exact schema:

{{
  "recommendation":   "recommend_no_action" | "recommend_rank_lower" | "recommend_remove",
  "confidence":       <float 0.0-1.0>,
  "primary_signal":   "listen_spike" | "geo_anomaly" | "stream_to_listener_ratio" | "repeat_listener_concentration" | "playlist_stuffing" | "none",
  "reasoning":        "<your reasoning in ≤300 chars>",
  "uncertainty_flags":["<flag1>", "<flag2>", ...]
}}

Consider: signals can fire from legitimate behavior (viral hit, niche fanbase,
regional release). Your job is to assess whether THIS specific evidence
warrants action, given the magnitudes and context.
"""


def render_prompt(scenario_evidence: dict[str, Any]) -> str:
    return PROMPT_TEMPLATE.format(**scenario_evidence)


# ============================================================================
# Evidence collector — pulls one representative track + signal evidence per scenario
# ============================================================================


def gather_scenario_evidence(scenario_id: str) -> dict[str, Any]:
    """Pull the highest-scored track from each fraud scenario + its signal evidence,
    by querying BigQuery's cadence_ci_marts_safety dataset."""
    from google.cloud import bigquery
    from google.oauth2 import service_account

    keyfile = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not keyfile or not Path(keyfile).expanduser().exists():
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS not set or missing; "
            "set it before running pre-cache."
        )
    creds = service_account.Credentials.from_service_account_file(
        str(Path(keyfile).expanduser())
    )
    bq = bigquery.Client(
        project="spry-smithy-489221-p4", credentials=creds, location="US"
    )

    # Pick the representative track: highest composite score in this scenario
    repr_q = f"""
    SELECT f.track_id, f.composite_suspicion_score, f.recommended_action,
           f.listen_spike_fires, f.listen_spike_severity,
           f.geo_anomaly_fires, f.geo_anomaly_severity,
           f.s2l_ratio_fires, f.s2l_ratio_severity,
           f.repeat_listener_fires, f.repeat_listener_severity,
           f.playlist_stuffing_fires, f.playlist_stuffing_severity,
           t.ai_generated_label, t.release_date, a.country_iso2 AS artist_country
    FROM `spry-smithy-489221-p4.cadence_ci_marts_safety.fct_artificial_streaming_flags` f
    JOIN `spry-smithy-489221-p4.cadence_ci_seeds.fraud_scenario_expectations` e
         ON e.track_id = f.track_id AND e.scenario_id = '{scenario_id}'
    JOIN `spry-smithy-489221-p4.cadence_ci_staging.stg_synth_tracks` t
         ON t.track_id = f.track_id
    LEFT JOIN `spry-smithy-489221-p4.cadence_ci_staging.stg_synth_artists` a
         ON a.artist_id = t.artist_id
    ORDER BY f.composite_suspicion_score DESC
    LIMIT 1
    """
    repr_row = next(iter(bq.query(repr_q).result()))

    # Per-signal supporting context (top_country_share, ratio, hhi, ai_share)
    sigs_q = f"""
    SELECT
        ls.spike_ratio, ga.top_country, ga.top_country_share,
        s2l.streams_per_listener AS s2l_ratio_value, rlc.hhi_value, ps.session_ai_share,
        ls.recent_streams + ls.baseline_streams AS total_streams
    FROM `spry-smithy-489221-p4.cadence_ci_marts_safety.sig_listen_spike` ls
    LEFT JOIN `spry-smithy-489221-p4.cadence_ci_marts_safety.sig_geo_anomaly` ga
         ON ga.track_id = ls.track_id
    LEFT JOIN `spry-smithy-489221-p4.cadence_ci_marts_safety.sig_stream_to_listener_ratio` s2l
         ON s2l.track_id = ls.track_id
    LEFT JOIN `spry-smithy-489221-p4.cadence_ci_marts_safety.sig_repeat_listener_concentration` rlc
         ON rlc.track_id = ls.track_id
    LEFT JOIN `spry-smithy-489221-p4.cadence_ci_marts_safety.sig_playlist_stuffing` ps
         ON ps.track_id = ls.track_id
    WHERE ls.track_id = '{repr_row.track_id}'
    """
    rows = list(bq.query(sigs_q).result())
    sig = rows[0] if rows else None

    return {
        "scenario_id": scenario_id,
        "track_id": repr_row.track_id,
        "artist_country": repr_row.artist_country or "unknown",
        "ai_generated_label": str(repr_row.ai_generated_label),
        "release_date": str(repr_row.release_date),
        "total_streams": int(sig.total_streams) if sig and sig.total_streams else 0,
        "top_country": (sig.top_country if sig and sig.top_country else "unknown"),
        "top_country_share_pct": (
            f"{100 * sig.top_country_share:.1f}" if sig and sig.top_country_share else "n/a"
        ),
        "ls_fires": repr_row.listen_spike_fires,
        "ls_sev": float(repr_row.listen_spike_severity or 0),
        "ls_ratio": float(sig.spike_ratio) if sig and sig.spike_ratio else 0.0,
        "ga_fires": repr_row.geo_anomaly_fires,
        "ga_sev": float(repr_row.geo_anomaly_severity or 0),
        "ga_share": float(sig.top_country_share) if sig and sig.top_country_share else 0.0,
        "s2l_fires": repr_row.s2l_ratio_fires,
        "s2l_sev": float(repr_row.s2l_ratio_severity or 0),
        "s2l_ratio": float(sig.s2l_ratio_value) if sig and sig.s2l_ratio_value else 0.0,
        "rlc_fires": repr_row.repeat_listener_fires,
        "rlc_sev": float(repr_row.repeat_listener_severity or 0),
        "rlc_hhi": float(sig.hhi_value) if sig and sig.hhi_value else 0.0,
        "ps_fires": repr_row.playlist_stuffing_fires,
        "ps_sev": float(repr_row.playlist_stuffing_severity or 0),
        "ps_share": (
            f"{sig.session_ai_share:.2f}" if sig and sig.session_ai_share else "n/a"
        ),
        "composite_score": float(repr_row.composite_suspicion_score or 0),
        "heuristic_action": repr_row.recommended_action,
    }


# ============================================================================
# Provider callers (each returns a Verdict)
# ============================================================================


def _verdict_id(prompt_hash: str, provider: str) -> str:
    return "v_" + hashlib.sha256(f"{provider}:{prompt_hash}".encode()).hexdigest()[:16]


def _new_skip(
    scenario_id: str, track_id: str, provider: str, prompt_hash: str, reason: str
) -> Verdict:
    now = datetime.now(timezone.utc)
    return Verdict(
        verdict_id=_verdict_id(prompt_hash, provider),
        scenario_id=scenario_id,
        track_id=track_id,
        provider=provider,
        model=PROVIDERS[provider]["model"],
        requested_at=now,
        completed_at=now,
        latency_ms=0,
        prompt_hash=prompt_hash,
        status="skipped_no_key",
        error_class=reason,
    )


def _parse_verdict_json(raw: str) -> dict[str, Any]:
    """Tolerant JSON parse — strips markdown fences if a provider wraps."""
    s = raw.strip()
    if s.startswith("```"):
        # remove ```json or ``` prefix and trailing ```
        s = s.split("```", 2)[1] if "```" in s[3:] else s[3:]
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    return json.loads(s)


def call_anthropic(prompt: str, model: str) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic()
    t0 = time.perf_counter()
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = "".join(b.text for b in resp.content if b.type == "text")
    return {
        "text": text,
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "latency_ms": latency_ms,
    }


def call_openai(prompt: str, model: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        response_format={"type": "json_object"},
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = resp.choices[0].message.content or ""
    return {
        "text": text,
        "input_tokens": resp.usage.prompt_tokens,
        "output_tokens": resp.usage.completion_tokens,
        "latency_ms": latency_ms,
    }


def call_google(prompt: str, model: str) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    t0 = time.perf_counter()
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=2048,  # larger buffer than 512 — free-tier flash truncates short replies
            temperature=0.2,
        ),
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = resp.text or ""
    usage = getattr(resp, "usage_metadata", None)
    return {
        "text": text,
        "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
        "latency_ms": latency_ms,
    }


CALLERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "google": call_google,
}


# ============================================================================
# Main loop
# ============================================================================


def cost_of(provider: str, input_tokens: int, output_tokens: int) -> float:
    p = PROVIDERS[provider]
    return (
        input_tokens * p["price_input_per_mtok"] / 1_000_000
        + output_tokens * p["price_output_per_mtok"] / 1_000_000
    )


def _transcript_path(scenario_id: str, provider: str) -> Path:
    return VERDICTS_DIR / f"{scenario_id}_{provider}.json"


def _persist_transcript(
    scenario_id: str,
    provider: str,
    prompt: str,
    prompt_hash: str,
    response_text: str | None,
    verdict: Verdict,
) -> None:
    VERDICTS_DIR.mkdir(parents=True, exist_ok=True)
    out = _transcript_path(scenario_id, provider)
    payload = {
        "scenario_id": scenario_id,
        "provider": provider,
        "model": verdict.model,
        "prompt": prompt,
        "prompt_hash": prompt_hash,
        "response_text": response_text,
        "verdict": verdict.model_dump(mode="json"),
    }
    out.write_text(json.dumps(payload, indent=2, default=str))


def _load_cached_verdict(scenario_id: str, provider: str, prompt_hash: str) -> Verdict | None:
    p = _transcript_path(scenario_id, provider)
    if not p.exists():
        return None
    payload = json.loads(p.read_text())
    if payload.get("prompt_hash") != prompt_hash:
        return None  # prompt changed → re-call
    try:
        return Verdict.model_validate(payload["verdict"])
    except Exception:
        return None


def make_verdict(
    *,
    scenario_id: str,
    track_id: str,
    provider: str,
    prompt: str,
    prompt_hash: str,
    cumulative_cost: float,
) -> Verdict:
    spec = PROVIDERS[provider]
    if not os.environ.get(spec["env_key"]):
        print(f"  [{provider:9s}] SKIP — {spec['env_key']} not set")
        return _new_skip(scenario_id, track_id, provider, prompt_hash, "skipped_no_key")

    if cumulative_cost >= BUDGET_USD:
        print(f"  [{provider:9s}] SKIP — budget cap reached (${cumulative_cost:.4f}/{BUDGET_USD})")
        return _new_skip(scenario_id, track_id, provider, prompt_hash, "budget_cap")

    caller = CALLERS[provider]
    last_err: str | None = None
    for attempt in range(MAX_RETRIES + 1):
        t_req = datetime.now(timezone.utc)
        try:
            result = caller(prompt, spec["model"])
        except Exception as e:  # API error
            last_err = f"{type(e).__name__}: {e}"
            print(f"  [{provider:9s}] api_error (attempt {attempt + 1}): {last_err[:120]}")
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            t_done = datetime.now(timezone.utc)
            return Verdict(
                verdict_id=_verdict_id(prompt_hash, provider),
                scenario_id=scenario_id,
                track_id=track_id,
                provider=provider,
                model=spec["model"],
                requested_at=t_req,
                completed_at=t_done,
                latency_ms=0,
                prompt_hash=prompt_hash,
                status="api_error",
                error_class=last_err[:200],
            )

        # Parse + validate the response
        try:
            parsed = _parse_verdict_json(result["text"])
        except Exception as e:
            last_err = f"json_parse: {e}"
            print(f"  [{provider:9s}] malformed (attempt {attempt + 1}): {last_err[:120]}")
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            t_done = datetime.now(timezone.utc)
            return Verdict(
                verdict_id=_verdict_id(prompt_hash, provider),
                scenario_id=scenario_id,
                track_id=track_id,
                provider=provider,
                model=spec["model"],
                requested_at=t_req,
                completed_at=t_done,
                latency_ms=result.get("latency_ms", 0),
                input_tokens=result.get("input_tokens", 0),
                output_tokens=result.get("output_tokens", 0),
                cost_usd=cost_of(provider, result.get("input_tokens", 0), result.get("output_tokens", 0)),
                prompt_hash=prompt_hash,
                response_hash=hashlib.sha256(result["text"].encode()).hexdigest(),
                status="malformed_response",
                error_class=last_err[:200],
            )

        t_done = datetime.now(timezone.utc)
        cost = cost_of(provider, result["input_tokens"], result["output_tokens"])
        try:
            return Verdict(
                verdict_id=_verdict_id(prompt_hash, provider),
                scenario_id=scenario_id,
                track_id=track_id,
                provider=provider,
                model=spec["model"],
                recommendation=parsed.get("recommendation"),
                confidence=parsed.get("confidence"),
                primary_signal=parsed.get("primary_signal"),
                reasoning=(parsed.get("reasoning") or "")[:1000],
                uncertainty_flags=parsed.get("uncertainty_flags") or [],
                requested_at=t_req,
                completed_at=t_done,
                latency_ms=result["latency_ms"],
                input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"],
                cost_usd=cost,
                prompt_hash=prompt_hash,
                response_hash=hashlib.sha256(result["text"].encode()).hexdigest(),
                status="ok",
            )
        except ValidationError as e:
            # Pydantic enum/range failed — treat as malformed
            last_err = f"pydantic: {e}"
            print(f"  [{provider:9s}] malformed (pydantic): {last_err[:120]}")
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            return Verdict(
                verdict_id=_verdict_id(prompt_hash, provider),
                scenario_id=scenario_id,
                track_id=track_id,
                provider=provider,
                model=spec["model"],
                requested_at=t_req,
                completed_at=t_done,
                latency_ms=result["latency_ms"],
                input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"],
                cost_usd=cost,
                prompt_hash=prompt_hash,
                response_hash=hashlib.sha256(result["text"].encode()).hexdigest(),
                status="malformed_response",
                error_class=last_err[:200],
            )

    # Shouldn't reach here
    raise RuntimeError("unreachable")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Bypass cache, call every provider.")
    args = parser.parse_args(argv)

    scenarios = ["bot_ring", "ai_fake_artists", "family_plan_abuse", "geographic_anomaly", "playlist_stuffing"]

    print(f"Budget cap: ${BUDGET_USD}")
    print(f"Providers configured: {list(PROVIDERS.keys())}")
    print(f"Cache directory: {VERDICTS_DIR}\n")

    all_verdicts: list[dict] = []
    all_prompts: list[tuple[str, str]] = []  # (scenario_id, prompt) for output
    cumulative_cost = 0.0

    for scenario_id in scenarios:
        print(f"=== {scenario_id} ===")
        ev = gather_scenario_evidence(scenario_id)
        prompt = render_prompt(ev)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        all_prompts.append((scenario_id, prompt))
        print(f"  representative track: {ev['track_id']}  prompt_hash={prompt_hash[:12]}...  "
              f"prompt_len={len(prompt)} chars")

        for provider in PROVIDERS:
            cached = None if args.force else _load_cached_verdict(scenario_id, provider, prompt_hash)
            if cached and cached.status == "ok":
                print(f"  [{provider:9s}] CACHED  rec={cached.recommendation}  "
                      f"latency={cached.latency_ms}ms  cost=${cached.cost_usd:.4f}")
                v = cached
            else:
                v = make_verdict(
                    scenario_id=scenario_id,
                    track_id=ev["track_id"],
                    provider=provider,
                    prompt=prompt,
                    prompt_hash=prompt_hash,
                    cumulative_cost=cumulative_cost,
                )
                if v.status == "ok":
                    print(f"  [{provider:9s}] OK      rec={v.recommendation}  "
                          f"conf={v.confidence:.2f}  latency={v.latency_ms}ms  cost=${v.cost_usd:.4f}")
                cumulative_cost += v.cost_usd
                response_text = None
                # Re-load the just-called response if we have it
                _persist_transcript(scenario_id, provider, prompt, prompt_hash,
                                    response_text=None, verdict=v)

            all_verdicts.append(v.model_dump(mode="json"))

    # Write Parquet for BQ load
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_verdicts)
    # Coerce timestamps to microseconds for BQ TIMESTAMP recognition
    for col in ("requested_at", "completed_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True).dt.tz_localize(None)
    # uncertainty_flags is a list; serialise to JSON string for Parquet→BQ
    if "uncertainty_flags" in df.columns:
        df["uncertainty_flags"] = df["uncertainty_flags"].apply(json.dumps)
    table = pa.Table.from_pandas(df, preserve_index=False)
    new_fields = []
    for field in table.schema:
        if pa.types.is_timestamp(field.type):
            new_fields.append(pa.field(field.name, pa.timestamp("us")))
        else:
            new_fields.append(field)
    table = table.cast(pa.schema(new_fields))
    pq.write_table(table, OUT_PARQUET, compression="snappy")

    n_ok = sum(1 for v in all_verdicts if v["status"] == "ok")
    n_skip = sum(1 for v in all_verdicts if v["status"].startswith("skipped"))
    n_err = sum(1 for v in all_verdicts if v["status"] in {"api_error", "malformed_response"})

    print("\n" + "=" * 80)
    print("PRE-CACHE SUMMARY")
    print("=" * 80)
    print(f"  {len(all_verdicts)} verdict rows ({n_ok} ok, {n_skip} skipped, {n_err} errored)")
    print(f"  Total API spend: ${cumulative_cost:.4f} (budget ${BUDGET_USD})")
    print(f"  Parquet: {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
