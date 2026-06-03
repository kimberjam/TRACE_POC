"""Public Health tab — county / regional surveillance view.

Cross-county and cross-facility patterns: resistance trends by county,
hotspot detection, multi-county comparisons. Designed for state and
regional health departments, and for investors to see the market-expansion
story.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from .. import data_loader as dl
from .. import components as ui
from .. import theme as t


def render(filters: dict) -> None:
    ui.tab_header(
        "Public health view",
        "Regional surveillance: cross-county resistance patterns, hotspots, "
        "and longitudinal trends. Designed for state and local public health "
        "teams.",
    )

    agg = dl.load_county_month_organism_drug()
    pos_agg = dl.load_county_month_organism()
    zip_30 = dl.load_zip_30day_organism_drug()

    if agg.empty:
        ui.empty_state(
            "Pre-aggregated public-health views not available.",
            "Re-run the synthesis pipeline to generate the aggregates folder.",
        )
        return

    # ----- TOP: regional summary cards -----
    sum_cols = st.columns(3)

    with sum_cols[0]:
        n_counties = agg["county"].nunique()
        ui.kpi_card("Counties in scope", f"{n_counties}",
                    sublabel="Salt Lake · Utah · Washington")

    with sum_cols[1]:
        most_recent = agg["year_month"].max()
        ui.kpi_card("Most recent month",
                    most_recent.strftime("%b %Y") if pd.notna(most_recent) else "—",
                    sublabel="Latest reporting window")

    with sum_cols[2]:
        total_n = int(agg["n_tested"].sum())
        ui.kpi_card("Aggregate isolates", f"{total_n:,}",
                    sublabel="Across all counties and months")

    st.markdown("")

    # ----- MIDDLE LEFT: cross-county resistance comparison -----
    mid_left, mid_right = st.columns([3, 2])

    with mid_left:
        ui.section_header(
            "Cross-county resistance comparison",
            "Latest-month % resistant for clinically high-impact organism × "
            "drug pairs.",
        )

        latest_month = agg["year_month"].max()
        latest = agg[agg["year_month"] == latest_month].copy()
        # Focus on a curated set of high-impact pairs
        focus = [
            ("Escherichia coli", "Ciprofloxacin"),
            ("Escherichia coli", "Ceftriaxone"),
            ("Klebsiella pneumoniae", "Meropenem"),
            ("Pseudomonas aeruginosa", "Piperacillin-Tazobactam"),
            ("Staphylococcus aureus", "Oxacillin"),
            ("Enterococcus species", "Vancomycin"),
        ]
        focus_df = pd.concat(
            [
                latest[(latest["organism"] == org) & (latest["drug"] == drug)]
                for org, drug in focus
            ],
            ignore_index=True,
        )
        if focus_df.empty:
            ui.empty_state("No data for high-impact pairs in latest month.")
        else:
            focus_df["pct_resistant"] = (
                100 - focus_df["pct_susceptible"]
            ).round(1)
            focus_df["pair"] = (
                focus_df["organism"] + " · " + focus_df["drug"]
            )
            chart = (
                alt.Chart(focus_df)
                .mark_bar()
                .encode(
                    x=alt.X("pct_resistant:Q",
                            title="% resistant",
                            scale=alt.Scale(domain=[0, 60])),
                    y=alt.Y("pair:N", title=None, sort="-x"),
                    color=alt.Color(
                        "county:N",
                        scale=alt.Scale(
                            domain=["Salt Lake", "Utah", "Washington"],
                            range=[t.PRIMARY_NAVY, t.TRACE_TEAL, t.SLATE_BLUE],
                        ),
                        legend=alt.Legend(title="County"),
                    ),
                    tooltip=["county", "organism", "drug",
                             "pct_resistant", "n_tested"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)
            ui.evidence_strip(
                period=latest_month.strftime("%b %Y") if pd.notna(latest_month) else "—",
                n=int(focus_df["n_tested"].sum()),
                qa_status="PUBLISHED",
            )

    with mid_right:
        ui.section_header(
            "Positivity trend",
            "Monthly positivity rate for key organisms across the region.",
        )
        if pos_agg.empty:
            ui.empty_state()
        else:
            focal_orgs = [
                "Group A Strep",
                "Streptococcus pneumoniae",
                "Escherichia coli",
            ]
            pos_focus = pos_agg[pos_agg["organism"].isin(focal_orgs)].copy()
            if pos_focus.empty:
                ui.empty_state()
            else:
                trend = (
                    pos_focus.groupby(["year_month", "organism"])
                    .apply(lambda g: (
                        g["n_positive"].sum() * 100 / g["n_tested"].sum()
                    ), include_groups=False)
                    .reset_index()
                    .rename(columns={0: "pct_positive"})
                )
                chart = (
                    alt.Chart(trend)
                    .mark_line(point=False, strokeWidth=2.5)
                    .encode(
                        x=alt.X("year_month:T", title="Month"),
                        y=alt.Y("pct_positive:Q", title="% positive"),
                        color=alt.Color(
                            "organism:N",
                            scale=alt.Scale(
                                range=[t.PRIMARY_NAVY, t.TRACE_TEAL,
                                       t.MUTED_AMBER, t.SLATE_BLUE,
                                       t.SOFT_BLUE],
                            ),
                            legend=alt.Legend(title="Organism",
                                              orient="bottom"),
                        ),
                        tooltip=["year_month:T", "organism", "pct_positive"],
                    )
                    .properties(height=280)
                )
                st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # ----- BOTTOM: ZIP-level hotspot view -----
    ui.section_header(
        "30-day ZIP hotspots — E. coli ciprofloxacin resistance",
        "ZIPs with elevated resistance signal in the most recent 30-day window. "
        "Useful for targeted local stewardship outreach.",
    )

    if zip_30.empty:
        ui.empty_state()
    else:
        eco = zip_30[
            (zip_30["organism"] == "Escherichia coli")
            & (zip_30["drug"] == "Ciprofloxacin")
        ].copy()
        if filters["counties"]:
            eco = eco[eco["county"].isin(filters["counties"])]
        if eco.empty:
            ui.empty_state()
        else:
            eco["pct_resistant"] = (100 - eco["pct_susceptible"]).round(1)
            hot = (
                eco.sort_values("pct_resistant", ascending=False)
                .head(15)
                .rename(columns={
                    "patient_zip": "ZIP",
                    "county": "County",
                    "n_tested": "N tested",
                    "n_susceptible": "N susceptible",
                    "pct_resistant": "% Resistant",
                    "window_start": "Window start",
                    "window_end": "Window end",
                })
            )
            st.dataframe(
                hot[["ZIP", "County", "% Resistant", "N tested",
                     "Window start", "Window end"]],
                use_container_width=True, hide_index=True,
            )
            window_label = (
                f"{hot['Window start'].min():%Y-%m-%d} → "
                f"{hot['Window end'].max():%Y-%m-%d}"
                if not hot.empty else "—"
            )
            ui.evidence_strip(
                period=window_label,
                n=int(hot["N tested"].sum()),
                qa_status="PUBLISHED",
            )

    st.markdown("---")
    ui.about_this_data_panel()
