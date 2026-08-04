"""Metric computations powering the dashboard KPIs.

All functions are pure pandas — they take a filtered DataFrame and return a
single number or a small structured result. UI code in tabs/ calls these and
renders the result. Keeping the math out of the UI makes it easy to test and
easy to swap rendering layers later.

── Phase 1 additions ────────────────────────────────────────────────────────
Functions auto-detect the data schema (old 27-field vs new 63-field) by
checking for `organism_normalized` in the DataFrame columns. Old tabs work
unchanged; Phase 1 tabs get richer outputs.

New / enhanced:
  susceptibility_table_p1()  — returns display_group, reliability_label, CI
  isolate_count()            — now Phase 1 aware
  filter_susceptibility()    — now Phase 1 aware
  empiric_coverage()         — now Phase 1 aware
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# ── Schema helpers ─────────────────────────────────────────────────────────────

def _col(df: pd.DataFrame, new_name: str, old_name: str) -> str:
    """Return new_name if present in df, else old_name."""
    return new_name if new_name in df.columns else old_name


def _is_phase1(df: pd.DataFrame) -> bool:
    """True if df uses the Phase 1 63-field schema."""
    return "organism_normalized" in df.columns


def _sir_values(df: pd.DataFrame) -> pd.Series:
    """Return the SIR column regardless of schema."""
    col = _col(df, "sir_normalized", "susceptibility")
    return df[col]


def _sir_in_denominator(df: pd.DataFrame) -> pd.Series:
    """Mask: rows that count in the susceptibility denominator."""
    sir = _sir_values(df)
    if _is_phase1(df):
        # Phase 1: S, I, R, S-DD, NS all in denominator
        return sir.isin(["S", "I", "R", "S-DD", "NS"])
    else:
        # Old schema: only S and R
        return sir.isin(["S", "R"])


def _sir_susceptible(df: pd.DataFrame) -> pd.Series:
    """Mask: rows that are susceptible (numerator)."""
    return _sir_values(df) == "S"


# ----- Susceptibility primitives -----

def filter_susceptibility(
    df: pd.DataFrame,
    organism: Optional[str] = None,
    drugs: Optional[list[str]] = None,
    counties: Optional[list[str]] = None,
    facility_ids: Optional[list[str]] = None,
    encounter_settings: Optional[list[str]] = None,
    specimen_types: Optional[list[str]] = None,
    days_back: Optional[int] = None,
) -> pd.DataFrame:
    """Return rows that have a susceptibility result.

    Accepts both the old 27-field schema and the new Phase 1 63-field schema.
    """
    org_col  = _col(df, "organism_normalized",          "organism")
    drug_col = _col(df, "antibiotic_normalized",        "drug")
    geo_col  = _col(df, "displayed_geography_value",    "county")
    set_col  = _col(df, "care_setting",                 "encounter_setting")
    spec_col = _col(df, "specimen_category_normalized", "specimen_type")

    sub = df[_sir_in_denominator(df)].copy()

    if organism and org_col in sub.columns:
        sub = sub[sub[org_col] == organism]
    if drugs and drug_col in sub.columns:
        sub = sub[sub[drug_col].isin(drugs)]
    if counties and geo_col in sub.columns:
        sub = sub[sub[geo_col].isin(counties)]
    if facility_ids and "facility_id" in sub.columns:
        sub = sub[sub["facility_id"].isin(facility_ids)]
    if encounter_settings and set_col in sub.columns:
        sub = sub[sub[set_col].isin(encounter_settings)]
    if specimen_types and spec_col in sub.columns:
        sub = sub[sub[spec_col].isin(specimen_types)]
    if days_back is not None and "collection_date" in sub.columns:
        cutoff = sub["collection_date"].max() - pd.Timedelta(days=days_back)
        sub = sub[sub["collection_date"] >= cutoff]
    return sub


def wilson_ci(p_hat: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson-score 95% CI on a proportion.

    p_hat: observed proportion (0–1).  n: denominator.
    Returns (lo, hi) as percentages.
    """
    import math
    if n <= 0:
        return (0.0, 0.0)
    z2 = z * z
    denom = 1 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denom
    margin = (z * math.sqrt(p_hat * (1 - p_hat) / n + z2 / (4 * n * n))) / denom
    lo = max(0.0, center - margin) * 100
    hi = min(1.0, center + margin) * 100
    return (round(lo, 1), round(hi, 1))


def percent_susceptible(df: pd.DataFrame) -> Optional[float]:
    """% of isolates marked Susceptible. Returns None if no isolates.

    Works with both old and Phase 1 schemas.
    """
    if df.empty:
        return None
    denom = _sir_in_denominator(df).sum()
    if denom == 0:
        return None
    return 100.0 * _sir_susceptible(df).sum() / denom


