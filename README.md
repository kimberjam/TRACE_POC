# TRACE — Unified POC

Antibiotic stewardship and antimicrobial-resistance dashboard. Aligned with the CDC NHSN AUR module data structure. Streamlit-based, four-tab layout (Clinician · Hospital · Public Health · Admin), powered by the 24-month synthetic Utah dataset.

This folder is the unified, polished POC that consolidates earlier work. It is the canonical place to develop, demo, and pilot from. Earlier POC variants (`ui_poc/`, `ui_poc_v0_1_working/`, `TRACE_POC_v0.1_WORKING:/`, `ingestion_poc/`, `trace_cds_poc/`) are kept as archive references; new work happens here.

## Quick start

```bash
# 1. Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run (the synthetic data ships in data/utah_synthetic/)
streamlit run app.py
```

The app auto-detects the dataset in three locations, in order:
`$TRACE_DATA_DIR` env var, `./data/utah_synthetic/`, and the original
`Claude Mockups/trace_poc_data/` path relative to this folder.

## Live deployment

For Streamlit Community Cloud hosting (a shareable HTTPS URL), see
**[DEPLOY.md](./DEPLOY.md)**.

## What's in here

- `app.py` — main Streamlit entry, four-tab navigation, header/branding, shared global filters
- `.streamlit/config.toml` — custom clinical theme
- `trace_poc/` — package
  - `data_loader.py` — loads test-level records, aggregates, facility metadata, ZIP-county map
  - `metrics.py` — computes KPIs (Empiric Coverage Score, susceptibility snapshots, time-to-result, AU rate proxies, SAAR-style benchmarks)
  - `guideline_content.py` — hand-curated guideline-aligned content keyed by (infection site, care setting, organism). Faithful to IDSA/ATS/SHEA recommendations with citations. Designed as a drop-in for a future RAG layer.
  - `components.py` — reusable UI components: Evidence Chip, KPI card, About-this-data panel, empty states
  - `tabs/` — one module per tab
    - `clinician.py` — hero tab. Empiric Coverage Score, Local Susceptibility Snapshot, Time to Effective Therapy, Empiric Therapy Explorer with ranked options, Clinical Risk & Context, Recent Similar Cases
    - `hospital.py` — SAAR vs benchmark, AU rate, Resistance Burden Index, trends, outlier alerts, facility comparison
    - `public_health.py` — county-level resistance map, multi-county trends, hotspots
    - `admin.py` — data sources, freshness, QA queue, ingestion log

## Demo scenarios

The app ships with pre-set scenarios so investors and clinicians can land on populated views without learning the filters. See the **Demo Scenarios** dropdown in the sidebar.

## Data

The synthetic Utah dataset (458,650 rows, 24 months, 3 counties, 17 facilities) is calibrated to:
- CDC AR Lab Network public reports
- CDC NHSN AUR module aggregate data
- Utah Department of Health state antibiogram
- SENTRY / MYSTIC published surveillance studies
- IDSA / ATS guideline expected ranges
- U.S. Census ACS population weighting

No real patient data. No real facility names. Susceptibility rates and seasonal patterns are statistically plausible for the geography. Fully reproducible from `generate_trace_data.py` (seed: 20260506).

## Status

- Phase 1 (current): unified POC, polished demo, hand-curated guideline content
- Phase 2 (next): real antibiogram ingestion pipeline; layer real RAG over the guideline content interface
- Phase 3 (pilot): clinician-in-the-loop feedback, eval-set, expert review board
