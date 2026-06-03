"""Hospital tab — institutional / stewardship-leadership view.

Layout (per draw.io mockup in Dashboard/Code/TRACE_hospital.txt):
  - Top: three benchmark cards (SAAR proxy, AU rate proxy, Resistance Burden)
  - Middle-left: trend panel (AU and Resistance over time)
  - Middle-right: Outlier Alerts (facilities flagged vs peers)
  - Bottom: Facility Comparison table
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from .. import data_loader as dl
from .. import metrics as m
from .. import components as ui
from .. import theme as t


def render(filters: dict) -> None:
    ui.tab_header(
        "Hospital view",
        "Stewardship leadership metrics: usage patterns, resistance burden, "
        "facility-level outliers, peer comparisons. "
        "Aligned with the CDC NHSN AUR module reporting model.",
    )

    df = dl.load_test_results(counties=filters["counties"])
    if df.empty:
        ui.empty_state(
            "No data for the current county selection.",
            "Add at least one county in the sidebar.",
        )
        return

    facilities = dl.load_facilities()

    # ----- BENCHMARK ROW -----
    kpi_cols = st.columns(3)

    # Card 1: SAAR-style proxy for current county
    with kpi_cols[0]:
        # Show the most-utilized facility's SAAR proxy as a headline
        facs_in_scope = (
            facilities[facilities["county"].isin(filters["counties"])]
            if not facilities.empty else pd.DataFrame()
        )
        if not facs_in_scope.empty:
            anchor_fac = facs_in_scope.sort_values(
                "share_within_county", ascending=False
            ).iloc[0]
            saar = m.saar_proxy(df, anchor_fac["facility_id"])
            if saar is not None:
                delta = f"{(saar - 1.0) * 100:+.0f}% vs peers"
                ui.kpi_card(
                    "SAAR (proxy)",
                    f"{saar:.2f}",
                    sublabel=f"Anchor: {anchor_fac['facility_name']}",
                    delta=delta,
                    help_text=(
                        "Standardized Antimicrobial Administration Ratio "
                        "proxy. 1.0 = at peer level. Real SAAR requires "
                        "NHSN AU days-of-therapy submissions (Phase 2)."
                    ),
                )
            else:
                ui.kpi_card("SAAR (proxy)", "—",
                            sublabel="Insufficient broad-spectrum data")
        else:
            ui.kpi_card("SAAR (proxy)", "—")

    # Card 2: AU rate proxy (broad-spectrum tests per 1000 isolates)
    with kpi_cols[1]:
        broad = ["Piperacillin-Tazobactam", "Cefepime", "Meropenem"]
        n_broad = df[df["drug"].isin(broad)].shape[0]
        n_total_iso = df[df["susceptibility"].isin(["S", "R"])]["test_id"].nunique()
        if n_total_iso > 0:
            rate = 1000 * n_broad / n_total_iso
            ui.kpi_card(
                "Broad-Spectrum AU Rate",
                f"{rate:.0f}",
                sublabel="Broad-spectrum tests per 1,000 isolates",
                help_text=(
                    "Proxy for AU days-of-therapy. Real metric (DOT/1000 "
                    "patient-days) requires pharmacy data in Phase 2."
                ),
            )
        else:
            ui.kpi_card("Broad-Spectrum AU Rate", "—")

    # Card 3: Resistance Burden Index
    with kpi_cols[2]:
        rbi = m.resistance_burden_index(df)
        ui.kpi_card(
            "Resistance Burden Index",
            f"{rbi:.1f}",
            sublabel="Composite, 0–100. Higher = worse.",
            help_text=(
                "Weighted average of resistance for clinically high-impact "
                "organism × drug pairs (ESBL, CRE, MRSA, VRE, "
                "Pseudomonas-Pip-Tazo)."
            ),
        )

    st.markdown("")

    # ----- MIDDLE ROW -----
    mid_left, mid_right = st.columns([2, 1])

    with mid_left:
        ui.section_header(
            "Resistance & usage trend",
            "Monthly trend of resistance burden across the selected counties.",
        )

        # Monthly resistance index using aggregates
        agg = dl.load_county_month_organism_drug()
        if filters["counties"]:
            agg = agg[agg["county"].isin(filters["counties"])]

        # Trend: % resistant for E. coli ciprofloxacin (proxy for resistance trend)
        eco = agg[(agg["organism"] == "Escherichia coli")
                  & (agg["drug"] == "Ciprofloxacin")]
        if not eco.empty:
            trend = (
                eco.groupby("year_month")
                .apply(lambda g: 100 - (
                    g["n_susceptible"].sum() * 100 / g["n_tested"].sum()
                ), include_groups=False)
                .reset_index()
                .rename(columns={0: "pct_resistant"})
            )
            trend["pct_resistant"] = trend["pct_resistant"].round(1)
            chart = (
                alt.Chart(trend)
                .mark_line(point=True, color=t.CLINICAL_CORAL, strokeWidth=2.5)
                .encode(
                    x=alt.X("year_month:T", title="Month"),
                    y=alt.Y(
                        "pct_resistant:Q",
                        title="E. coli ciprofloxacin resistance (%)",
                        scale=alt.Scale(domain=[0, 50]),
                    ),
                    tooltip=["year_month:T", "pct_resistant"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart, use_container_width=True)
            ui.evidence_strip(
                county=", ".join(filters["counties"]),
                period="rolling monthly",
                qa_status="PUBLISHED",
            )
        else:
            ui.empty_state("No trend data in scope.")

    with mid_right:
        ui.section_header("Outlier alerts")
        outliers = m.outlier_facilities(df, threshold=1.3)
        if outliers.empty:
            st.success("No facilities exceeding peer threshold.", icon="✅")
        else:
            outliers = outliers.merge(
                facilities[["facility_id", "facility_name"]],
                on="facility_id", how="left",
            )
            for _, row in outliers.iterrows():
                st.warning(
                    f"**{row['facility_name']}** — SAAR proxy "
                    f"{row['saar_proxy']:.2f}",
                    icon="⚠️",
                )

        ui.section_header("Stewardship signals")
        st.info(
            "Local fluoroquinolone resistance trending up — consider "
            "stewardship intervention for ED empiric UTI orders.",
            icon="ℹ️",
        )
        st.info(
            "Broad-spectrum use higher in ICU vs peer ICUs in cohort.",
            icon="ℹ️",
        )

    st.markdown("---")

    # ----- BOTTOM: FACILITY COMPARISON -----
    ui.section_header(
        "Facility comparison",
        "Each facility's SAAR proxy, AU rate, and resistance burden vs. peers.",
    )

    if not facilities.empty:
        rows = []
        for _, fac in facilities[
            facilities["county"].isin(filters["counties"])
        ].iterrows():
            fac_df = df[df["facility_id"] == fac["facility_id"]]
            saar = m.saar_proxy(df, fac["facility_id"])
            rbi = m.resistance_burden_index(fac_df) if not fac_df.empty else None
            n_iso = m.isolate_count(fac_df)
            rows.append({
                "Facility": fac["facility_name"],
                "County": fac["county"],
                "Type": fac["facility_type"],
                "SAAR (proxy)": f"{saar:.2f}" if saar is not None else "—",
                "Resistance Burden": f"{rbi:.1f}" if rbi is not None else "—",
                "N isolates": n_iso,
            })
        comp = pd.DataFrame(rows).sort_values("Facility")
        st.dataframe(comp, use_container_width=True, hide_index=True)
    else:
        ui.empty_state("Facility metadata not available.")

    st.markdown("---")
    ui.about_this_data_panel()
