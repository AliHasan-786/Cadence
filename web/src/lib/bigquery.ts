/**
 * Server-only BigQuery client.
 *
 * Credentials come from one of two env vars:
 *   1. GOOGLE_APPLICATION_CREDENTIALS_BASE64 — base64-encoded SA JSON (Vercel)
 *   2. GOOGLE_APPLICATION_CREDENTIALS — path to SA JSON file (local dev)
 *
 * Never imported into a Client Component — this file lives on the server.
 */

import "server-only";
import { BigQuery } from "@google-cloud/bigquery";

export const PROJECT_ID = "spry-smithy-489221-p4";
export const LOCATION = "US";
export const DATASET_MARTS_TRANSPARENCY = "cadence_marts_transparency";
export const DATASET_MARTS_SAFETY = "cadence_marts_safety";
export const DATASET_MARTS_LLM_OPS = "cadence_marts_llm_ops";
export const DATASET_SEEDS = "cadence_seeds";

let _client: BigQuery | null = null;

export function getBigQuery(): BigQuery {
  if (_client) return _client;

  const b64 = process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64;
  if (b64) {
    const json = JSON.parse(Buffer.from(b64, "base64").toString("utf8"));
    _client = new BigQuery({
      projectId: PROJECT_ID,
      credentials: { client_email: json.client_email, private_key: json.private_key },
      location: LOCATION,
    });
    return _client;
  }

  const path = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (path) {
    _client = new BigQuery({ projectId: PROJECT_ID, keyFilename: path, location: LOCATION });
    return _client;
  }

  throw new Error(
    "No BigQuery credentials. Set GOOGLE_APPLICATION_CREDENTIALS_BASE64 (Vercel) " +
      "or GOOGLE_APPLICATION_CREDENTIALS (local).",
  );
}

/** Run a parameterless query, return typed rows. */
export async function bqQuery<T = Record<string, unknown>>(sql: string): Promise<T[]> {
  const bq = getBigQuery();
  const [rows] = await bq.query({ query: sql, location: LOCATION });
  return rows as T[];
}
