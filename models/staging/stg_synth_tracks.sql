{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_tracks_synth') }}
)

SELECT
    {{ safe_text('track_id') }}                        AS track_id,
    {{ safe_text('artist_id') }}                       AS artist_id,
    {{ safe_text('title') }}                           AS title,
    {{ safe_text('isrc') }}                            AS isrc,
    {{ safe_int('duration_ms') }}                      AS duration_ms,
    {{ safe_text('release_date') }}                    AS release_date,
    {{ safe_text('distributor') }}                     AS distributor,
    {{ safe_bool('ai_generated_label') }}              AS ai_generated_label
FROM source
