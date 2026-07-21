"""Data Engine tab — shows the ingestion/dedup/geography pipeline that sits
underneath TRACE, not just the clinical-facing surfaces.

Two things live here, deliberately kept separate:
  1. A summary of what the pipeline proved, using the REAL numbers from
     running it (against a real de-identified microbiology export, a real
     hospital antibiogram template, and a purpose-built synthetic dataset
     engineered to exercise every geography outcome). Static content —
     the full multi-stage pipeline (parsing a ~1M-row file, SQLite writes)
     is not something to run inside a shared Streamlit Cloud container on
     every page load.
  2. One genuinely live piece: the adaptive-geography resolver run in real
     time against the dataset already bundled with this app. Cheap enough
     to be safe (458K rows, already cached), and it's the same resolution
     logic now powering the Weather Map and EHR Sandbox tabs.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import data_loader as dl
from .. import geography as geo
from .. import components as ui
from .. import theme as t


def render(filters: dict) -> None:
    ui.tab_header(
        "TRACE Data Engine",
        "How TRACE turns a lab's raw data into governed, geography-aware resistance intelligence.",
    )

    st.caption(
        "This tab shows the pipeline itself, not clinical output. Everything below reflects "
        "code that runs today — none of it is a mockup — but it has not yet been run against "
        "MAKO's or MicroCulture's own data. See “What we still need from a lab partner” below."
    )

    _pipeline_summary()
    st.divider()
    _live_geography_resolver()
    st.divider()
    _lab_gaps()


def _pipeline_summary() -> None:
    ui.section_header(
        "What the pipeline proved",
        "Four stages, wired together, tested against real file shapes.",
    )
    cols = st.columns(4)
    with cols[0]:
        ui.metric_pill(
            "Format translator", "2 formats",
            sub="Row-per-observation lab export + wide hospital antibiogram matrix — both real files, both produce one standard schema.",
        )
    with cols[1]:
        ui.metric_pill(
            "Duplicate-patient filter", "9 / 9",
            sub="Hand-built test cases with known right answers, including a repeat-within-window and a >365-day re-count. All passed.",
        )
    with cols[2]:
        ui.metric_pill(
            "Adaptive geography", "92% / 8%",
            sub="Across 1,634 real ZIP × organism × drug queries: 92% reliable at ZIP level, 8% correctly zoomed out to county.",
        )
    with cols[3]:
        ui.metric_pill(
            "Curated store", "3 batches",
            sub="Loaded into one SQLite store; reopened fresh afterward and answered live queries with zero source files touched.",
        )


def _live_geography_resolver() -> None:
    ui.section_header(
        "Try the adaptive-geography engine live",
        "Runs in real time against this app's own bundled dataset — pick a ZIP, organism, and drug.",
    )

    df = dl.load_test_results()
    zip_map = dl.load_zip_county_map()

    col1, col2, col3, col4 = st.columns([1.2, 1.6, 1.6, 0.8])
    with col1:
        zip_options = sorted(zip_map["zip"].unique())
        default_zip = "84782" if "84782" in zip_options else zip_options[0]
        zip_code = st.selectbox("ZIP", zip_options, index=zip_options.index(default_zip), key="de_zip")
    with col2:
        organisms = sorted(df["organism"].dropna().unique())
        default_org = "Escherichia coli" if "Escherichia coli" in organisms else organisms[0]
        organism = st.selectbox("Organism", organisms, index=organisms.index(default_org), key="de_organism")
    with col3:
        drug_options = sorted(df.loc[df["organism"] == organism, "drug"].dropna().unique())
        drug = st.selectbox("Drug", drug_options, key="de_drug") if drug_options else None
    with col4:
        st.markdown("<div style='height: 1.9em;'></div>", unsafe_allow_html=True)
        run = st.button("Resolve", type="primary", use_container_width=True)

    if not run or drug is None:
        return

    result = geo.resolve_geography(df, zip_code, organism, drug)

    tone = "stable" if result.stable else "watch"
    icon = "✓" if result.stable else "⚠"
    level_display = result.resolved_level.replace("_", " ").title()
    ui.branded_alert(
        f"Resolved at {level_display}: {result.resolved_label}",
        (
            f"<strong>{result.n_isolates} isolates</strong>"
            + (f" · <strong>{result.pct_susceptible}% susceptible</strong>"
               f" (95% CI {result.ci_lo}–{result.ci_hi})" if result.pct_susceptible is not None else "")
            + f"<br/>Path tried: {' → '.join(l.replace('_', ' ').title() for l in result.levels_tried)}"
        ),
        tone=tone, icon=icon,
    )
    if result.notes:
        st.caption(" · ".join(result.notes))


def _lab_gaps() -> None:
    ui.section_header(
        "What we still need from a lab partner",
        "Found by running the pipeline against a real (non-MAKO) de-identified microbiology export.",
    )
    ui.branded_alert(
        "Two fields block first-isolate dedup and geography today",
        (
            "Running the ingestion pipeline against a real row-per-observation lab export "
            "surfaced two concrete gaps, not hypothetical ones: <strong>no reliably-filled "
            "specimen collection date</strong>, and <strong>no ordering-location geography field</strong>. "
            "Everything downstream — duplicate-patient filtering and adaptive geography — depends on "
            "at least one of these being present. This is now the lead discovery question for the "
            "MAKO / MicroCulture conversation."
        ),
        tone="watch", icon="⚠",
    )
