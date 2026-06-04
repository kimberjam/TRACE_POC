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


# ----- Branded clinical alert -----

def branded_alert(
    title: str,
    body: str,
    tone: str = "watch",
    icon: str = "⚠",
) -> None:
    """TRACE-styled clinical alert card with colored left border and icon.

    Tones:
      watch    — Muted Amber  (stewardship concern, trend to watch)
      concern  — Clinical Coral (high concern, worsening)
      info     — Soft Blue (neutral information)
      stable   — Soft Green (success, validated)
    """
    palettes = {
        "watch":   (t.MUTED_AMBER, "#FFFBED"),
        "concern": (t.CLINICAL_CORAL, "#FFF5F2"),
        "info":    (t.SOFT_BLUE, "#F4F8FC"),
        "stable":  (t.SOFT_GREEN, "#F0F8F3"),
    }
    border_color, bg_color = palettes.get(tone, palettes["watch"])
    st.markdown(
        f'<div style="background: {bg_color}; '
        f'border-left: 4px solid {border_color}; '
        f'padding: 10px 14px; border-radius: 4px; '
        f'margin: 4px 0 8px 0; font-family: {t.FONT_UI};">'
        f'<div style="display: flex; gap: 10px; align-items: flex-start;">'
        f'<div style="color: {border_color}; font-size: 1.1em; '
        f'flex-shrink: 0; line-height: 1.3;">{icon}</div>'
        f'<div style="flex: 1;">'
        f'<div style="font-weight: 600; color: {t.PRIMARY_NAVY}; '
        f'font-size: 0.9em;">{title}</div>'
        f'<div style="color: {t.INK}; font-size: 0.85em; '
        f'margin-top: 4px; line-height: 1.45;">{body}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )


# ----- Hero stat card (TRACE-card pattern) -----

def hero_stat_card(
    brand_title: str,
    meta_text: str,
    stat_label: str,
    stat_value: str,
    stat_unit: str = "",
    sub_text: str = "",
    chips: Optional[list] = None,
    comparison_cells: Optional[list] = None,
    live: bool = True,
) -> None:
    """Big-number TRACE card: navy header, meta row, hero stat, chip row,
    optional comparison-strip footer.

    Args:
        brand_title: text in the navy header (e.g., "TRACE · Point of Care")
        meta_text: secondary context line (HTML allowed)
        stat_label: small uppercase label above the big number
        stat_value: the headline number/text
        stat_unit: a small suffix (e.g., "%", "/1k adm")
        sub_text: line beneath the stat — CI, baseline, etc.
        chips: list of (label, tone) tuples — rendered as evidence chips
        comparison_cells: list of (label, value, sub) — rendered as a 3-col
                          comparison strip in the footer
        live: whether to show the green "LIVE" indicator in the header
    """
    chips_html = ""
    if chips:
        chips_html = "".join(_chip_html(label, tone) for label, tone in chips)

    live_html = ""
    if live:
        live_html = (
            f'<div style="font-size: 0.75em; color: {t.SOFT_GREEN}; '
            f'display: flex; align-items: center; gap: 6px;">'
            f'<span style="width: 7px; height: 7px; background: '
            f'{t.SOFT_GREEN}; border-radius: 50%; display: inline-block;">'
            f'</span>LIVE</div>'
        )

    comparison_html = ""
    if comparison_cells:
        cells = "".join(
            f'<div>'
            f'<div style="font-size: 0.7em; color: {t.SLATE_BLUE}; '
            f'letter-spacing: 0.05em; font-weight: 600; '
            f'text-transform: uppercase;">{lbl}</div>'
            f'<div style="font-weight: 600; color: {t.PRIMARY_NAVY}; '
            f'font-size: 0.95em; margin-top: 2px;">{val}</div>'
            f'<div style="font-size: 0.75em; color: {t.SLATE_BLUE}; '
            f'margin-top: 2px;">{sub}</div>'
            f'</div>'
            for lbl, val, sub in comparison_cells
        )
        comparison_html = (
            f'<div style="background: {t.MIST_WHITE}; '
            f'border-top: 1px solid {t.COOL_GRAY}55; '
            f'padding: 12px 16px; display: grid; '
            f'grid-template-columns: repeat({len(comparison_cells)}, 1fr); '
            f'gap: 14px; font-family: {t.FONT_UI};">{cells}</div>'
        )

    chips_block = ""
    if chips_html:
        chips_block = (
            f'<div style="margin-top: 10px;">{chips_html}</div>'
        )

    st.markdown(
        f'<div style="background: white; border: 1px solid {t.COOL_GRAY}; '
        f'border-radius: 8px; overflow: hidden; margin-bottom: 0.5rem; '
        f'box-shadow: 0 1px 4px rgba(7,26,61,0.06);">'
        # Navy header
        f'<div style="background: {t.PRIMARY_NAVY}; color: white; '
        f'padding: 10px 16px; display: flex; justify-content: space-between; '
        f'align-items: center; font-family: {t.FONT_UI}; font-size: 0.92em;">'
        f'<div><strong style="letter-spacing: 0.02em;">{brand_title}</strong>'
        f'</div>{live_html}</div>'
        # Meta row
        f'<div style="background: {t.MIST_WHITE}; padding: 8px 16px; '
        f'border-bottom: 1px solid {t.COOL_GRAY}55; '
        f'font-family: {t.FONT_UI}; font-size: 0.82em; '
        f'color: {t.SLATE_BLUE};">{meta_text}</div>'
        # Body
        f'<div style="padding: 18px 16px;">'
        f'<div style="font-family: {t.FONT_UI}; font-size: 0.72em; '
        f'color: {t.SLATE_BLUE}; letter-spacing: 0.06em; '
        f'font-weight: 600; text-transform: uppercase;">{stat_label}</div>'
        f'<div style="font-family: {t.FONT_HEADING}; font-size: 3.0em; '
        f'font-weight: 700; color: {t.PRIMARY_NAVY}; line-height: 1; '
        f'margin: 4px 0;">{stat_value}'
        f'<span style="font-size: 0.36em; color: {t.SLATE_BLUE}; '
        f'font-weight: 600; margin-left: 2px;">{stat_unit}</span></div>'
        f'<div style="font-size: 0.88em; color: {t.INK}; line-height: 1.45;">'
        f'{sub_text}</div>'
        f'{chips_block}'
        f'</div>'
        f'{comparison_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ----- Compact KPI pill (used inside st.columns rows) -----

def metric_pill(
    label: str,
    value: str,
    sub: str = "",
    delta: str = "",
    delta_tone: str = "neutral",
) -> None:
    """Brand-aligned compact KPI card. Render inside an st.columns() block."""
    delta_palette = {
        "up_bad":     t.CLINICAL_CORAL,
        "down_bad":   t.CLINICAL_CORAL,
        "up_good":    t.SOFT_GREEN,
        "down_good":  t.SOFT_GREEN,
        "neutral":    t.SLATE_BLUE,
        "warn":       t.MUTED_AMBER,
    }
    delta_color = delta_palette.get(delta_tone, t.SLATE_BLUE)

    delta_html = ""
    if delta:
        delta_html = (
            f'<div style="font-size: 0.78em; color: {delta_color}; '
            f'font-weight: 600; margin-top: 4px;">{delta}</div>'
        )

    st.markdown(
        f'<div style="background: white; '
        f'border: 1px solid {t.COOL_GRAY}55; border-radius: 6px; '
        f'padding: 12px 14px; height: 100%; '
        f'font-family: {t.FONT_UI};">'
        f'<div style="font-size: 0.7em; color: {t.SLATE_BLUE}; '
        f'letter-spacing: 0.06em; font-weight: 600; '
        f'text-transform: uppercase;">{label}</div>'
        f'<div style="font-family: {t.FONT_HEADING}; font-size: 1.7em; '
        f'font-weight: 700; color: {t.PRIMARY_NAVY}; line-height: 1.1; '
        f'margin: 4px 0;">{value}</div>'
        f'<div style="font-size: 0.78em; color: {t.SLATE_BLUE}; '
        f'line-height: 1.35;">{sub}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


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
