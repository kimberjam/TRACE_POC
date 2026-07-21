"""About & Architecture tab.

The product story + pipeline + six design principles, derived directly
from the HTML investor mockup. This is the read-this-to-understand-TRACE
surface for due-diligence and partner conversations.
"""
from __future__ import annotations

import streamlit as st

from .. import components as ui
from .. import theme as t


def _hero() -> None:
    st.markdown(
        f'<div style="background: {t.PRIMARY_NAVY}; color: white; '
        f'border-radius: 8px; padding: 28px 32px; '
        f'font-family: {t.FONT_UI}; box-shadow: 0 1px 4px rgba(7,26,61,0.1);">'
        f'<div style="font-family: {t.FONT_HEADING}; font-size: 1.8em; '
        f'font-weight: 600; color: white; line-height: 1.15; '
        f'letter-spacing: -0.015em;">'
        f'Turning compliance '
        f'<span style="color: {t.TRACE_TEAL};">into intelligence.</span></div>'
        f'<p style="color: #B7C4CE; font-size: 0.95em; line-height: 1.55; '
        f'margin-top: 14px; max-width: 880px;">'
        f'The 2024 CMS NHSN mandate requires hospitals billing Medicare '
        f'to report antibiotic use and resistance data. Today that data '
        f'is buried in state and federal silos and returned to clinicians, '
        f'if at all, as a blurred annual average. TRACE ingests the same '
        f'data hospitals are already generating, then converts it into '
        f'continuously updated, ZIP-code-level resistance intelligence — '
        f'delivered as role-specific web dashboards and, for '
        f'EHR-integrated environments, CDS Hooks cards surfaced '
        f'at the point of care.'
        f'</p>'

        # Pipeline
        f'<div style="display: grid; '
        f'grid-template-columns: 1fr auto 1fr auto 1fr; gap: 14px; '
        f'align-items: stretch; margin-top: 22px;">'
        + _pipeline_step("01 · Ingest",
                         "AU/AR CDA XML, antibiograms, lab feeds",
                         "From hospital NHSN submissions, institutional "
                         "antibiograms, and HL7/FHIR microbiology streams. "
                         "Ingest is automated and incremental.")
        + _arrow()
        + _pipeline_step("02 · Normalize",
                         "Harmonize to a FHIR-native dataset",
                         "Vocabulary mapping (SNOMED / LOINC / RxNorm), "
                         "organism and antibiotic canonicalization, QA "
                         "gates, governance-first filtering before "
                         "analytics run.")
        + _arrow()
        + _pipeline_step("03 · Insight",
                         "ZIP-level views + EHR-native cards",
                         "Role-specific dashboards for clinicians, "
                         "stewardship committees, hospital ops, and "
                         "public health — plus CDS Hooks cards surfaceable "
                         "inside the EHR at order-select.")
        + f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _pipeline_step(num: str, title: str, desc: str) -> str:
    return (
        f'<div style="background: rgba(255,255,255,0.06); '
        f'border: 1px solid rgba(79,183,178,0.25); '
        f'border-radius: 6px; padding: 14px 16px;">'
        f'<div style="font-family: {t.FONT_UI}; font-size: 0.72em; '
        f'color: {t.TRACE_TEAL}; letter-spacing: 0.08em; '
        f'font-weight: 600; text-transform: uppercase;">{num}</div>'
        f'<div style="font-family: {t.FONT_HEADING}; color: white; '
        f'font-weight: 600; font-size: 0.95em; margin: 6px 0;">{title}</div>'
        f'<div style="color: #B7C4CE; font-size: 0.78em; line-height: 1.5;">'
        f'{desc}</div>'
        f'</div>'
    )


def _arrow() -> str:
    return (
        f'<div style="display: flex; align-items: center; '
        f'justify-content: center; color: {t.TRACE_TEAL}; '
        f'font-size: 1.4em; font-weight: 600;">→</div>'
    )


PRINCIPLES = [
    {
        "n": 1, "title": "Descriptive, not prescriptive",
        "body": (
            "TRACE is <strong>not a clinical decision support tool</strong>; "
            "it is informational software that displays descriptive "
            "resistance context per current FDA guidance. It surfaces "
            "population-level context. It does not select, rank, or "
            "recommend therapies for individual patients. Every view "
            "reinforces this boundary in both language and framing. "
            "<em>&ldquo;CDS Hooks&rdquo; refers to the HL7 interoperability "
            "standard for surfacing information inside an EHR — distinct from "
            "&ldquo;clinical decision support&rdquo; as a regulatory device "
            "category. TRACE uses the former to display context; it is not "
            "the latter.</em>"
        ),
        "tags": None,
    },
    {
        "n": 2, "title": "Governance before analytics",
        "body": (
            "Data quality and participation rules are applied as a hard "
            "gate before any slicing or aggregation. Facility coverage, "
            "approval status, and minimum-isolate thresholds run first; "
            "the dashboard cannot bypass them. Small-cell suppression "
            "(default n &lt; 30) protects patient privacy and prevents "
            "overinterpretation."
        ),
        "tags": None,
    },
    {
        "n": 3, "title": "Provenance is transparent",
        "body": (
            "Every percentage is traceable to its contributing facilities, "
            "time window, and isolate counts. Empty tables are an honest "
            "signal — the system surfaces when local evidence is "
            "insufficient rather than interpolating or borrowing from "
            "state averages."
        ),
        "tags": [
            "NHSN AU/AR", "CDA R1/R6", "HL7 FHIR R4", "SNOMED CT",
            "LOINC", "RxNorm", "SMART on FHIR", "CDS Hooks 1.1",
        ],
    },
    {
        "n": 4, "title": "Built for the data flywheel",
        "body": (
            "Every new hospital that joins deepens the longitudinal dataset "
            "for its region. A competitor who builds a dashboard tomorrow "
            "cannot replicate the cross-institution history required to "
            "predict where resistance is shifting next. The moat compounds: "
            "more hospitals → higher regional density → better weather-map "
            "resolution → higher product value."
        ),
        "tags": None,
    },
    {
        "n": 5, "title": "Dual-market by design",
        "body": (
            "Healthcare delivery (hospitals, systems, ACOs) is the revenue "
            "engine, driven by CMS mandates and the $4.6B annual MDR cost "
            "burden. Public health (VA, DoD, state and local agencies) is "
            "the scale engine, driven by surveillance interoperability "
            "needs. Both sets of customers are already mandated to report "
            "— TRACE makes that reporting valuable to them in return."
        ),
        "tags": None,
    },
    {
        "n": 6, "title": "Scalable pricing that tracks value",
        "body": (
            "Three-phase commercialization: institutional SaaS ($40–60K "
            "flat by bed count) for predictable land-and-expand, "
            "shared-savings contracts capturing ~30% of documented "
            "antibiotic-spend and length-of-stay reductions, and "
            "predictive AI premium add-ons for forecasting and "
            "spatial modeling."
        ),
        "tags": None,
    },
]


def _principle_card(p: dict) -> None:
    tags_html = ""
    if p["tags"]:
        tag_spans = "".join(
            f'<span style="display: inline-block; padding: 2px 9px; '
            f'margin: 3px 4px 0 0; background: {t.TRACE_TEAL}1A; '
            f'border: 1px solid {t.TRACE_TEAL}55; border-radius: 11px; '
            f'font-family: monospace; font-size: 0.72em; '
            f'color: {t.PRIMARY_NAVY}; font-weight: 500;">{tag}</span>'
            for tag in p["tags"]
        )
        tags_html = f'<div style="margin-top: 10px;">{tag_spans}</div>'

    st.markdown(
        f'<div style="background: white; '
        f'border: 1px solid {t.COOL_GRAY}77; border-radius: 8px; '
        f'padding: 16px 18px; height: 100%; font-family: {t.FONT_UI}; '
        f'min-height: 180px;">'
        f'<div style="font-family: {t.FONT_HEADING}; font-weight: 600; '
        f'color: {t.PRIMARY_NAVY}; font-size: 1em; '
        f'display: flex; align-items: center; gap: 10px;">'
        f'<span style="background: {t.TRACE_TEAL}; color: white; '
        f'width: 22px; height: 22px; border-radius: 50%; '
        f'display: inline-flex; align-items: center; '
        f'justify-content: center; font-size: 0.78em;">{p["n"]}</span>'
        f'{p["title"]}'
        f'</div>'
        f'<p style="font-size: 0.85em; color: {t.INK}; '
        f'line-height: 1.5; margin-top: 8px; margin-bottom: 0;">'
        f'{p["body"]}</p>'
        f'{tags_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _principles_grid() -> None:
    st.markdown("")
    st.markdown(
        f'<div style="font-family: {t.FONT_HEADING}; font-weight: 600; '
        f'color: {t.PRIMARY_NAVY}; font-size: 1.15em; '
        f'margin: 1rem 0 0.5rem;">Six design principles</div>',
        unsafe_allow_html=True,
    )
    # Three across, two rows
    row1 = st.columns(3)
    for col, p in zip(row1, PRINCIPLES[:3]):
        with col:
            _principle_card(p)
    st.markdown("")
    row2 = st.columns(3)
    for col, p in zip(row2, PRINCIPLES[3:]):
        with col:
            _principle_card(p)


def _footer_note() -> None:
    st.markdown("")
    st.markdown(
        f'<div style="background: {t.MIST_WHITE}; '
        f'border-left: 3px solid {t.SOFT_BLUE}; '
        f'padding: 12px 16px; border-radius: 4px; '
        f'font-family: {t.FONT_UI}; font-size: 0.82em; '
        f'color: {t.SLATE_BLUE}; line-height: 1.55; margin-top: 1rem;">'
        f'<strong style="color: {t.PRIMARY_NAVY};">On this demo.</strong> '
        f'All data shown in this interface is synthetic and illustrative. '
        f'ZIP-level susceptibility values are generated to be geographically '
        f'plausible using published baselines (e.g., E. coli outpatient '
        f'urinary isolates per CDC AR&amp;PW reporting bands) with stochastic '
        f'per-ZIP variation. The map, trend chart, hospital benchmarks, and '
        f'hotspot signals are for visual demonstration of the TRACE value '
        f'proposition only. The underlying production system uses a '
        f'CSV / parquet aggregation pipeline and a separate governance layer '
        f'(data-quality gates, participation rules, small-cell suppression) '
        f'that runs before any analytics are surfaced.'
        f'</div>',
        unsafe_allow_html=True,
    )


def render(filters: dict) -> None:
    _hero()
    _principles_grid()
    _footer_note()
