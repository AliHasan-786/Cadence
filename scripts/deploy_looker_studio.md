# Looker Studio dashboard deployment runbook

3 dashboards must be deployed against the **production** `cadence_marts_transparency` dataset (not the CI dataset) so their URLs are stable and recruiter-clickable. This runbook is the source of truth for what each dashboard shows.

## Prerequisites (verify before starting)

```bash
# 1. Production marts are populated
bq ls cadence-public:cadence_marts_transparency   # should show 9 rpt_* + 4 dim_* + 3 fct_* tables
# OR:
uv run python -c "from google.cloud import bigquery; \
    c = bigquery.Client(project='spry-smithy-489221-p4'); \
    print(list(c.list_tables('cadence_marts_transparency')))"

# 2. Looker Studio org policy allows public sharing
#    (If your GCP org locks this down, see fallback below)

# 3. Cadence service account has BigQuery Data Viewer on cadence_marts_transparency
#    (already true — it's a dataEditor on the project)
```

If public sharing is locked at the org level: create a parallel **personal** Google account for hosting these dashboards. The dashboards read from BigQuery using your work identity but share publicly through the personal account.

---

## Dashboard 1 — Cross-Product Executive Summary

**Source:** `spry-smithy-489221-p4.cadence_marts_transparency.rpt_cross_product_summary`

**Purpose:** The headline view for Compliance Counsel + Policy Manager. One row per product line, all key DSA metrics side-by-side. This is the dashboard the recruiter clicks first.

**Build steps:**

1. https://lookerstudio.google.com/ → **+ Blank report**
2. **Add data → BigQuery**
3. Select project `spry-smithy-489221-p4` → dataset `cadence_marts_transparency` → table `rpt_cross_product_summary` → **Add**
4. Rename the report: **Cadence — Spotify DSA Cross-Product Executive Summary (Annual 2025)**

**Layout (top to bottom):**

