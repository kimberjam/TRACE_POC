"""Adaptive geographic resolution — one shared implementation for every tab
that needs to decide "is there enough local data to show a ZIP-level number,
or do we need to zoom out."

Before this module existed, that decision was made two different,
inconsistent ways in this app: weather_map.py silently dropped any ZIP
under 30 isolates with no fallback at all, and ehr_sandbox.py had its own
separate ZIP -> county -> statewide chain with a threshold of 5 and no
region tier — despite its own footer claiming "n>=30 threshold." This
module is the single source of truth both tabs now use, and it corrects
that footer claim to actually be true.

Ported from the standalone lab_ingest/geography.py prototype (see
`TRACE - Technical/Dashboard/Ingestion Files_Templates/TRACE POC/lab_ingest/`),
adapted to this app's existing column names (organism, drug, patient_zip,
county, susceptibility, test_id) and reusing this app's own wilson_ci
instead of a second copy of the same formula.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .metrics import wilson_ci

DEFAULT_MIN_ISOLATES = 30
DEFAULT_MAX_CI_HALFWIDTH: Optional[float] = None  # None = isolate-count check only

LEVEL_ZIP = "zip"
LEVEL_COUNTY = "county"
LEVEL_REGION = "region"
LEVEL_STATEWIDE = "statewide"
LEVEL_INSUFFICIENT = "insufficient_data"

# Same grouping the Weather Map's own zoom presets already use
# ("Wasatch Front" / "St. George") — not a new invention.
DEFAULT_COUNTY_TO_REGION = {
    "Salt Lake": "Wasatch Front",
    "Utah": "Wasatch Front",
    "Washington": "Southwest Utah",
}


@dataclass
class GeographyResolution:
    requested_zip: str
    resolved_level: str
    resolved_label: str
    n_isolates: int
    pct_susceptible: Optional[float]
    ci_lo: Optional[float]
    ci_hi: Optional[float]
    stable: bool
    levels_tried: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    matched_rows: Optional[pd.DataFrame] = field(default=None, repr=False)


def _summarize(sub: pd.DataFrame) -> tuple[int, Optional[float], Optional[float], Optional[float]]:
    n = sub["test_id"].nunique() if not sub.empty else 0
    if n == 0:
        return 0, None, None, None
    p_hat = (sub["susceptibility"] == "S").mean()
    pct = round(p_hat * 100, 1)
    lo, hi = wilson_ci(p_hat, n)
    return n, pct, lo, hi


def _is_stable(n: int, ci_lo, ci_hi, min_isolates: int, max_ci_halfwidth: Optional[float]) -> bool:
    if n < min_isolates:
        return False
    if max_ci_halfwidth is not None and ci_lo is not None and ci_hi is not None:
        if (ci_hi - ci_lo) / 2 > max_ci_halfwidth:
            return False
    return True


def _resolve(
    df: pd.DataFrame,
    zip_code: str,
    row_filter: pd.Series,
    min_isolates: int,
    max_ci_halfwidth: Optional[float],
    county_to_region: dict[str, str],
) -> GeographyResolution:
    """Shared ZIP -> County -> Region -> Statewide walk. `row_filter` has
    already selected the organism (and optionally drug) rows to consider;
    this function only adds the geography narrowing on top.
    """
    base = df[row_filter & df["susceptibility"].isin(["S", "R"])]
    zip_rows = df.loc[df["patient_zip"] == zip_code]
    county_matches = zip_rows["county"].dropna().unique()
    county = county_matches[0] if len(county_matches) else None
    region = county_to_region.get(county) if county else None

    levels_tried: list[str] = []
    notes: list[str] = []

    def _try(level: str, label: str, mask: pd.Series) -> Optional[GeographyResolution]:
        levels_tried.append(level)
        sub = base[mask]
        n, pct, lo, hi = _summarize(sub)
        if _is_stable(n, lo, hi, min_isolates, max_ci_halfwidth):
            return GeographyResolution(
                requested_zip=zip_code, resolved_level=level, resolved_label=label,
                n_isolates=n, pct_susceptible=pct, ci_lo=lo, ci_hi=hi, stable=True,
                levels_tried=list(levels_tried), notes=list(notes), matched_rows=sub,
            )
        notes.append(f"{label}: n={n}, below the {min_isolates}-isolate threshold." if n < min_isolates
                      else f"{label}: n={n}, but the confidence interval is too wide to call stable.")
        return None

    result = _try(LEVEL_ZIP, f"ZIP {zip_code}", base["patient_zip"] == zip_code)
    if result:
        return result

    if county:
        result = _try(LEVEL_COUNTY, f"{county} County", base["county"] == county)
        if result:
            return result
    else:
        notes.append(f"ZIP {zip_code} not found in the ZIP-to-county lookup.")

    if region:
        counties_in_region = [c for c, r in county_to_region.items() if r == region]
        result = _try(LEVEL_REGION, region, base["county"].isin(counties_in_region))
        if result:
            return result

    n, pct, lo, hi = _summarize(base)
    levels_tried.append(LEVEL_STATEWIDE)
    stable = _is_stable(n, lo, hi, min_isolates, max_ci_halfwidth)
    if not stable:
        notes.append(f"Statewide: only n={n}, still below the {min_isolates}-isolate threshold.")
    return GeographyResolution(
        requested_zip=zip_code,
        resolved_level=LEVEL_STATEWIDE if stable else LEVEL_INSUFFICIENT,
        resolved_label="Statewide", n_isolates=n, pct_susceptible=pct, ci_lo=lo, ci_hi=hi,
        stable=stable, levels_tried=list(levels_tried), notes=list(notes), matched_rows=base,
    )


def resolve_geography(
    df: pd.DataFrame,
    zip_code: str,
    organism: str,
    drug: str,
    min_isolates: int = DEFAULT_MIN_ISOLATES,
    max_ci_halfwidth: Optional[float] = DEFAULT_MAX_CI_HALFWIDTH,
    county_to_region: Optional[dict[str, str]] = None,
) -> GeographyResolution:
    """Resolve one (ZIP, organism, drug) susceptibility question — the
    precise question the Weather Map's ZIP bubbles each represent."""
    county_to_region = county_to_region or DEFAULT_COUNTY_TO_REGION
    mask = (df["organism"] == organism) & (df["drug"] == drug)
    return _resolve(df, zip_code, mask, min_isolates, max_ci_halfwidth, county_to_region)


def resolve_organism_scope(
    df: pd.DataFrame,
    zip_code: str,
    organism: str,
    min_isolates: int = DEFAULT_MIN_ISOLATES,
    max_ci_halfwidth: Optional[float] = DEFAULT_MAX_CI_HALFWIDTH,
    county_to_region: Optional[dict[str, str]] = None,
) -> GeographyResolution:
    """Resolve the geographic scope for a whole organism panel (all drugs
    together) — what the EHR Sandbox's antibiogram card needs, since it
    shows a multi-drug table under one shared scope label rather than
    picking a geography per drug."""
    county_to_region = county_to_region or DEFAULT_COUNTY_TO_REGION
    mask = df["organism"] == organism
    return _resolve(df, zip_code, mask, min_isolates, max_ci_halfwidth, county_to_region)
