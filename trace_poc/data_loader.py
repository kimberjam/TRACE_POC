"""Load the synthetic Utah dataset that powers the TRACE POC.

Auto-detects the data directory in three places, in order:
  1. The TRACE_DATA_DIR environment variable
  2. ./data/utah_synthetic/ relative to the app
  3. ../../../../Claude Mockups/trace_poc_data/ relative to this file
     (the original location of the generated synthetic dataset)

All loaders are Streamlit-cached so reruns don't re-read 60MB of CSV.

── Phase 1 loaders (new) ───────────────────────────────────────────────────
load_phase1_processed()      Full Phase 1 canonical parquet (all 63 fields)
load_phase1_first_isolates() First-isolate-only subset (what the dashboard shows)
PHASE1_DATA_AVAILABLE        True when data/phase1/phase1_processed.parquet exists
────────────────────────────────────────────────────────────────────────────

Old loaders (load_test_results, load_facilities, …) are unchanged so existing
tabs continue to work during the Step 3 migration.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

# ----- Locate the dataset -----

_THIS_DIR = Path(__file__).resolve().parent
_APP_DIR = _THIS_DIR.parent
# Walk up to TRACE - Technical/ then into Claude Mockups/trace_poc_data/
# (trace_poc_unified/ → TRACE POC/ → Ingestion Files_Templates/ →
#  Dashboard/ → TRACE - Technical/)
_ORIGINAL_PATH = (
    _APP_DIR.parent.parent.parent.parent / "Claude Mockups" / "trace_poc_data"
)


def find_data_dir() -> Optional[Path]:
    """Return the first existing dataset location, or None if not found."""
    candidates = []
    env = os.environ.get("TRACE_DATA_DIR")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(_APP_DIR / "data" / "utah_synthetic")
    candidates.append(_ORIGINAL_PATH)
    for c in candidates:
        if c.exists() and (c / "test_results.csv").exists():
            return c
    return None


# ── Phase 1 data location ─────────────────────────────────────────────────────

_PHASE1_PARQUET = _APP_DIR / "data" / "phase1" / "phase1_processed.parquet"


def find_phase1_data() -> Optional[Path]:
    """Return path to Phase 1 processed parquet, or None if not found."""
    if _PHASE1_PARQUET.exists():
        return _PHASE1_PARQUET
    return None


#: True when the Phase 1 processed parquet is available on disk.
PHASE1_DATA_AVAILABLE: bool = _PHASE1_PARQUET.exists()


# ----- Cached loaders (legacy — old schema) ----------------------------------

@st.cache_data(show_spinner=False)
def load_facilities() -> pd.DataFrame:
    """Facility metadata: id, name, county, type, share_within_county."""
    data_dir = find_data_dir()
    if data_dir is None:
        return pd.DataFrame()
    return pd.read_csv(data_dir / "facilities.csv")


@st.cache_data(show_spinner=False)
def load_zip_county_map() -> pd.DataFrame:
    """ZIP → county lookup with population."""
    data_dir = find_data_dir()
    if data_dir is None:
        return pd.DataFrame()
    return pd.read_csv(data_dir / "zip_county_map.csv", dtype={"zip": str})


@st.cache_data(show_spinner="Loading test-level records…")
def load_test_results(
    counties: Optional[list[str]] = None,
    encounter_settings: Optional[list[str]] = None,
    specimen_types: Optional[list[str]] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
) -> pd.DataFrame:
    """Load test-level results, optionally filtered.

    Columns: test_id, collection_date, result_date, patient_zip, county,
    patient_age_band, patient_sex, facility_id, encounter_setting,
    specimen_type, test_method, organism, drug, mic_value, susceptibility.
    """
    data_dir = find_data_dir()
    if data_dir is None:
        return pd.DataFrame()
    df = pd.read_csv(
        data_dir / "test_results.csv",
        parse_dates=["collection_date", "result_date"],
        dtype={"patient_zip": str},
    )
    if counties:
        df = df[df["county"].isin(counties)]
    if encounter_settings:
        df = df[df["encounter_setting"].isin(encounter_settings)]
    if specimen_types:
        df = df[df["specimen_type"].isin(specimen_types)]
    if date_start:
        df = df[df["collection_date"] >= pd.Timestamp(date_start)]
    if date_end:
        df = df[df["collection_date"] <= pd.Timestamp(date_end)]
    return df


@st.cache_data(show_spinner=False)
def load_county_month_organism_drug() -> pd.DataFrame:
    """Pre-aggregated: county × month × organism × drug → % susceptible."""
    data_dir = find_data_dir()
    if data_dir is None:
        return pd.DataFrame()
    df = pd.read_csv(data_dir / "aggregates" / "county_month_organism_drug.csv")
    df["year_month"] = pd.to_datetime(df["year_month"] + "-01")
    return df


@st.cache_data(show_spinner=False)
def load_county_month_organism() -> pd.DataFrame:
    """Pre-aggregated: county × month × organism → positivity rate."""
    data_dir = find_data_dir()
    if data_dir is None:
        return pd.DataFrame()
    df = pd.read_csv(data_dir / "aggregates" / "county_month_organism.csv")
    df["year_month"] = pd.to_datetime(df["year_month"] + "-01")
    return df


@st.cache_data(show_spinner=False)
def load_zip_30day_organism_drug() -> pd.DataFrame:
    """Pre-aggregated: ZIP × organism × drug → % susceptible (last 30d window)."""
    data_dir = find_data_dir()
    if data_dir is None:
        return pd.DataFrame()
    df = pd.read_csv(
        data_dir / "aggregates" / "zip_30day_organism_drug.csv",
        dtype={"patient_zip": str},
        parse_dates=["window_start", "window_end"],
    )
    return df


# ── Phase 1 loaders (new schema — 63 fields) ----------------------------------

@st.cache_data(show_spinner="Loading Phase 1 canonical data…")
def load_phase1_processed() -> pd.DataFrame:
    """Load the full Phase 1 processed parquet (all 63 canonical fields).

    Returns an empty DataFrame if the parquet does not exist yet.
    Run ingestion/run_phase1_demo.py (or the real lab adapters) to generate it.

    Key columns (Phase 1 schema):
        organism_normalized          canonical organism name
        antibiotic_normalized        canonical antibiotic name
        sir_normalized               S / I / R / S-DD / NS
        care_setting                 Outpatient / ED / LTC / Inpatient / Urgent care
        specimen_category_normalized Urine / Wound-Abscess / ...
        patient_age_band             18-44 / 45-64 / 65+
        patient_sex                  F / M
        patient_zip                  5-digit ZIP
        displayed_geography_level    patient_zip / clinic_zip / county / state
        displayed_geography_value    actual value at that level
        is_phase1_eligible           bool: passes all Phase 1 inclusion criteria
        is_first_isolate_primary     bool: first isolate per patient x org x specimen
        is_inpatient / is_ed / is_ltc / is_urgent_care  care-setting flags
        n_tested                     n in denominator for susceptibility %
        n_susceptible                n with sir_normalized == 'S'
        ci_lower / ci_upper          Wilson 95% CI bounds
        reliability_label            'Strong data support' / 'Limited' / 'Insufficient'
        privacy_suppression_flag     True -> suppress from display (n < 5)
        display_group                antibiotic display group (1-4)
        stewardship_note             CIP fluoroquinolone caution, etc.
        intrinsic_resistance_note    P. mirabilis + NIT note
        cefazolin_surrogate_note     CFZ surrogate caution
    """
    path = find_phase1_data()
    if path is None:
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if "collection_date" in df.columns:
        df["collection_date"] = pd.to_datetime(df["collection_date"], errors="coerce")
    return df


@st.cache_data(show_spinner="Loading Phase 1 first-isolate data…")
def load_phase1_first_isolates(
    organisms: Optional[list[str]] = None,
    care_settings: Optional[list[str]] = None,
    specimen_categories: Optional[list[str]] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    include_suppressed: bool = False,
) -> pd.DataFrame:
    """Load Phase 1 eligible first-isolates -- the display-ready subset.

    Applies automatically:
      * is_phase1_eligible == True
      * is_first_isolate_primary == True
      * privacy_suppression_flag == False  (unless include_suppressed=True)

    This is the recommended source for the clinician, stewardship, and public
    health tabs once they are migrated to the Phase 1 schema (Step 3).

    Parameters
    ----------
    organisms           list of organism_normalized values (None = all)
    care_settings       list of care_setting values (None = all)
    specimen_categories list of specimen_category_normalized values (None = all)
    date_start / date_end   collection_date bounds (ISO string, inclusive)
    include_suppressed  if True, include privacy-suppressed rows (default False)

    Returns
    -------
    DataFrame with all 63 Phase 1 canonical columns.
    """
    df = load_phase1_processed()
    if df.empty:
        return df

    mask = (
        df["is_phase1_eligible"].fillna(False).astype(bool)
        & df["is_first_isolate_primary"].fillna(False).astype(bool)
    )
    if not include_suppressed:
        mask = mask & (~df["privacy_suppression_flag"].fillna(False).astype(bool))

    df = df[mask].copy()

    if organisms:
        df = df[df["organism_normalized"].isin(organisms)]
    if care_settings:
        df = df[df["care_setting"].isin(care_settings)]
    if specimen_categories:
        df = df[df["specimen_category_normalized"].isin(specimen_categories)]
    if date_start:
        df = df[df["collection_date"] >= pd.Timestamp(date_start)]
    if date_end:
        df = df[df["collection_date"] <= pd.Timestamp(date_end)]

    return df


# ----- Lightweight metadata --------------------------------------------------

DATASET_SOURCES = [
    "CDC AR Lab Network public reports",
    "CDC NHSN AUR module aggregate data",
    "Utah Department of Health state antibiogram (most recent published year)",
    "SENTRY and MYSTIC published surveillance studies",
    "IDSA / ATS guideline expected susceptibility ranges",
    "U.S. Census ACS population weighting",
]

DATASET_PERIOD = "May 2024 - April 2026 (24 months)"
DATASET_COUNTIES = ["Salt Lake", "Utah", "Washington"]
DATASET_SEED = 20260506
