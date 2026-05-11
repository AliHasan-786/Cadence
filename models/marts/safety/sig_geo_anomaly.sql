{{ config(materialized='view') }}

-- Signal 2: geo_anomaly
-- Fires when one country accounts for ≥80% of a track's streams AND that
-- country is NOT the artist's home country. Catches geo-concentrated bot
-- traffic and unexpected market-shift fraud (US-registered artist with
-- 80%+ streams from JP).

{% set ga = var('safety_metrics').thresholds.geo_anomaly %}
{% set cap = var('safety_metrics').severity_cap %}

WITH track_artist AS (
    SELECT t.track_id, a.country_iso2 AS artist_country
    FROM {{ ref('stg_synth_tracks') }} t
    LEFT JOIN {{ ref('stg_synth_artists') }} a USING (artist_id)
),

per_track_country AS (
    SELECT
        s.track_id,
        s.stream_country_iso2 AS country,
        COUNT(*) AS streams
    FROM {{ ref('stg_synth_streams') }} s
    GROUP BY s.track_id, s.stream_country_iso2
),

top_country AS (
    SELECT
        track_id,
        country AS top_country,
        streams AS top_country_streams,
        ROW_NUMBER() OVER (PARTITION BY track_id ORDER BY streams DESC) AS rk
    FROM per_track_country
),

totals AS (
    SELECT
        track_id,
        SUM(streams) AS total_streams,
        COUNT(*)     AS n_distinct_countries
    FROM per_track_country
    GROUP BY track_id
),

joined AS (
    SELECT
        tc.track_id,
        ta.artist_country,
        tc.top_country,
        tc.top_country_streams,
        tt.total_streams,
        tt.n_distinct_countries,
        CAST(tc.top_country_streams AS {{ dbt.type_float() }})
            / NULLIF(tt.total_streams, 0)                              AS top_country_share
    FROM top_country tc
    JOIN totals tt   USING (track_id)
    JOIN track_artist ta USING (track_id)
    WHERE tc.rk = 1
)

SELECT
    track_id,
    CAST('track' AS {{ dbt.type_string() }})                           AS entity_kind,
    artist_country,
    top_country,
    top_country_streams,
    total_streams,
    n_distinct_countries,
    top_country_share,
    CASE
        WHEN top_country_share >= {{ ga.single_country_share }}
         AND total_streams >= {{ ga.min_streams }}
         AND top_country <> artist_country
        THEN 1 ELSE 0
    END                                                                AS fires,
    LEAST(
        {{ cap }},
        (top_country_share - 0.50) / 0.20
    )                                                                  AS severity
FROM joined
