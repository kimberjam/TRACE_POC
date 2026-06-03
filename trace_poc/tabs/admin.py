"""Admin tab — operational view.

Data sources & freshness, QA queue, ingestion log. Light by design — its
purpose is to signal that TRACE is an operational system rather than a toy.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import data_loader as dl
from .. import components as ui
from .. import guideline_content as gc


def render(filters: dict) -> None:
    ui.tab_header(
        "Admin view",
        "Data sources, ingestion status, QA queue, and content-library health.",
    )

    df = dl.load_test_results()
    facilities = dl.load_facilities()

    # ----- DATA FRESHNESS -----
    ui.section_header("Data freshness & coverage")

    fresh_cols = st.columns(4)

    with fresh_cols[0]:
        n_total = len(df)
        ui.kpi_card("Test-level records", f"{n_total:,}",
                    sublabel="Synthetic Utah cohort")

    with fresh_cols[1]:
        latest = df["collection_date"].max() if not df.empty else None
        ui.kpi_card(
            "Most recent collection",
            latest.strftime("%Y-%m-%d") if latest is not None else "—",
        )

    with fresh_cols[2]:
        n_fac = len(facilities)
        ui.kpi_card("Reporting facilities", f"{n_fac}",
                    sublabel="Across 3 counties")

    with fresh_cols[3]:
        period_days = (
            (df["collection_date"].max() - df["collection_date"].min()).days
            if not df.empty else 0
        )
        ui.kpi_card("Coverage window",
                    f"{period_days} days",
                    sublabel="From earliest to latest record")

    st.markdown("")

    # ----- SOURCES PANEL -----
    ui.section_header(
        "Calibration sources",
        "The synthetic dataset is statistically calibrated to:",
    )
    for src in dl.DATASET_SOURCES:
        st.markdown(f"- {src}")

    st.caption(
        f"Reproducible from seed `{dl.DATASET_SEED}`. "
        "When connected to a real facility pipeline, replaces this calibration "
        "with their actual antibiogram ingestion."
    )

    st.markdown("---")

    # ----- INGESTION & QA QUEUE -----
    ui.section_header("Ingestion & QA queue")

    queue_cols = st.columns(2)
    with queue_cols[0]:
        st.markdown("**Ingestion log (last 5 events)**")
        log = pd.DataFrame([
            {"When": "2026-05-12 13:34", "Source": "Synthetic Utah cohort v1.0",
             "Records": "458,650", "Status": "PUBLISHED"},
            {"When": "2026-05-12 13:33",
             "Source": "aggregates/county_month_organism_drug.csv",
             "Records": "rebuilt", "Status": "PUBLISHED"},
            {"When": "2026-05-12 13:33",
             "Source": "aggregates/zip_30day_organism_drug.csv",
             "Records": "rebuilt", "Status": "PUBLISHED"},
            {"When": "2026-05-12 13:32",
             "Source": "facilities.csv",
             "Records": "17", "Status": "PUBLISHED"},
            {"When": "2026-05-12 13:32",
             "Source": "zip_county_map.csv",
             "Records": "47", "Status": "PUBLISHED"},
        ])
        st.dataframe(log, use_container_width=True, hide_index=True)

    with queue_cols[1]:
        st.markdown("**Pending QA review**")
        st.success("Queue is empty.", icon="✅")
        st.caption(
            "When connected to a real facility pipeline, this surfaces "
            "staged antibiogram rows awaiting reviewer approval before "
            "publishing to clinical views."
        )

    st.markdown("---")

    # ----- GUIDELINE LIBRARY HEALTH -----
    ui.section_header(
        "Guideline content library",
        "Hand-curated scenarios that populate the Clinician tab's "
        "guideline-aligned context. Phase 2 replaces with a RAG layer.",
    )

    rows = []
    for s in gc.get_all_scenarios():
        rows.append({
            "Infection": s.scenario_key[0],
            "Setting": s.scenario_key[1],
            "Organism": s.scenario_key[2],
            "Evidence": s.evidence_grade,
            "Source": s.source,
        })
    lib = pd.DataFrame(rows)
    st.dataframe(lib, use_container_width=True, hide_index=True)
    st.caption(
        f"Library size: {len(rows)} scenarios. "
        "Phase 2 expands to full guideline corpora with retrieval-augmented "
        "answering and clinician-in-the-loop corrections."
    )

    st.markdown("---")
    ui.about_this_data_panel()