- **Header text block:** "Cadence — Cross-Product DSA Comparison" (32pt, Spotify green #1DB954 only on the small accent bar; everything else black on white)
- **Subtitle:** "Reporting period: Annual 2025 (published 27 Feb 2026 by Spotify). Source: Spotify DSA Transparency Reports × 4 product lines. Methodology: github.com/AliHasan-786/Cadence."
- **Row 1 — 4 scorecards (one per product):**
  - `total_decisions` formatted as comma-thousands
  - `notices_received` below it
  - `automated_share_pct` formatted as percent
  - `automated_accuracy_pct` formatted as percent
- **Row 2 — Bar chart:** `total_decisions` by `product_line`
  - X axis: `product_line`
  - Y axis: `total_decisions`
  - Color: single solid Spotify green
  - Annotation: "Creators dominates volume (5.9k internal complaints) because of podcast catalog scale via Anchor"
- **Row 3 — Stacked bar:** `actions_on_law` vs `actions_on_tc` by product
- **Row 4 — Table:** All columns of `rpt_cross_product_summary`, sortable, with subtle row borders. Hide `reporting_period_start/_end`.
- **Footer:** "Synthetic stream-event data labeled `_synth` is NOT shown here — this dashboard surfaces only Spotify's published DSA data."

**Sharing:**
- File → Share → Get link → **Anyone with the link can view**
- Copy URL into `README.md` under `## Live URLs`

---

## Dashboard 2 — Operational Trends

**Sources:**
- `cadence_marts_transparency.rpt_quarter_over_quarter_trends` (time-series)
- `cadence_marts_transparency.rpt_automated_vs_human` (posture comparison)

**Purpose:** Policy Manager view. How is each product evolving? What's the automation posture?

**Build steps:**

1. Looker Studio → **+ Blank report**
2. Add **both** data sources
3. Rename: **Cadence — DSA Operational Trends (Annual 2025)**

**Layout:**

- **Header:** "Operational Trends — Automation Posture + Quarter-over-Quarter"
- **Subtitle:** "With only one period currently loaded, the trend view shows one datapoint per series. 2024 backfill = Sprint V1.1."
- **Row 1 — Banner annotation (callout text block):** "1 period available — series will populate as more reporting periods land. n_periods_available column drives this state."
- **Row 2 — Time-series chart:** `total_decisions` by `reporting_period_start` faceted by `product_line` (`rpt_quarter_over_quarter_trends`)
- **Row 3 — 4 scorecards comparing automation posture (`rpt_automated_vs_human`):**
  - For each product: `automated_accuracy_pct` (with the `automation_posture` label below as a chip — conservative / aggressive / balanced)
- **Row 4 — Heatmap-style table:** rows = product_line, columns = (accuracy, precision, recall), cell color scaled by value
- **Row 5 — Highlight callout:** "Main is the only product labeled conservative (100% accuracy, 94.4% recall = 5.6pp accuracy-over-recall). Artists is the only aggressive posture (95% accuracy, 96% recall = 1pp recall-over-accuracy). This is the cross-product policy-shape distinction visible only at the marts layer."
- **Footer:** see Dashboard 1.

**Sharing:** same as Dashboard 1.

---

## Dashboard 3 — Member-State Heatmap

**Source:** `cadence_marts_transparency.rpt_member_state_breakdown`

**Purpose:** EU regulator-facing view. Per-Member-State drilldown.

**Build steps:**

1. Looker Studio → **+ Blank report**
2. Add the data source
3. Rename: **Cadence — Member-State Breakdown (Annual 2025)**

**Layout:**

- **Header:** "Member-State Breakdown — Spotify DSA Orders (Annual 2025)"
- ⚠️ **HONEST-SCOPE BANNER** (top of page, yellow background, NOT decorative — operationally important):
  > "Spotify's 2025 DSA reports disclose only EU_AGGREGATE rather than per-Member-State granularity. This dashboard surfaces that gap honestly rather than fabricating distribution. When/if Spotify discloses per-state data in future reports, this dashboard will populate automatically via the existing schema."
- **Row 1 — 4 scorecards** (orders_to_act, items_in_orders_to_act, orders_to_provide_info, mean median_time_to_inform_act_hours) by product_line, EU_AGGREGATE only
- **Row 2 — Table:** `rpt_member_state_breakdown` filtered to `is_aggregate = false` (will be empty — that's the point. Display "(no rows — see banner above)" empty-state text)
- **Row 3 — Choropleth placeholder:** Static EU map image with a "Per-state data not currently disclosed" overlay. (Looker Studio's Geo chart needs lat/lng data; with all rows aggregating to one synthetic country code, the map can't render meaningfully. Visual fidelity here is honest > pretty.)
- **Footer:** see Dashboard 1.

**Sharing:** same as Dashboard 1.

---

## Verification checklist

After each dashboard is deployed:

- [ ] Open the URL in an **incognito window**. Should load without sign-in prompt.
- [ ] Verify the numbers match the BQ source. Run:
  ```sql
  SELECT * FROM `spry-smithy-489221-p4.cadence_marts_transparency.rpt_cross_product_summary`
  ORDER BY product_line;
  ```
  in BQ console and check that the dashboard scorecards show the same values.
- [ ] Add the URL to `README.md` under the `## Live URLs` section.
- [ ] Take a screenshot, save to `docs/dashboards/dashboard_<N>.png`.

## What we deliberately don't do

- **No LookML-driven dashboards.** That requires Looker (Google's enterprise BI), not Looker Studio. The `looker/` directory's LookML files are the methodology-contract artifact (parallel to MetricFlow) — the Looker Studio dashboards read from BigQuery directly using the production marts.
- **No multi-LLM verdict interactivity.** Looker Studio can't render the verbatim-transcript Dialog modals the Detection Lab needs. The Next.js app (Sprint 13) owns that surface.
- **No per-PR dashboards.** Looker Studio dashboards are stable URLs against production. PRs build into `cadence_ci_*` datasets for testing; production deploys to `cadence_*` on main-branch merges only.

## If a dashboard ever breaks

This runbook is the rebuild instructions. Looker Studio dashboards built in the UI aren't fully version-controllable — the runbook + the screenshots in `docs/dashboards/` are the recovery path.
