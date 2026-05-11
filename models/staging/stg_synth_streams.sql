{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('cadence_raw', 'raw_streams_synth') }}
)

SELECT
    {{ safe_text('stream_id') }}                       AS stream_id,
    {{ safe_text('user_id') }}                         AS user_id,
    {{ safe_text('track_id') }}                        AS track_id,
    {{ safe_timestamp('ts') }}                         AS streamed_at,
    {{ safe_text('country') }}                         AS stream_country_iso2,
    {{ safe_text('device') }}                          AS device,
    {{ safe_int('ms_played') }}                        AS ms_played,
    {{ safe_text('session_id') }}                      AS session_id
FROM source
