"""Load the synthetic Utah dataset that powers the TRACE POC.

Auto-detects the data directory in three places, in order:
  1. The TRACE_DATA_DIR environment variable
  2. ./data/utah_synthetic/ relative to the app
  3. ../../../../Claude Mockups/trace_poc_data/ relative to this file
     (the original location of the generated synthetic dataset)

All loaders are Streamlit-cached so reruns don't re-read 60MB of CSV.
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


# ----- Cached loaders -----

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


# ----- Lightweight metadata -----

DATASET_SOURCES = [
    "CDC AR Lab Network public reports",
    "CDC NHSN AUR module aggregate data",
    "Utah Department of Health state antibiogram (most recent published year)",
    "SENTRY and MYSTIC published surveillance studies",
    "IDSA / ATS guideline expected susceptibility ranges",
    "U.S. Census ACS population weighting",
]

DATASET_PERIOD = "May 2024 – April 2026 (24 months)"
DATASET_COUNTIES = ["Salt Lake", "Utah", "Washington"]
DATASET_SEED = 20260506
