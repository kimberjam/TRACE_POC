"""Clinician tab — the hero experience.

Layout (per draw.io mockup in Dashboard/Code/TRACE_Clinician.txt):
  - Top: three KPI cards (Empiric Coverage Score, Local Susceptibility
    Snapshot, Time to Effective Therapy)
  - Middle-left: Empiric Therapy Explorer — ranked informational options
    based on local susceptibility + guideline-aligned content
  - Middle-right: Clinical Risk & Context — alerts, stewardship hints
  - Bottom: Recent Similar Cases & Outcomes (aggregated, de-identified)

Information-only. Not a prescribing tool.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from .. import data_loader as dl
from .. import metrics as m
from .. import guideline_content as gc
from .. import components as ui
from .. import theme as t


# Drugs we'll consider for empiric ranking, by infection site.
# (In Phase 2 this becomes guideline-driven.)
_EMPIRIC_OPTIONS = {
    "UTI": {
        "Outpatient": [
            ("Nitrofurantoin", ["Nitrofurantoin"]),
            ("TMP-SMX", ["TMP-SMX"]),
            ("Fosfomycin", ["Fosfomycin"]),
            ("Cephalexin", ["Cephalexin"]),
            ("Ciprofloxacin (reserve)", ["Ciprofloxacin"]),
        ],
        "Inpatient": [
            ("Ceftriaxone", ["Ceftriaxone"]),
            ("Pip-tazo", ["Piperacillin-Tazobactam"]),
            ("Ertapenem (if ESBL risk)", ["Ertapenem"]),
            ("Ciprofloxacin", ["Ciprofloxacin"]),
        ],
        "ED": [
            ("Ceftriaxone", ["Ceftriaxone"]),
            ("Pip-tazo", ["Piperacillin-Tazobactam"]),
            ("Ciprofloxacin", ["Ciprofloxacin"]),
        ],
    },
    "Pneumonia": {
        "Outpatient": [
            ("Amoxicillin", ["Amoxicillin"]),
            ("Amox-clav + macrolide", ["Amoxicillin-Clavulanate", "Azithromycin"]),
            ("Doxycycline", ["Doxycycline"]),
            ("Levofloxacin (reserve)", ["Levofloxacin"]),
        ],
        "Inpatient": [
            ("Ceftriaxone + azithromycin", ["Ceftriaxone", "Azithromycin"]),
            ("Levofloxacin", ["Levofloxacin"]),
            ("Pip-tazo + vanc (if MRSA/Ps risk)",
             ["Piperacillin-Tazobactam", "Vancomycin"]),
        ],
        "ICU": [
            ("Pip-tazo + vanc", ["Piperacillin-Tazobactam", "Vancomycin"]),
            ("Cefepime + vanc", ["Cefepime", "Vancomycin"]),
            ("Meropenem + vanc (ESBL risk)", ["Meropenem", "Vancomycin"]),
        ],
        "ED": [
            ("Ceftriaxone + azithromycin", ["Ceftriaxone", "Azithromycin"]),
            ("Levofloxacin", ["Levofloxacin"]),
        ],
    },
    "Bloodstream": {
        "Inpatient": [
            ("Vancomycin (empiric MRSA)", ["Vancomycin"]),
            ("Oxacillin — MSSA marker", ["Oxacillin"]),
            ("Linezolid (MRSA alternative)", ["Linezolid"]),
        ],
        "ICU": [
            ("Vancomycin + pip-tazo",
             ["Vancomycin", "Piperacillin-Tazobactam"]),
            ("Vancomycin + cefepime", ["Vancomycin", "Cefepime"]),
        ],
        "ED": [
            ("Vancomycin + ceftriaxone", ["Vancomycin", "Ceftriaxone"]),
        ],
    },
    "Pharyngitis": {
        "Outpatient": [
            ("Penicillin V", ["Penicillin"]),
            ("Amoxicillin", ["Amoxicillin"]),
            ("Cephalexin", ["Cephalexin"]),
            ("Azithromycin (allergy)", ["Azithromycin"]),
        ],
    },
    "GI": {
        "Inpatient": [
            ("Vancomycin PO", ["Vancomycin"]),
        ],
    },
}


# Map UI specimen choice → infection site (best-effort POC mapping)
_SPECIMEN_TO_INFECTION = {
    "Urine": "UTI",
    "Respiratory": "Pneumonia",
    "Blood": "Bloodstream",
    "Throat": "Pharyngitis",
    "Stool": "GI",
    "Wound": "Bloodstream",  # nearest match in scenario library
    "Nares": "Bloodstream",
}


def _infection_site(specimen: str) -> str | None:
    return _SPECIMEN_TO_INFECTION.get(specimen)


def render(filters: dict) -> None:
    ui.tab_header(
        "Clinical Context View",
        "Local susceptibility patterns and guideline-aligned context "
        "for the patient in front of you. Descriptive information — not a "
        "prescribing tool.",
    )

    # Load test-level data, scoped to current filters
    df = dl.load_test_results(
        counties=filters["counties"],
        encounter_settings=[filters["encounter_setting"]],
        specimen_types=[filters["specimen_type"]],
    )

    organism = filters["organism"]
    care_setting = filters["encounter_setting"]
    infection_site = _infection_site(filters["specimen_type"])

    # Active scenario summary banner + View in EHR CTA
    sb_cols = st.columns([4, 2, 1])
    with sb_cols[0]:
        scenario_label = filters.get("scenario_label")
        if scenario_label:
            st.markdown(f"**Active scenario:** {scenario_label}")
        else:
            st.markdown(
                f"**Active scenario:** {care_setting} · "
                f"{filters['specimen_type']} · {organism}"
            )
    with sb_cols[1]:
        ui.evidence_strip(
            county=", ".join(filters["counties"]) if filters["counties"] else "—",
            period="last 24 months",
            n=m.isolate_count(df, organism),
            qa_status="PUBLISHED",
        )
    with sb_cols[2]:
        if ui.view_in_ehr_button(key="clin_view_in_ehr_top"):
            st.session_state["mode"] = "ehr_sandbox"
            st.rerun()

    st.markdown("")

    # ----- HERO STAT CARD: empiric coverage of the first-listed option -----
    options_for_setting = (
        _EMPIRIC_OPTIONS.get(infection_site or "", {}).get(care_setting, [])
    )
    n_iso = m.isolate_count(df, organism)
    sus_table = m.susceptibility_table(df, organism)
    ttr = m.time_to_result_hours(df)

    if options_for_setting:
        top_label, top_drugs = options_for_setting[0]
        cov = m.empiric_coverage(df, organism, top_drugs)
        if cov.pct_covered is not None and cov.n_isolates > 0:
            ci_lo, ci_hi = m.wilson_ci(cov.pct_covered / 100.0, cov.n_isolates)
            chips = []
            if sus_table is not None and not sus_table.empty:
                top_drug = sus_table.iloc[0]
                chips.append((
                    f"Highest susceptibility: {top_drug['drug']} {top_drug['pct_susceptible']:.0f}%",
                    "stable" if top_drug['pct_susceptible'] >= 85 else "watch",
                ))
            if ttr is not None:
                chips.append((f"Median TAT {ttr:.1f}h", "neutral"))
            chips.append((f"N = {cov.n_isolates:,} isolates", "neutral"))

            ui.hero_stat_card(
                brand_title="TRACE · Clinical Context",
                meta_text=(
                    f"<strong style='color:{t.PRIMARY_NAVY};'>"
                    f"{organism} × {top_label}</strong>"
                    f"&nbsp;&nbsp;|&nbsp;&nbsp;{care_setting}"
                    f"&nbsp;·&nbsp;{', '.join(filters['counties'])}"
                    f"&nbsp;&nbsp;|&nbsp;&nbsp;trailing 24 months"
                ),
                stat_label=f"OBSERVED SUSCEPTIBILITY — {top_label}",
                stat_value=f"{cov.pct_covered:.0f}",
                stat_unit="%",
                sub_text=(
                    f"95% Wilson CI <strong>{ci_lo:.0f}–{ci_hi:.0f}%</strong>"
                    f" · informational only, not a recommendation"
                ),
                chips=chips,
                comparison_cells=[
                    (
                        "Highest observed susceptibility",
                        f"{sus_table.iloc[0]['drug']}"
                        if sus_table is not None and not sus_table.empty
                        else "—",
                        f"{sus_table.iloc[0]['pct_susceptible']:.0f}% susceptible (local)"
                        if sus_table is not None and not sus_table.empty
                        else "—",
                    ),
                    (
                        "Time to result",
                        f"{ttr:.1f} h" if ttr is not None else "—",
                        "collection → susceptibility",
                    ),
                    (
                        "Scope",
                        f"{n_iso:,}",
                        "isolates in current filter",
                    ),
                ],
                live=True,
            )
        else:
            ui.empty_state(
                "No isolates for the active scenario.",
                "Try widening the county selection or changing the encounter "
                "setting.",
            )
    else:
        ui.empty_state(
            "No empiric options mapped for this infection × setting yet.",
            "Phase 2 expands the curated empiric library beyond the current "
            "UTI / Pneumonia / Bloodstream / Pharyngitis / GI scope.",
        )

    st.markdown("")

    # ----- MIDDLE ROW -----
    mid_left, mid_right = st.columns([2, 1])

    with mid_left:
        ui.section_header(
            "Local Susceptibility Comparison",
            "Ranked by observed local susceptibility. Information-only — does not "
            "replace clinical judgment or institutional guidelines.",
        )
        if not options_for_setting:
            ui.empty_state(
                "No empiric options mapped for this infection × setting yet.",
                "The current POC covers the most common stewardship scenarios. "
                "Additional mappings expand in Phase 2.",
            )
        else:
            results: list[m.CoverageResult] = []
            for label, drugs in options_for_setting:
                cov = m.empiric_coverage(df, organism, drugs)
                cov_label = type(cov)(  # patch label for display
                    regimen_label=label,
                    drugs=drugs,
                    pct_covered=cov.pct_covered,
                    n_isolates=cov.n_isolates,
                )
                results.append(cov_label)

            # Sort: covered % desc, with None at bottom
            results.sort(
                key=lambda r: (r.pct_covered if r.pct_covered is not None else -1),
                reverse=True,
            )

            # Render as a sorted horizontal bar chart
            chart_df = pd.DataFrame([
                {
                    "Regimen": r.regimen_label,
                    "Coverage (%)": r.pct_covered if r.pct_covered is not None else 0,
                    "N isolates": r.n_isolates,
                }
                for r in results
            ])
            chart = (
                alt.Chart(chart_df)
                .mark_bar(color=t.TRACE_TEAL)
                .encode(
                    x=alt.X("Coverage (%):Q", scale=alt.Scale(domain=[0, 100])),
                    y=alt.Y("Regimen:N", sort="-x", title=None),
                    tooltip=["Regimen", "Coverage (%)", "N isolates"],
                )
                .properties(height=max(120, 36 * len(chart_df)))
            )
            text = chart.mark_text(
                align="left", baseline="middle", dx=4, color=t.INK,
            ).encode(text=alt.Text("Coverage (%):Q", format=".0f"))
            st.altair_chart(chart + text, use_container_width=True)

            ui.evidence_strip(
                county=", ".join(filters["counties"]),
                period="last 24 months",
                n=m.isolate_count(df, organism),
                qa_status="PUBLISHED",
            )

        # Susceptibility table (collapsed below the chart)
        with st.expander("Full local susceptibility table", expanded=False):
            sus_table = m.susceptibility_table(df, organism)
            if sus_table.empty:
                ui.empty_state()
            else:
                display = sus_table.rename(columns={
                    "drug": "Antibiotic",
                    "pct_susceptible": "% Susceptible",
                    "n_isolates": "N isolates",
                })
                st.dataframe(display, use_container_width=True, hide_index=True)

    with mid_right:
        ui.section_header("Guideline-aligned context")
        scenario = None
        if infection_site:
            scenario = gc.lookup_scenario(infection_site, care_setting, organism)
        if scenario:
            ui.guideline_card(scenario)
        else:
            ui.empty_state(
                "No matching guideline scenario in the curated library.",
                "Current scope: UTI, Pneumonia, Bloodstream, Pharyngitis, GI. "
                "Phase 2 expands to a full RAG-backed library.",
            )

        ui.section_header("Clinical risk & alerts")
        # Build alerts dynamically from the data, render as branded cards
        alerts = _build_alerts(df, organism, care_setting)
        if alerts:
            for level, text in alerts:
                # Split into title (first sentence) + body if there's a period
                parts = text.split(" — ", 1) if " — " in text else (
                    text.split(". ", 1)
                    if ". " in text else [text, ""]
                )
                title = parts[0]
                body = parts[1] if len(parts) > 1 else ""
                tone = "watch" if level == "warn" else "info"
                icon = "⚠" if level == "warn" else "ℹ"
                ui.branded_alert(title, body, tone=tone, icon=icon)
        else:
            ui.branded_alert(
                "No stewardship alerts triggered",
                "Local susceptibility patterns are within expected ranges "
                "for the current filter scope.",
                tone="stable",
                icon="✓",
            )

    st.markdown("---")

    # ----- BOTTOM: RECENT SIMILAR CASES -----
    ui.section_header(
        "Recent similar cases (aggregated, de-identified)",
        "Last 60 days of isolates matching the current filter scope.",
    )
    recent = df[df["collection_date"] >= df["collection_date"].max()
                - pd.Timedelta(days=60)]
    recent = recent[recent["organism"] == organism].copy()
    if recent.empty:
        ui.empty_state(
            "No recent isolates in scope.",
            "Try widening the date range or selecting another organism.",
        )
    else:
        summary = (
            recent.groupby(
                ["county", "encounter_setting", "patient_age_band"]
            )
            .agg(
                n_isolates=("test_id", "nunique"),
                drugs_tested=("drug", "nunique"),
            )
            .reset_index()
            .rename(columns={
                "county": "County",
                "encounter_setting": "Setting",
                "patient_age_band": "Age band",
                "n_isolates": "N isolates",
                "drugs_tested": "Drugs tested",
            })
            .sort_values("N isolates", ascending=False)
            .head(15)
        )
        st.dataframe(summary, use_container_width=True, hide_index=True)
        ui.evidence_strip(
            period="last 60 days",
            n=int(summary["N isolates"].sum()),
            qa_status="PUBLISHED",
        )

    st.markdown("---")
    ui.about_this_data_panel()


# ----- Helpers -----

def _build_alerts(df, organism: str, care_setting: str) -> list[tuple[str, str]]:
    """Generate context-aware alerts based on local data patterns."""
    alerts: list[tuple[str, str]] = []
    if df.empty:
        return alerts

    # Fluoroquinolone resistance alert for E. coli
    if organism == "Escherichia coli":
        cip = df[(df["organism"] == organism)
                 & (df["drug"] == "Ciprofloxacin")
                 & df["susceptibility"].isin(["S", "R"])]
        if not cip.empty:
            pct_r = 100.0 * (cip["susceptibility"] == "R").mean()
            if pct_r >= 20:
                alerts.append((
                    "warn",
                    f"Local E. coli ciprofloxacin resistance — {pct_r:.0f}% "
                    "of isolates in scope were resistant. Local fluoroquinolone "
                    "susceptibility is lower than national benchmarks for this area.",
                ))

    # MRSA prevalence alert
    if organism in ("Staphylococcus aureus", "MRSA"):
        mrsa = df[df["organism"] == "MRSA"]
        sa = df[df["organism"] == "Staphylococcus aureus"]
        n_mrsa = mrsa["test_id"].nunique()
        n_sa = sa["test_id"].nunique() + n_mrsa
        if n_sa:
            pct_mrsa = 100.0 * n_mrsa / n_sa
            if pct_mrsa >= 30:
                alerts.append((
                    "warn",
                    f"MRSA accounts for {pct_mrsa:.0f}% of S. aureus isolates "
                    "in this scope. Local MRSA prevalence is elevated relative "
                    "to national benchmarks for this setting.",
                ))

    # C. diff context
    if organism == "C. difficile":
        alerts.append((
            "info",
            "Discontinue precipitating antibiotics where clinically possible. "
            "Avoid metronidazole as first-line per 2021 IDSA/SHEA update.",
        ))

    # ICU broad-spectrum context
    if care_setting == "ICU":
        alerts.append((
            "info",
            "ICU isolates in scope tend toward broader-spectrum agents. "
            "Local susceptibility patterns are shown for the ICU encounter "
            "setting based on available data.",
        ))

    return alerts
