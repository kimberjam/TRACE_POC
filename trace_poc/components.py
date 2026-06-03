"""Reusable UI components for TRACE.

All visual decisions defer to trace_poc.theme — never hardcode colors here.

Style attribute convention:
  All inline style attributes use double quotes around the value, because
  font-family stacks contain embedded single quotes (e.g., 'Aptos', 'Inter').
  Outer f-string delimiters are single-quoted.
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

from . import data_loader as dl
from . import theme as t


# ----- Section helpers -----

def section_header(title: str, subtext: Optional[str] = None) -> None:
    st.markdown(
        f'<div style="font-family: {t.FONT_HEADING}; '
        f'font-size: 1.05em; font-weight: 600; color: {t.PRIMARY_NAVY}; '
        f'margin-top: 0.5rem; margin-bottom: 0.25rem;">{title}</div>',
        unsafe_allow_html=True,
    )
    if subtext:
        st.caption(subtext)


def tab_header(title: str, subtext: str) -> None:
    st.markdown(
        f'<div style="font-family: {t.FONT_HEADING}; '
        f'font-size: 1.85em; font-weight: 600; color: {t.PRIMARY_NAVY}; '
        f'letter-spacing: -0.015em;">{title}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-family: {t.FONT_UI}; font-size: 0.95em; '
        f'color: {t.SLATE_BLUE}; margin-top: 0.25rem; '
        f'margin-bottom: 0.5rem;">{subtext}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<hr style="margin: 0.5rem 0 1rem 0; '
        f'border-color: {t.COOL_GRAY}55;"/>',
        unsafe_allow_html=True,
    )


# ----- KPI card -----

def kpi_card(
    label: str,
    value: str,
    sublabel: Optional[str] = None,
    delta: Optional[str] = None,
    help_text: Optional[str] = None,
) -> None:
    st.metric(label=label, value=value, delta=delta, help=help_text)
    if sublabel:
        st.markdown(
            f'<div style="font-family: {t.FONT_UI}; font-size: 0.78em; '
            f'color: {t.SLATE_BLUE}; margin-top: -0.5rem;">{sublabel}</div>',
            unsafe_allow_html=True,
        )


# ----- Evidence chip -----

def _chip_html(label: str, tone: str = "neutral") -> str:
    palettes = {
        "neutral": (f"{t.PRIMARY_NAVY}11", t.COOL_GRAY, t.SLATE_BLUE),
        "concern": (f"{t.CLINICAL_CORAL}1A", t.CLINICAL_CORAL, t.CLINICAL_CORAL),
        "watch":   (f"{t.MUTED_AMBER}1A", t.MUTED_AMBER, "#8A5F0F"),
        "stable":  (f"{t.SOFT_GREEN}1A", t.SOFT_GREEN, "#2E6A52"),
    }
    bg, border, fg = palettes.get(tone, palettes["neutral"])
    return (
        f'<span style="display:inline-block; padding:2px 9px; '
        f'margin:2px 4px 2px 0; background:{bg}; '
        f'border:1px solid {border}66; border-radius:11px; '
        f'font-family:{t.FONT_UI}; font-size:0.76em; color:{fg}; '
        f'font-weight:500; letter-spacing:0.01em;">{label}</span>'
    )


def evidence_chip(label: str, tone: str = "neutral") -> str:
    return _chip_html(label, tone)


def evidence_strip(
    facility: Optional[str] = None,
    period: Optional[str] = None,
    n: Optional[int] = None,
    qa_status: Optional[str] = None,
    county: Optional[str] = None,
) -> None:
    chips = []
    if facility:
        chips.append(_chip_html(f"Facility: {facility}"))
    if county:
        chips.append(_chip_html(f"County: {county}"))
    if period:
        chips.append(_chip_html(f"Period: {period}"))
    if n is not None:
        chips.append(_chip_html(f"N = {n:,}"))
    if qa_status:
        chips.append(_chip_html(f"QA: {qa_status}", tone="stable"))
    if chips:
        st.markdown("".join(chips), unsafe_allow_html=True)


# ----- Empty state -----

def empty_state(
    title: str = "No data for the current selection",
    suggestion: str = "Try a different organism, a wider date range, or another county.",
) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div style="font-family: {t.FONT_UI}; font-weight: 600; '
            f'color: {t.PRIMARY_NAVY};">{title}</div>',
            unsafe_allow_html=True,
        )
        st.caption(suggestion)


# ----- About-this-data panel -----

def about_this_data_panel() -> None:
    with st.expander("About this data — provenance & calibration", expanded=False):
        st.markdown(
            "TRACE is currently running on a **fully synthetic dataset** built "
            "specifically for the POC. No real patient data, no real facility "
            "names. The data is **statistically calibrated** to:"
        )
        for src in dl.DATASET_SOURCES:
            st.markdown(f"- {src}")
        st.markdown(
            f"**Coverage:** {', '.join(dl.DATASET_COUNTIES)} (Utah). "
            f"**Period:** {dl.DATASET_PERIOD}. "
            f"**Reproducible** from seed `{dl.DATASET_SEED}`."
        )
        st.markdown(
            "When TRACE is connected to a real participating facility's "
            "antibiogram pipeline, every data point displayed will carry a "
            "provenance chip (facility, period, N, QA status) the same way "
            "synthetic data does today."
        )


# ----- Guideline scenario card -----

def guideline_card(scenario) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div style="font-family: {t.FONT_HEADING}; '
            f'font-size: 1.05em; font-weight: 600; color: {t.PRIMARY_NAVY}; '
            f'margin-bottom: 0.5rem;">{scenario.display_name}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            _chip_html(scenario.evidence_grade, tone="neutral"),
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div style="font-family: {t.FONT_UI}; font-weight: 600; '
            f'color: {t.PRIMARY_NAVY}; margin-top: 0.75rem; '
            f'margin-bottom: 0.25rem;">First-line empiric therapy</div>',
            unsafe_allow_html=True,
        )
        for line in scenario.first_line:
            st.markdown(f"- {line}")

        if scenario.alternatives:
            st.markdown(
                f'<div style="font-family: {t.FONT_UI}; font-weight: 600; '
                f'color: {t.PRIMARY_NAVY}; margin-top: 0.5rem; '
                f'margin-bottom: 0.25rem;">Alternatives</div>',
                unsafe_allow_html=True,
            )
            for alt in scenario.alternatives:
                st.markdown(f"- {alt}")

        st.markdown(
            f'<div style="font-family: {t.FONT_UI}; margin-top: 0.5rem;">'
            f'<span style="font-weight: 600; color: {t.PRIMARY_NAVY};">'
            f'Duration:</span> {scenario.duration}</div>',
            unsafe_allow_html=True,
        )

        if scenario.contraindications:
            st.markdown(
                f'<div style="font-family: {t.FONT_UI}; font-weight: 600; '
                f'color: {t.PRIMARY_NAVY}; margin-top: 0.5rem; '
                f'margin-bottom: 0.25rem;">Contraindications & cautions</div>',
                unsafe_allow_html=True,
            )
            for c in scenario.contraindications:
                st.markdown(f"- {c}")

        if scenario.stewardship_notes:
            st.markdown(
                f'<div style="font-family: {t.FONT_UI}; font-weight: 600; '
                f'color: {t.PRIMARY_NAVY}; margin-top: 0.5rem; '
                f'margin-bottom: 0.25rem;">Stewardship notes</div>',
                unsafe_allow_html=True,
            )
            for n in scenario.stewardship_notes:
                st.markdown(f"- {n}")

        st.caption(f"Source: {scenario.source}")
        if scenario.source_url:
            st.caption(f"[{scenario.source_url}]({scenario.source_url})")


# ----- Coming-soon stub -----

def coming_next_phase(message: str = "This view is part of the Phase-2 build.") -> None:
    with st.container(border=True):
        st.markdown(
            f'<div style="font-family: {t.FONT_UI}; font-weight: 600; '
            f'color: {t.PRIMARY_NAVY};">Coming in next phase</div>',
            unsafe_allow_html=True,
        )
        st.caption(message)


# ----- DEMO DATA banner -----

def demo_data_banner() -> None:
    """Full-width informational banner indicating the demo nature of the data.

    Uses Soft Blue (neutral information per brand) — does not encroach on
    warm colors which are reserved for clinical concern.
    """
    st.markdown(
        f'<div style="background: {t.SOFT_BLUE}1A; '
        f'border-top: 1px solid {t.SOFT_BLUE}66; '
        f'border-bottom: 1px solid {t.SOFT_BLUE}66; '
        f'padding: 8px 24px; margin: -1rem -1rem 1rem -1rem; '
        f'font-family: {t.FONT_UI}; font-size: 0.85em; '
        f'color: {t.SLATE_BLUE}; text-align: center; letter-spacing: 0.02em;">'
        f'<strong style="color: {t.PRIMARY_NAVY}; '
        f'letter-spacing: 0.08em;">DEMO DATA</strong>'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;Illustrative only'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;Not live clinical data'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;Values are synthetic, geographically plausible'
        f'</div>',
        unsafe_allow_html=True,
    )


# ----- View in EHR button -----

def view_in_ehr_button(key: str = "view_in_ehr") -> bool:
    """Teal-accented CTA. Returns True if clicked.

    Caller is responsible for handling the navigation (typically by setting
    st.session_state.mode = 'ehr_sandbox' and rerunning).
    """
    return st.button(
        "View in EHR →",
        key=key,
        type="primary",
        help="Open the simulated EHR sandbox to see how TRACE surfaces in a "
             "clinician's chart workflow via CDS Hooks.",
    )
