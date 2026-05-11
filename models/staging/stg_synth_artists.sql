{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_artists_synth') }}
)

SELECT
    {{ safe_text('artist_id') }}                       AS artist_id,
    {{ safe_text('name') }}                            AS name,
    {{ safe_text('country') }}                         AS country_iso2,
    {{ safe_text('distributor') }}                     AS distributor,
    {{ safe_int('monthly_listeners') }}                AS monthly_listeners
FROM source
