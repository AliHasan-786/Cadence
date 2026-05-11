{{ config(materialized='table') }}

-- Canonical fact table for LLM moderation verdicts.
-- Grain: one row per (scenario, provider, prompt_hash).
-- Joined to heuristic context so dashboards can answer "does Cadence's
-- heuristic agree with the LLM consensus?" without re-joining.

SELECT * FROM {{ ref('int_llm_verdict_aggregates') }}