def susceptibility_table(df: pd.DataFrame, organism: str) -> pd.DataFrame:
    """For a single organism, return antibiotic × (% susceptible, N) table.

    Works with both old and Phase 1 schemas. For Phase 1 data, prefer
    susceptibility_table_p1() to get reliability labels and CI bounds.
    """
    org_col  = _col(df, "organism_normalized",   "organism")
    drug_col = _col(df, "antibiotic_normalized",  "drug")

    sub = df[(df[org_col] == organism) & _sir_in_denominator(df)]
    if sub.empty:
        return pd.DataFrame(columns=["drug", "pct_susceptible", "n_isolates"])

    grp = sub.groupby(drug_col).apply(
        lambda g: pd.Series({
            "n_isolates":   _sir_in_denominator(g).sum(),
            "n_susceptible": _sir_susceptible(g).sum(),
        }),
        include_groups=False,
    )
    grp["pct_susceptible"] = (100.0 * grp["n_susceptible"] / grp["n_isolates"]).round(1)
    return (
        grp.reset_index()
        .rename(columns={drug_col: "drug"})
        [["drug", "pct_susceptible", "n_isolates"]]
        .sort_values("pct_susceptible", ascending=False)
        .reset_index(drop=True)
    )


def susceptibility_table_p1(df: pd.DataFrame, organism: str) -> pd.DataFrame:
    """Phase 1 version: susceptibility table with display_group, reliability, CI.

    Uses pre-computed n_tested / n_susceptible / ci_lower / ci_upper already
    set by trace_phase1_pipeline.py, so no re-aggregation needed.

    Input should be load_phase1_first_isolates() data (eligible first-isolates,
    privacy suppression already applied).

    Returns columns:
        antibiotic_normalized, display_group, pct_susceptible,
        n_tested, ci_lower_pct, ci_upper_pct, reliability_label,
        stewardship_note, intrinsic_resistance_note, cefazolin_surrogate_note
    """
    if not _is_phase1(df):
        # Fall back to old-style table for backward compat
        tbl = susceptibility_table(df, organism)
        return tbl.rename(columns={"drug": "antibiotic_normalized",
                                   "n_isolates": "n_tested"})

    sub = df[df["organism_normalized"] == organism].copy()
    if sub.empty:
        return pd.DataFrame(columns=[
            "antibiotic_normalized", "display_group", "pct_susceptible",
            "n_tested", "ci_lower_pct", "ci_upper_pct", "reliability_label",
            "stewardship_note", "intrinsic_resistance_note",
            "cefazolin_surrogate_note",
        ])

    # Use pre-computed stats (one row per isolate-drug — take first for each drug)
    agg = (
        sub.groupby("antibiotic_normalized")
        .agg(
            n_tested=("n_tested", "first"),
            n_susceptible=("n_susceptible", "first"),
            ci_lower=("ci_lower", "first"),
            ci_upper=("ci_upper", "first"),
            reliability_label=("reliability_label", "first"),
            display_group=("display_group", "first"),
            stewardship_note=("stewardship_note", "first"),
            intrinsic_resistance_note=("intrinsic_resistance_note", "first"),
            cefazolin_surrogate_note=("cefazolin_surrogate_note", "first"),
        )
        .reset_index()
    )
    agg["pct_susceptible"] = (
        100.0 * agg["n_susceptible"] / agg["n_tested"].replace(0, np.nan)
    ).round(1)
    agg["ci_lower_pct"] = (agg["ci_lower"] * 100).round(1)
    agg["ci_upper_pct"] = (agg["ci_upper"] * 100).round(1)

    return (
        agg[[
            "antibiotic_normalized", "display_group", "pct_susceptible",
            "n_tested", "ci_lower_pct", "ci_upper_pct", "reliability_label",
            "stewardship_note", "intrinsic_resistance_note",
            "cefazolin_surrogate_note",
        ]]
        .sort_values(["display_group", "pct_susceptible"],
                     ascending=[True, False])
        .reset_index(drop=True)
    )


# ----- Clinician KPIs -----

@dataclass
class CoverageResult:
    """Result of an empiric coverage calculation."""
    regimen_label: str
    drugs: list[str]
    pct_covered: Optional[float]
    n_isolates: int


def empiric_coverage(
    df: pd.DataFrame,
    organism: str,
    drugs: list[str],
) -> CoverageResult:
    """% of isolates susceptible to AT LEAST ONE drug in the regimen.

    Works with both old and Phase 1 schemas.
    """
    org_col  = _col(df, "organism_normalized",  "organism")
    drug_col = _col(df, "antibiotic_normalized", "drug")
    id_col   = _col(df, "isolate_id",            "test_id")

    sub = df[(df[org_col] == organism) & _sir_in_denominator(df)]
    if sub.empty:
        return CoverageResult(
            regimen_label=" + ".join(drugs),
            drugs=drugs,
            pct_covered=None,
            n_isolates=0,
        )
    pivot = (
        sub.assign(is_S=_sir_susceptible(sub).astype(int))
        .groupby([id_col, drug_col])["is_S"]
        .max()
        .unstack(fill_value=np.nan)
    )
    available = [d for d in drugs if d in pivot.columns]
    if not available:
        return CoverageResult(
            regimen_label=" + ".join(drugs),
            drugs=drugs,
            pct_covered=None,
            n_isolates=len(pivot),
        )
    covered = pivot[available].max(axis=1).fillna(0).astype(bool)
    n = len(covered)
    return CoverageResult(
        regimen_label=" + ".join(drugs),
        drugs=drugs,
        pct_covered=100.0 * covered.sum() / n if n else None,
        n_isolates=n,
    )


