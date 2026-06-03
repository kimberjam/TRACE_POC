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
            ("Cefazolin (if MSSA confirmed)", ["Oxacillin"]),
            ("Daptomycin (vanc alternative)", ["Linezolid"]),
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
            ("Fidaxomicin (preferred)", ["Linezolid"]),
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
        "Point of care",
        "Local susceptibility patterns and guideline-aligned empiric options "
        "for the patient in front of you. Descriptive context — not a "
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

    # ----- KPI ROW -----
    kpi_cols = st.columns(3)

    # Card 1: Empiric coverage of the FIRST listed option
    options_for_setting = (
        _EMPIRIC_OPTIONS.get(infection_site or "", {}).get(care_setting, [])
    )
    with kpi_cols[0]:
        if options_for_setting:
            label, drugs = options_for_setting[0]
            cov = m.empiric_coverage(df, organism, drugs)
            ui.kpi_card(
                "Empiric Coverage Score",
                f"{cov.pct_covered:.0f}%" if cov.pct_covered is not None else "—",
                sublabel=f"Estimated coverage if {label} chosen empirically",
                help_text=(
                    "Share of locally-isolated organisms that test susceptible "
                    "to at least one drug in the regimen. Higher is better."
                ),
            )
        else:
            ui.kpi_card("Empiric Coverage Score", "—",
                        sublabel="No mapping for this combination")

    # Card 2: Local susceptibility snapshot
    with kpi_cols[1]:
        sus_table = m.susceptibility_table(df, organism)
        if not sus_table.empty:
            top = sus_table.iloc[0]
            ui.kpi_card(
                "Local Susceptibility Snapshot",
                f"{top['drug']}",
                sublabel=(
                    f"{top['pct_susceptible']:.0f}% susceptible "
                    f"(N = {int(top['n_isolates'])})"
                ),
                help_text="Best-tested antibiotic for this organism in the "
                          "current filter scope.",
            )
        else:
            ui.kpi_card("Local Susceptibility Snapshot", "—",
                        sublabel="No isolates in current scope")

    # Card 3: Time to effective therapy (proxy)
    with kpi_cols[2]:
        ttr = m.time_to_result_hours(df)
        if ttr is not None:
            ui.kpi_card(
                "Time to Result (median)",
                f"{ttr:.1f} h",
                sublabel="Collection → susceptibility result",
                help_text=(
                    "Proxy for time-to-effective-therapy. Faster turnaround "
                    "means de-escalation can happen sooner."
                ),
            )
        else:
            ui.kpi_card("Time to Result", "—",
                        sublabel="No completed tests in scope")

    st.markdown("")

    # ----- MIDDLE ROW -----
    mid_left, mid_right = st.columns([2, 1])

    with mid_left:
        ui.section_header(
            "Empiric Therapy Explorer",
            "Ranked by local susceptibility. Information-only — does not "
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
        # Build alerts dynamically from the data
        alerts = _build_alerts(df, organism, care_setting)
        if alerts:
            for level, text in alerts:
                if level == "warn":
                    st.warning(text, icon="⚠️")
                else:
                    st.info(text, icon="ℹ️")
        else:
            st.caption("No alerts triggered for the current scope.")

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
                    f"Local E. coli ciprofloxacin resistance is {pct_r:.0f}% "
                    "— consider non-fluoroquinolone first-line for "
                    "uncomplicated infections.",
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
                    "in this scope — empiric MRSA coverage warranted.",
                ))

    # C. diff context
    if organism == "C. difficile":
        alerts.append((
            "info",
            "Discontinue precipitating antibiotics where clinically possible. "
            "Avoid metronidazole as first-line per 2021 IDSA/SHEA update.",
        ))

    # ICU broad-spectrum reminder
    if care_setting == "ICU":
        alerts.append((
            "info",
            "ICU empiric coverage tends toward broad-spectrum. Plan a "
            "de-escalation review at 48–72h based on culture results.",
        ))

    return alerts
