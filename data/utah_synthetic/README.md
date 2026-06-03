# TRACE POC Synthetic Dataset

**Generated:** 2026-05-12
**Random seed:** 20260506
**Coverage:** Salt Lake County, Utah County, Washington County (Utah). Real ZIPs, fictional facility names.
**Time horizon:** May 2024 – April 2026 (24 months)
**Records:** 458,650 test-level rows (152,604 unique tests)

## Files

- `test_results.csv` / `test_results.parquet` — test-level records, one row per organism × drug
- `aggregates/county_month_organism_drug.csv` — % susceptible aggregated by county × month
- `aggregates/zip_30day_organism_drug.csv` — % susceptible by ZIP for the most recent 30 days (CDS card surface)
- `aggregates/county_month_organism.csv` — positivity rates by county × month
- `facilities.csv` — fictional facility metadata
- `zip_county_map.csv` — ZIP → county lookup

## Important

This is **fully synthetic data**. No real patient values, no real lab outputs, no real facility names. All susceptibility rates, MIC distributions, and seasonal patterns are statistically calibrated to public sources:

- CDC AR Lab Network public reports
- CDC NHSN AUR module aggregate data
- Utah Department of Health state antibiogram (most recent published year)
- Published surveillance studies (SENTRY, MYSTIC)
- IDSA / ATS guideline expected ranges
- U.S. Census ACS (population weighting)

To regenerate: `python generate_trace_data.py <output_dir>` from the script directory.
Reproducible — same seed produces the same dataset.
