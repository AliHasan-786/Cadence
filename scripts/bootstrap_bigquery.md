# BigQuery bootstrap — one-time setup

This sets up the service account and datasets Cadence needs in your GCP project (`spry-smithy-489221-p4`). Run once.

## 1. Create the service account

In the GCP console (signed into ali.hasan@house-iq.ai → project `spry-smithy-489221-p4`):

1. Open **IAM & Admin → Service Accounts** → `https://console.cloud.google.com/iam-admin/serviceaccounts?project=spry-smithy-489221-p4`
2. Click **+ CREATE SERVICE ACCOUNT**
3. Name: `cadence-dbt`
4. ID: `cadence-dbt` (auto-fills)
5. Description: `Service account for Cadence dbt + ingest + API workloads`
6. Click **CREATE AND CONTINUE**
7. Grant these project-level roles (Step 2):
   - **BigQuery Data Editor** — `roles/bigquery.dataEditor`
   - **BigQuery Job User** — `roles/bigquery.jobUser`
8. Click **CONTINUE** → **DONE**

## 2. Generate a JSON key

1. On the service-accounts list, click the `cadence-dbt@spry-smithy-489221-p4.iam.gserviceaccount.com` row
2. Open the **KEYS** tab
3. **ADD KEY → Create new key → JSON → CREATE**
4. The browser downloads `spry-smithy-489221-p4-XXXX.json` to `~/Downloads/`

## 3. Move and protect the key

```bash
mkdir -p ~/.config/gcloud
mv ~/Downloads/spry-smithy-489221-p4-*.json ~/.config/gcloud/cadence-sa.json
chmod 600 ~/.config/gcloud/cadence-sa.json
```

## 4. Export the env var

Add to your shell profile (`~/.zshrc`):

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/cadence-sa.json"
```

Reload: `source ~/.zshrc` (or open a fresh shell).

## 5. Enable BigQuery API

Make sure the BigQuery API is enabled on the project:
`https://console.cloud.google.com/apis/library/bigquery.googleapis.com?project=spry-smithy-489221-p4`

Click **ENABLE** if not already enabled.

## 6. Run the bootstrap script

```bash
uv run python scripts/bootstrap_bigquery.py
```

This creates `cadence_raw` and `cadence` datasets in `US` and prints a confirmation. Idempotent — safe to re-run.

## 7. Verify

```bash
uv run python scripts/bootstrap_bigquery.py --verify
```

Should print:

```
Project: spry-smithy-489221-p4
Auth identity: cadence-dbt@spry-smithy-489221-p4.iam.gserviceaccount.com
Datasets present: cadence_raw, cadence (location=US)
BQ connection OK.
```
