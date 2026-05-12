/**
 * Citation infrastructure — every number on every page resolves to a source.
 *
 * Three citation types:
 *   - dbt: a dbt model file in the GitHub repo (with anchored line range if useful)
 *   - spotify: a verbatim Spotify-published source URL (PRD §15)
 *   - yaml: a methodology weight or threshold in safety_metrics.yml
 */

export type CitationKind = "dbt" | "spotify" | "yaml";

export type Citation = {
  kind: CitationKind;
  /** Short label rendered inside the chip. */
  label: string;
  /** Resolved URL. Always opens in a new tab. */
  href: string;
  /** Long-form tooltip body. */
  tooltip: string;
};

const REPO_TREE = "https://github.com/AliHasan-786/Cadence/blob/main";

// --- dbt model citations -----------------------------------------------------

export function citeDbtModel(
  modelName: string,
  opts?: { layer?: "staging" | "intermediate" | "marts/transparency" | "marts/safety" | "marts/llm_ops" | "marts/researcher" },
): Citation {
  const layer = opts?.layer ?? guessLayer(modelName);
  const href = `${REPO_TREE}/models/${layer}/${modelName}.sql`;
  return {
    kind: "dbt",
    label: modelName,
    href,
    tooltip: `Source: models/${layer}/${modelName}.sql — dbt model in the Cadence repo.`,
  };
}

function guessLayer(modelName: string): string {
  if (modelName.startsWith("stg_")) return "staging";
  if (modelName.startsWith("int_")) return "intermediate";
  if (modelName.startsWith("sig_") || modelName.startsWith("fct_artificial_streaming")) return "marts/safety";
  if (modelName.startsWith("rpt_llm") || modelName.startsWith("fct_llm")) return "marts/llm_ops";
  if (modelName.startsWith("rpt_researcher") || modelName.startsWith("fct_researcher") || modelName.startsWith("dim_researcher")) return "marts/researcher";
  return "marts/transparency";
}

// --- Spotify-published source citations --------------------------------------

const SPOTIFY_XLSX: Record<string, string> = {
  main: "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_main",
  artists: "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_artists",
  authors: "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_authors",
  creators: "https://www.spotify.com/safetyandprivacy/file/eu_2025_dsa_report_spotify_for_creators",
};

export function citeSpotifyXlsx(product: "main" | "artists" | "authors" | "creators"): Citation {
  return {
    kind: "spotify",
    label: `Spotify ${product} XLSX`,
    href: SPOTIFY_XLSX[product],
    tooltip: `Source: Spotify's published ${product} DSA Transparency Report XLSX (annual 2025, published 27 Feb 2026).`,
  };
}

export function citeSpotifyTransparencyHub(): Citation {
  return {
    kind: "spotify",
    label: "Spotify Transparency Hub",
    href: "https://www.spotify.com/us/safetyandprivacy/transparency",
    tooltip: "Spotify's public transparency hub listing all four DSA reports.",
  };
}

// --- YAML methodology citations ---------------------------------------------

export function citeMethodologyWeight(signal: string): Citation {
  // Resolves to the safety_metrics.yml file in the repo. Browsers won't auto-anchor
  // to a YAML key, but GitHub renders the file with line numbers + search.
  return {
    kind: "yaml",
    label: `weight: ${signal}`,
    href: `${REPO_TREE}/models/semantic/safety_metrics.yml`,
    tooltip: `Methodology: ${signal} weight is defined in models/semantic/safety_metrics.yml. Edit there and the entire pipeline re-tunes.`,
  };
}

export function citeYamlSection(label: string): Citation {
  return {
    kind: "yaml",
    label,
    href: `${REPO_TREE}/models/semantic/safety_metrics.yml`,
    tooltip: `safety_metrics.yml — methodology source of truth.`,
  };
}
