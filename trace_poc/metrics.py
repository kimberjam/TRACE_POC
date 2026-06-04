"""Metric computations powering the dashboard KPIs.

All functions are pure pandas — they take a filtered DataFrame and return a
single number or a small structured result. UI code in tabs/ calls these and
renders the result. Keeping the math out of the UI makes it easy to test and
easy to swap rendering layers later.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


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
    """Return test-level rows that have a susceptibility result (S/R)."""
    sub = df[df["susceptibility"].isin(["S", "R"])].copy()
    if organism:
        sub = sub[sub["organism"] == organism]
    if drugs:
        sub = sub[sub["drug"].isin(drugs)]
    if counties:
        sub = sub[sub["county"].isin(counties)]
    if facility_ids:
        sub = sub[sub["facility_id"].isin(facility_ids)]
    if encounter_settings:
        sub = sub[sub["encounter_setting"].isin(encounter_settings)]
    if specimen_types:
        sub = sub[sub["specimen_type"].isin(specimen_types)]
    if days_back is not None:
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
    """% of isolates marked Susceptible. Returns None if no isolates."""
    if df.empty:
        return None
    return 100.0 * (df["susceptibility"] == "S").mean()


def susceptibility_table(df: pd.DataFrame, organism: str) -> pd.DataFrame:
    """For a single organism, return drug × (% susceptible, N) table."""
    sub = df[(df["organism"] == organism) & df["susceptibility"].isin(["S", "R"])]
    if sub.empty:
        return pd.DataFrame(columns=["drug", "pct_susceptible", "n_isolates"])
    grp = sub.groupby("drug").agg(
        n_isolates=("susceptibility", "size"),
        n_susceptible=("susceptibility", lambda s: (s == "S").sum()),
    )
    grp["pct_susceptible"] = (100.0 * grp["n_susceptible"] / grp["n_isolates"]).round(1)
    return (
        grp.reset_index()[["drug", "pct_susceptible", "n_isolates"]]
        .sort_values("pct_susceptible", ascending=False)
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
    """For a given organism and a candidate regimen (list of drugs),
    compute the % of isolates susceptible to AT LEAST ONE drug in the regimen.

    This is the standard "empiric coverage" estimate — would this regimen have
    covered the bug if we'd chosen it before culture results came back.
    """
    sub = df[(df["organism"] == organism) & df["susceptibility"].isin(["S", "R"])]
    if sub.empty:
        return CoverageResult(
            regimen_label=" + ".join(drugs),
            drugs=drugs,
            pct_covered=None,
            n_isolates=0,
        )
    # Pivot to one row per isolate, columns = drugs, values = "S"/"R"
    pivot = (
        sub.assign(is_S=(sub["susceptibility"] == "S").astype(int))
        .groupby(["test_id", "drug"])["is_S"]
        .max()
        .unstack(fill_value=np.nan)
    )
    # An isolate is "covered" if any drug in the regimen tests Susceptible.
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
    """Median hours from collection to result (proxy for time-to-effective-therapy
    signal — once the result lands, therapy can be tailored)."""
    if df.empty or "collection_date" not in df.columns:
        return None
    sub = df[df["susceptibility"].isin(["S", "R"])].dropna(
        subset=["collection_date", "result_date"]
    )
    if sub.empty:
        return None
    delta = (sub["result_date"] - sub["collection_date"]).dt.total_seconds() / 3600.0
    return float(delta.median())


def isolate_count(df: pd.DataFrame, organism: Optional[str] = None) -> int:
    sub = df[df["susceptibility"].isin(["S", "R"])]
    if organism:
        sub = sub[sub["organism"] == organism]
    return int(sub["test_id"].nunique())


# ----- Hospital tab metrics -----

def saar_proxy(df: pd.DataFrame, facility_id: str) -> Optional[float]:
    """Standardized Antimicrobial Administration Ratio proxy.

    Real SAAR comes from NHSN AU days-of-therapy submissions; we don't have
    that here, so we proxy with the facility's share of broad-spectrum-drug
    susceptibility tests (a hand-rolled stand-in). This is for demo only —
    the real SAAR pipeline is Phase-2 work.
    """
    if df.empty:
        return None
    broad = ["Piperacillin-Tazobactam", "Cefepime", "Meropenem", "Vancomycin"]
    fac = df[df["facility_id"] == facility_id]
    if fac.empty:
        return None
    fac_broad = fac[fac["drug"].isin(broad)].shape[0]
    all_broad = df[df["drug"].isin(broad)].shape[0]
    if all_broad == 0:
        return None
    # Normalize by expected share (number of facilities in same county).
    same_county_facs = df[df["county"] == fac["county"].iloc[0]]["facility_id"].nunique()
    if same_county_facs == 0:
        return None
    expected_share = 1.0 / same_county_facs
    actual_share = fac_broad / all_broad
    return actual_share / expected_share  # 1.0 = at peer level


def resistance_burden_index(df: pd.DataFrame) -> float:
    """Composite resistance burden score (0–100).

    Weighted average of resistance rates for clinically high-impact
    organism × drug pairs. Higher = worse local resistance picture.
    """
    burden_pairs = [
        ("Escherichia coli", "Ciprofloxacin", 0.20),
        ("Escherichia coli", "Ceftriaxone", 0.15),
        ("Klebsiella pneumoniae", "Meropenem", 0.20),
        ("Pseudomonas aeruginosa", "Piperacillin-Tazobactam", 0.15),
        ("Staphylococcus aureus", "Oxacillin", 0.15),
        ("Enterococcus species", "Vancomycin", 0.15),
    ]
    score = 0.0
    total_weight = 0.0
    for organism, drug, weight in burden_pairs:
        sub = df[
            (df["organism"] == organism)
            & (df["drug"] == drug)
            & df["susceptibility"].isin(["S", "R"])
        ]
        if sub.empty:
            continue
        pct_resistant = 100.0 * (sub["susceptibility"] == "R").mean()
        score += weight * pct_resistant
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return round(score / total_weight, 1)


def outlier_facilities(df: pd.DataFrame, threshold: float = 1.3) -> pd.DataFrame:
    """Facilities whose broad-spectrum-use proxy exceeds threshold × peers."""
    facs = df["facility_id"].dropna().unique()
    rows = []
    for fac in facs:
        s = saar_proxy(df, fac)
        if s is not None and s >= threshold:
            rows.append({"facility_id": fac, "saar_proxy": round(s, 2)})
    if not rows:
        # Return empty DataFrame with the right columns so downstream code
        # can still call .sort_values / .merge without KeyError.
        return pd.DataFrame(columns=["facility_id", "saar_proxy"])
    return pd.DataFrame(rows).sort_values("saar_proxy", ascending=False)
