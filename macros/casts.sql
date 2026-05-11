-- Cross-dialect safe-cast helpers.
--
-- Bronze layer is permissive (`str | int | float | None`) to preserve source
-- fidelity. Staging coerces to canonical types using BigQuery's SAFE_CAST and
-- DuckDB's TRY_CAST under one macro name so staging SQL stays identical
-- across both targets.
--
-- dbt.safe_cast() + dbt.type_*() handle the dialect translation; these
-- wrappers exist so model SQL reads naturally as `{{ safe_int('col') }}`.

{% macro safe_int(col) %}
    {{ dbt.safe_cast(col, dbt.type_int()) }}
{% endmacro %}

{% macro safe_float(col) %}
    {{ dbt.safe_cast(col, dbt.type_float()) }}
{% endmacro %}

{% macro safe_text(col) %}
    {{ dbt.safe_cast(col, dbt.type_string()) }}
{% endmacro %}

{% macro safe_bool(col) %}
    {{ dbt.safe_cast(col, dbt.type_boolean()) }}
{% endmacro %}

{% macro safe_timestamp(col) %}
    {{ dbt.safe_cast(col, dbt.type_timestamp()) }}
{% endmacro %}

-- safe_date — DATE-typed cast. dbt's built-in type_*() doesn't include 'date',
-- so we branch in the macro (per the agreed contract: dialect divergence
-- lives here, not in individual models). BigQuery: SAFE_CAST; DuckDB: TRY_CAST.
{% macro safe_date(col) %}
    {% if target.type == 'bigquery' %}
        SAFE_CAST({{ col }} AS DATE)
    {% else %}
        TRY_CAST({{ col }} AS DATE)
    {% endif %}
{% endmacro %}

-- Standardise the period dimension. Spotify's 2025 reports are calendar-year
-- annual under the EU harmonised template — not "H2" despite the PRD's early
-- labelling. Hardcoded for now; will become a CASE statement once 2024 (PDF)
-- backfill lands.
{% macro reporting_period_canonical() %}
    'annual_2025'
{% endmacro %}

{% macro reporting_period_start() %}
    {{ safe_date("'2025-01-01'") }}
{% endmacro %}

{% macro reporting_period_end() %}
    {{ safe_date("'2025-12-31'") }}
{% endmacro %}
