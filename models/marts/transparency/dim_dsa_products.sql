{{ config(materialized='table') }}

-- The four Spotify product lines named in §2.1 of the PRD. Each is an
-- EU-designated intermediary service; each files its own DSA Transparency Report.

SELECT product_line AS product_id, display_name, service_kind, audience_kind FROM (
    SELECT 'main'     AS product_line, 'Spotify Main'         AS display_name, 'music_streaming'         AS service_kind, 'consumer' AS audience_kind UNION ALL
    SELECT 'artists'  AS product_line, 'Spotify for Artists'  AS display_name, 'music_artist_platform'   AS service_kind, 'creator'  AS audience_kind UNION ALL
    SELECT 'authors'  AS product_line, 'Spotify for Authors'  AS display_name, 'audiobook_author_platform' AS service_kind, 'creator' AS audience_kind UNION ALL
    SELECT 'creators' AS product_line, 'Spotify for Creators' AS display_name, 'podcast_creator_platform' AS service_kind, 'creator' AS audience_kind
) products