def time_to_result_hours(df: pd.DataFrame) -> Optional[float]:
    """Median hours from collection to result."""
    if df.empty or "collection_date" not in df.columns:
        return None
    sub = df[_sir_in_denominator(df)].dropna(
        subset=["collection_date", "result_date"]
    )
    if sub.empty:
        return None
    delta = (sub["result_date"] - sub["collection_date"]).dt.total_seconds() / 3600.0
    return float(delta.median())


def isolate_count(df: pd.DataFrame, organism: Optional[str] = None) -> int:
    """Count unique isolates in the denominator.

    Works with both schemas. Phase 1 data uses `isolate_id`; old data uses
    `test_id`.
    """
    org_col = _col(df, "organism_normalized", "organism")
    id_col  = _col(df, "isolate_id",          "test_id")

    sub = df[_sir_in_denominator(df)]
    if organism and org_col in sub.columns:
        sub = sub[sub[org_col] == organism]
    if id_col in sub.columns:
        return int(sub[id_col].nunique())
    return len(sub)


# ----- Hospital / stewardship tab metrics -----

def saar_proxy(df: pd.DataFrame, facility_id: str) -> Optional[float]:
    """Standardized Antimicrobial Administration Ratio proxy (demo only).

    Uses old schema (facility_id, drug columns). Phase 2 will replace this
    with real NHSN AU days-of-therapy data.
    """
    if df.empty:
        return None
    drug_col = _col(df, "antibiotic_normalized", "drug")
    broad = ["Piperacillin-Tazobactam", "Cefepime", "Meropenem", "Vancomycin"]
    if "facility_id" not in df.columns:
        return None
    fac = df[df["facility_id"] == facility_id]
    if fac.empty:
        return None
    fac_broad = fac[fac[drug_col].isin(broad)].shape[0]
    all_broad  = df[df[drug_col].isin(broad)].shape[0]
    if all_broad == 0:
        return None
    county_col = _col(df, "displayed_geography_value", "county")
    same_county_facs = (
        df[df[county_col] == fac[county_col].iloc[0]]["facility_id"].nunique()
        if county_col in df.columns and county_col in fac.columns
        else 1
    )
    if same_county_facs == 0:
        return None
    expected_share = 1.0 / same_county_facs
    actual_share   = fac_broad / all_broad
    return actual_share / expected_share


def resistance_burden_index(df: pd.DataFrame) -> float:
    """Composite resistance burden score (0–100). Higher = worse.

    Works with both schemas.
    """
    org_col  = _col(df, "organism_normalized",  "organism")
    drug_col = _col(df, "antibiotic_normalized", "drug")

    burden_pairs = [
        ("Escherichia coli",         "Ciprofloxacin",              0.20),
        ("Escherichia coli",         "Ceftriaxone",                0.15),
        ("Klebsiella pneumoniae",    "Meropenem",                  0.20),
        ("Pseudomonas aeruginosa",   "Piperacillin-Tazobactam",    0.15),
        ("Staphylococcus aureus",    "Oxacillin",                  0.15),
        ("Enterococcus species",     "Vancomycin",                 0.15),
    ]
    score = 0.0
    total_weight = 0.0
    for organism, drug, weight in burden_pairs:
        sub = df[
            (df[org_col] == organism)
            & (df[drug_col] == drug)
            & _sir_in_denominator(df)
        ]
        if sub.empty:
            continue
        pct_resistant = 100.0 * (_sir_values(sub) == "R").mean()
        score += weight * pct_resistant
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return round(score / total_weight, 1)


def outlier_facilities(df: pd.DataFrame, threshold: float = 1.3) -> pd.DataFrame:
    """Facilities whose broad-spectrum-use proxy exceeds threshold × peers."""
    if "facility_id" not in df.columns:
        return pd.DataFrame(columns=["facility_id", "saar_proxy"])
    facs = df["facility_id"].dropna().unique()
    rows = []
    for fac in facs:
        s = saar_proxy(df, fac)
        if s is not None and s >= threshold:
            rows.append({"facility_id": fac, "saar_proxy": round(s, 2)})
    if not rows:
        return pd.DataFrame(columns=["facility_id", "saar_proxy"])
    return pd.DataFrame(rows).sort_values("saar_proxy", ascending=False)
