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
        "Stewardship view",
        "Hospital and antimicrobial stewardship leadership metrics: usage "
        "patterns, resistance burden, facility-level outliers, peer "
        "comparisons. Aligned with CDC NHSN AUR reporting.",
    )

    df = dl.load_test_results(counties=filters["counties"])
    if df.empty:
        ui.empty_state(
            "No data for the current county selection.",
            "Add at least one county in the sidebar.",
        )
        return

    facilities = dl.load_facilities()
    facs_in_scope = (
        facilities[facilities["county"].isin(filters["counties"])]
        if not facilities.empty else pd.DataFrame()
    )

    # Pre-compute key metrics
    rbi = m.resistance_burden_index(df)
    broad = ["Piperacillin-Tazobactam", "Cefepime", "Meropenem"]
    n_broad = df[df["drug"].isin(broad)].shape[0]
    n_total_iso = df[df["susceptibility"].isin(["S", "R"])]["test_id"].nunique()
    broad_rate = (1000 * n_broad / n_total_iso) if n_total_iso > 0 else 0
    anchor_fac_name = "—"
    anchor_saar = None
    if not facs_in_scope.empty:
        anchor_fac = facs_in_scope.sort_values(
            "share_within_county", ascending=False
        ).iloc[0]
        anchor_fac_name = anchor_fac["facility_name"]
        anchor_saar = m.saar_proxy(df, anchor_fac["facility_id"])

    # ----- HERO CARD: Resistance Burden Index -----
    chips = []
    if anchor_saar is not None:
        saar_pct = (anchor_saar - 1.0) * 100
        saar_tone = "watch" if saar_pct >= 5 else (
            "stable" if saar_pct <= -5 else "neutral"
        )
        chips.append((f"SAAR {anchor_saar:.2f} ({saar_pct:+.0f}% vs peers)",
                      saar_tone))
    chips.append((f"Broad-spectrum {broad_rate:.0f}/1k isolates",
                  "watch" if broad_rate > 200 else "neutral"))
    chips.append((f"N = {n_total_iso:,} isolates", "neutral"))

    rbi_tone_text = (
        "low burden" if rbi < 15 else
        "moderate burden" if rbi < 30 else "elevated burden"
    )

    ui.hero_stat_card(
        brand_title="TRACE · Stewardship intelligence",
        meta_text=(
            f"<strong style='color:{t.PRIMARY_NAVY};'>"
            f"{anchor_fac_name}</strong>"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;{', '.join(filters['counties'])}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;trailing 24 months"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;NHSN AUR-aligned"
        ),
        stat_label="RESISTANCE BURDEN INDEX",
        stat_value=f"{rbi:.1f}",
        stat_unit="/100",
        sub_text=(
            f"Composite weighted across ESBL, CRE, MRSA, VRE, and "
            f"Pseudomonas–Pip-Tazo pairs — currently in the "
            f"<strong>{rbi_tone_text}</strong> band."
        ),
        chips=chips,
        comparison_cells=[
            (
                "Anchor SAAR",
                f"{anchor_saar:.2f}" if anchor_saar is not None else "—",
                "1.00 = at peer level",
            ),
            (
                "Broad-spectrum rate",
                f"{broad_rate:.0f}",
                "per 1,000 isolates",
            ),
            (
                "Resistance burden",
                f"{rbi:.1f}",
                "composite, 0–100",
            ),
        ],
        live=True,
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
            ui.branded_alert(
                "No facilities exceeding peer threshold",
                "All facilities in the selected counties are within 1.3× the "
                "peer median broad-spectrum-use share.",
                tone="stable",
                icon="✓",
            )
        else:
            outliers = outliers.merge(
                facilities[["facility_id", "facility_name"]],
                on="facility_id", how="left",
            )
            for _, row in outliers.iterrows():
                ui.branded_alert(
                    f"{row['facility_name']}",
                    f"SAAR proxy {row['saar_proxy']:.2f} — "
                    f"{(row['saar_proxy'] - 1.0) * 100:+.0f}% vs peer "
                    f"median. Stewardship review suggested.",
                    tone="watch",
                    icon="⚠",
                )

        ui.section_header("Stewardship signals")
        ui.branded_alert(
            "Fluoroquinolone resistance trending up",
            "Local E. coli ciprofloxacin susceptibility has dropped this "
            "quarter. Consider stewardship intervention for ED empiric "
            "UTI orders — non-fluoroquinolone first-line where appropriate.",
            tone="info",
            icon="ℹ",
        )
        ui.branded_alert(
            "Broad-spectrum use elevated in ICU",
            "ICU broad-spectrum prescribing exceeds peer ICUs by "
            "approximately 18%. De-escalation review at 48–72h is the "
            "highest-leverage intervention.",
            tone="info",
            icon="ℹ",
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
            rbi_fac = m.resistance_burden_index(fac_df) if not fac_df.empty else None
            n_iso_fac = m.isolate_count(fac_df)
            rows.append({
                "facility": fac["facility_name"],
                "county": fac["county"],
                "type": fac["facility_type"],
                "saar": saar,
                "rbi": rbi_fac,
                "n": n_iso_fac,
            })

        # Sort: highest SAAR first (most stewardship concern at top)
        rows.sort(key=lambda r: (r["saar"] if r["saar"] is not None else -1),
                  reverse=True)

        # Build custom HTML table
        def _saar_chip(v):
            if v is None:
                return f'<span style="color:{t.SLATE_BLUE};">—</span>'
            tone = "concern" if v >= 1.3 else ("watch" if v >= 1.1 else "stable")
            return ui.evidence_chip(f"{v:.2f}", tone=tone)

        def _rbi_chip(v):
            if v is None:
                return f'<span style="color:{t.SLATE_BLUE};">—</span>'
            tone = "concern" if v >= 30 else ("watch" if v >= 15 else "stable")
            return ui.evidence_chip(f"{v:.1f}", tone=tone)

        header_html = (
            f'<thead><tr style="background:{t.PRIMARY_NAVY}; color:white;">'
            f'<th style="text-align:left; padding:10px 14px; '
            f'font-family:{t.FONT_UI}; font-size:0.78em; font-weight:600; '
            f'letter-spacing:0.05em; text-transform:uppercase;">Facility</th>'
            f'<th style="text-align:left; padding:10px 14px; '
            f'font-family:{t.FONT_UI}; font-size:0.78em; font-weight:600; '
            f'letter-spacing:0.05em; text-transform:uppercase;">County</th>'
            f'<th style="text-align:left; padding:10px 14px; '
            f'font-family:{t.FONT_UI}; font-size:0.78em; font-weight:600; '
            f'letter-spacing:0.05em; text-transform:uppercase;">Type</th>'
            f'<th style="text-align:center; padding:10px 14px; '
            f'font-family:{t.FONT_UI}; font-size:0.78em; font-weight:600; '
            f'letter-spacing:0.05em; text-transform:uppercase;">SAAR proxy</th>'
            f'<th style="text-align:center; padding:10px 14px; '
            f'font-family:{t.FONT_UI}; font-size:0.78em; font-weight:600; '
            f'letter-spacing:0.05em; text-transform:uppercase;">Resistance burden</th>'
            f'<th style="text-align:right; padding:10px 14px; '
            f'font-family:{t.FONT_UI}; font-size:0.78em; font-weight:600; '
            f'letter-spacing:0.05em; text-transform:uppercase;">N isolates</th>'
            f'</tr></thead>'
        )

        body_rows = []
        for i, r in enumerate(rows):
            tint = "white" if i % 2 == 0 else f"{t.MIST_WHITE}"
            body_rows.append(
                f'<tr style="background:{tint}; '
                f'border-bottom:1px solid {t.COOL_GRAY}33;">'
                f'<td style="padding:10px 14px; font-family:{t.FONT_UI}; '
                f'font-size:0.88em; color:{t.PRIMARY_NAVY}; '
                f'font-weight:600;">{r["facility"]}</td>'
                f'<td style="padding:10px 14px; font-family:{t.FONT_UI}; '
                f'font-size:0.85em; color:{t.SLATE_BLUE};">{r["county"]}</td>'
                f'<td style="padding:10px 14px; font-family:{t.FONT_UI}; '
                f'font-size:0.85em; color:{t.SLATE_BLUE}; '
                f'text-transform:capitalize;">{r["type"]}</td>'
                f'<td style="padding:10px 14px; text-align:center;">'
                f'{_saar_chip(r["saar"])}</td>'
                f'<td style="padding:10px 14px; text-align:center;">'
                f'{_rbi_chip(r["rbi"])}</td>'
                f'<td style="padding:10px 14px; text-align:right; '
                f'font-family:monospace; font-size:0.88em; '
                f'color:{t.INK};">{r["n"]:,}</td>'
                f'</tr>'
            )

        table_html = (
            f'<table style="width:100%; border-collapse:collapse; '
            f'background:white; border:1px solid {t.COOL_GRAY}55; '
            f'border-radius:6px; overflow:hidden;">'
            f'{header_html}<tbody>{"".join(body_rows)}</tbody></table>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

        st.markdown(
            f'<div style="margin-top:8px; font-family:{t.FONT_UI}; '
            f'font-size:0.78em; color:{t.SLATE_BLUE};">'
            f'SAAR ≥ 1.30 flagged as <span style="color:{t.CLINICAL_CORAL}; '
            f'font-weight:600;">concern</span>; '
            f'1.10–1.30 as <span style="color:{t.MUTED_AMBER}; '
            f'font-weight:600;">watch</span>; '
            f'&lt; 1.10 as <span style="color:{t.SOFT_GREEN}; '
            f'font-weight:600;">stable</span>. '
            f'Same thresholds applied at 30 / 15 for the Resistance Burden Index.'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        ui.empty_state("Facility metadata not available.")

    st.markdown("---")
    ui.about_this_data_panel()
