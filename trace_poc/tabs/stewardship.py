"""Stewardship tab — population-level antibiotic stewardship metrics.

Shows:
  - Broad-spectrum rate (% of isolates receiving broad-spectrum antibiotics)
  - SAAR proxy (stewardship-adjusted antibiotic use rate)
  - Resistance burden index
  - Resistance trend chart (county × month × organism × drug)
  - Outlier facilities (if facility-level data available)

Phase 1: uses load_phase1_first_isolates() when available, with
schema-agnostic fallback to the old test-results loader.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from .. import data_loader as dl
from .. import metrics as m
from .. import components as ui
from .. import theme as t


# Antibiotics considered broad-spectrum for stewardship purposes
_BROAD_SPECTRUM = {
    "Piperacillin-Tazobactam",
    "Meropenem",
    "Ertapenem",
    "Imipenem",
    "Doripenem",
    "Cefepime",
    "Vancomycin",
    "Linezolid",
    "Daptomycin",
    "Colistin",
    "Polymyxin B",
    "Tigecycline",
    "Ceftazidime-Avibactam",
    "Ceftolozane-Tazobactam",
}


def render(filters: dict) -> None:
    ui.tab_header(
        "Stewardship view",
        "Population-level antibiotic stewardship metrics for quality "
        "improvement. All figures are aggregate and de-identified.",
    )

    # ── Load data ──────────────────────────────────────────────────────────
    using_phase1 = dl.PHASE1_DATA_AVAILABLE
    if using_phase1:
        df = dl.load_phase1_first_isolates()
    else:
        df = dl.load_test_results(
            counties=filters["counties"],
            encounter_settings=filters.get("encounter_settings"),
        )

    # Apply county filter using whichever geography column is present
    geo_col  = m._col(df, "displayed_geography_value", "county")
    drug_col = m._col(df, "antibiotic_normalized", "drug")
    sir_col  = m._col(df, "sir_normalized", "susceptibility")
    id_col   = m._col(df, "isolate_id", "test_id")
    org_col  = m._col(df, "organism_normalized", "organism")

    if filters.get("counties"):
        df = df[df[geo_col].isin(filters["counties"])]

    if using_phase1:
        st.caption("⚡ Showing Phase 1 canonical data — first-isolate dedup applied.")

    if df.empty:
        ui.empty_state(
            "No data for the selected filters.",
            "Try widening the county or date range.",
        )
        return

    st.markdown("")

    # ── KPI ROW ────────────────────────────────────────────────────────────
    kpi_cols = st.columns(3)

    # Card 1: Broad-spectrum rate
    with kpi_cols[0]:
        broad_set = _BROAD_SPECTRUM
        n_broad     = df[df[drug_col].isin(broad_set)].shape[0]
        n_total_iso = df[df[sir_col].isin(["S", "R", "I", "S-DD", "NS"])][id_col].nunique()
        broad_rate  = 100.0 * n_broad / n_total_iso if n_total_iso else None
        ui.kpi_card(
            "Broad-spectrum rate",
            f"{broad_rate:.1f}%" if broad_rate is not None else "—",
            sublabel=f"{n_broad:,} broad-spectrum tests / {n_total_iso:,} isolates",
            help_text=(
                "Share of first isolates tested against a broad-spectrum agent. "
                "A rising rate may signal over-escalation."
            ),
        )

    # Card 2: SAAR proxy
    with kpi_cols[1]:
        saar = m.saar_proxy(df)
        ui.kpi_card(
            "SAAR proxy",
            f"{saar:.2f}" if saar is not None else "—",
            sublabel="Observed / expected broad-spectrum use",
            help_text=(
                "Stewardship-Adjusted Antibiotic Rate proxy. "
                "Values > 1.0 indicate higher-than-expected broad-spectrum use "
                "given the local case mix."
            ),
        )

    # Card 3: Resistance burden index
    with kpi_cols[2]:
        rbi = m.resistance_burden_index(df)
        ui.kpi_card(
            "Resistance burden index",
            f"{rbi:.2f}" if rbi is not None else "—",
            sublabel="Weighted resistance across tested drugs",
            help_text=(
                "Composite index: mean resistance rate weighted by testing volume. "
                "Higher values indicate a greater overall resistance burden in the population."
            ),
        )

    st.markdown("")

    # ── TREND CHART ────────────────────────────────────────────────────────
    ui.section_header(
        "Resistance trend",
        "Monthly % susceptible for the top organisms in scope. "
        "Uses pre-aggregated county-level data.",
    )

    # This pre-aggregated CSV is unchanged in Phase 1 — use it directly.
    trend_df = dl.load_county_month_organism_drug()

    if filters.get("counties"):
        trend_df = trend_df[trend_df["county"].isin(filters["counties"])]

    if trend_df.empty:
        ui.empty_state("No trend data available for the selected counties.")
    else:
        # Let user pick organism for trend
        orgs_available = sorted(trend_df["organism"].dropna().unique().tolist())
        selected_org = st.selectbox(
            "Organism",
            orgs_available,
            index=0,
            key="stewardship_trend_org",
        )
        trend_org = trend_df[trend_df["organism"] == selected_org].copy()

        if trend_org.empty:
            ui.empty_state("No trend data for this organism.")
        else:
            drugs_available = sorted(trend_org["drug"].dropna().unique().tolist())
            selected_drugs = st.multiselect(
                "Antibiotics",
                drugs_available,
                default=drugs_available[:4] if len(drugs_available) >= 4 else drugs_available,
                key="stewardship_trend_drugs",
            )
            if selected_drugs:
                trend_plot = trend_org[trend_org["drug"].isin(selected_drugs)].copy()
                # year_month is already datetime (parsed in data_loader)
                chart = (
                    alt.Chart(trend_plot)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("year_month:T", title="Month"),
                        y=alt.Y(
                            "pct_susceptible:Q",
                            scale=alt.Scale(domain=[0, 100]),
                            title="% Susceptible",
                        ),
                        color=alt.Color("drug:N", title="Antibiotic"),
                        tooltip=["year_month:T", "drug:N", "pct_susceptible:Q", "n_isolates:Q"],
                    )
                    .properties(height=280)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                ui.empty_state("Select at least one antibiotic to display.")

    st.markdown("---")

    # ── OUTLIER FACILITIES ─────────────────────────────────────────────────
    ui.section_header(
        "Outlier facilities",
        "Facilities with statistically elevated resistance rates vs. county peers. "
        "Requires facility-level identifiers in the data.",
    )

    if "facility_id" not in df.columns:
        st.caption(
            "Facility-level breakdown not available in the current data extract. "
            "This section activates when facility identifiers are present."
        )
    else:
        outliers = m.outlier_facilities(df)
        if outliers.empty:
            st.caption("No outlier facilities detected in the current scope.")
        else:
            display = outliers.rename(columns={
                "facility_id": "Facility",
                "organism": "Organism",
                "drug": "Drug",
                "pct_resistant": "% Resistant",
                "county_avg_pct_resistant": "County avg %",
                "z_score": "Z-score",
            })
            st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── ABOUT ──────────────────────────────────────────────────────────────
    ui.about_this_data_panel()
