"""Today vs TRACE tab — investor-pitch comparison view.

Shows the gap between what prescribers actually see today (state DOH PDF
antibiogram, 12–18 months old, statewide aggregate) and what TRACE delivers
(continuously updated, ZIP-level intelligence at the moment of decision).

Layout:
  - Hero intro with pair pill
  - Side-by-side: simulated DOH PDF (left) vs TRACE live card (right)
  - 5-cell contrast strip: Granularity · Recency · Statistical depth ·
    Delivery · Action
  - Closing CTA: "The gap is the opportunity"
"""
from __future__ import annotations

import streamlit as st

from .. import components as ui
from .. import theme as t


# ----- Scenario → comparison-example mapping -----

# Each scenario maps to a comparison example used by the hero pill and the
# TRACE card. Fields are illustrative — the underlying message ("ZIP-level
# vs statewide aggregate") doesn't depend on real values.
_ORGANISM_SHORT = {
    "Escherichia coli": "E. coli",
    "Staphylococcus aureus": "S. aureus",
    "Streptococcus pneumoniae": "S. pneumoniae",
    "Klebsiella pneumoniae": "K. pneumoniae",
    "Pseudomonas aeruginosa": "P. aeruginosa",
    "MRSA": "MRSA",
    "Enterococcus species": "Enterococcus spp.",
    "Group A Strep": "S. pyogenes",
    "C. difficile": "C. difficile",
    "Haemophilus influenzae": "H. influenzae",
}

_DRUG_FOR = {
    "Escherichia coli":          ("Ciprofloxacin", "CIP"),
    "Staphylococcus aureus":     ("Clindamycin",   "CLI"),
    "MRSA":                      ("Vancomycin",    "VAN"),
    "Streptococcus pneumoniae":  ("Azithromycin",  "AZM"),
    "Klebsiella pneumoniae":     ("Ceftriaxone",   "CRO"),
    "Pseudomonas aeruginosa":    ("Pip-Tazo",      "TZP"),
    "Enterococcus species":      ("Vancomycin",    "VAN"),
    "Group A Strep":             ("Penicillin",    "PEN"),
    "C. difficile":              ("Vancomycin PO", "VAN"),
    "Haemophilus influenzae":    ("Ceftriaxone",   "CRO"),
}

_COUNTY_ZIP = {
    "Salt Lake":  ("84101", "Downtown SLC"),
    "Utah":       ("84601", "Provo"),
    "Washington": ("84770", "St. George area"),
}

_SCENARIO_LABEL = {
    "UTI / Outpatient":  "Uncomplicated UTI",
    "UTI / Inpatient":   "Complicated UTI / pyelo",
    "Pneumonia":         "Community-acquired pneumonia",
    "Bloodstream":       "S. aureus bacteremia",
    "Pharyngitis":       "GAS pharyngitis",
    "Default":           "Same scenario, same patient, same day",
}


def _resolve_scenario(filters: dict) -> dict:
    """Derive comparison-example metadata from active filter state."""
    organism = filters.get("organism", "Escherichia coli")
    encounter = filters.get("encounter_setting", "Outpatient")
    specimen = filters.get("specimen_type", "Urine")
    counties = filters.get("counties") or ["Washington"]
    # Pick first county for the example ZIP
    primary_county = counties[0]
    zip_code, zip_label = _COUNTY_ZIP.get(
        primary_county, ("84770", "St. George area")
    )
    drug, drug_short = _DRUG_FOR.get(
        organism, ("Ciprofloxacin", "CIP")
    )
    org_short = _ORGANISM_SHORT.get(organism, organism)
    # Choose presenting-scenario phrase
    if specimen == "Urine":
        ctx = "Uncomplicated UTI" if encounter == "Outpatient" \
              else "Complicated UTI / pyelonephritis"
    elif specimen == "Respiratory":
        ctx = "Community-acquired pneumonia" if encounter != "ICU" \
              else "Hospital-acquired pneumonia"
    elif specimen == "Blood":
        ctx = f"{org_short} bacteremia"
    elif specimen == "Throat":
        ctx = "GAS pharyngitis"
    elif specimen == "Wound":
        ctx = "Skin & soft-tissue infection"
    else:
        ctx = "Same pathogen-drug pair"
    return {
        "organism": organism,
        "org_short": org_short,
        "drug": drug,
        "drug_short": drug_short,
        "pair": f"{org_short} × {drug}",
        "zip": zip_code,
        "zip_label": zip_label,
        "county": primary_county,
        "context": ctx,
    }


def _hero(scenario: dict) -> None:
    st.markdown(
        f'<div style="font-family: {t.FONT_HEADING}; font-size: 1.6em; '
        f'font-weight: 600; color: {t.PRIMARY_NAVY}; '
        f'letter-spacing: -0.015em; line-height: 1.2;">'
        f'What prescribers see today '
        f'<span style="color: {t.CLINICAL_CORAL};">vs.</span> '
        f'what TRACE delivers.</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns([3, 2])
    with cols[0]:
        st.markdown(
            f'<div style="font-family: {t.FONT_UI}; font-size: 0.92em; '
            f'color: {t.SLATE_BLUE}; line-height: 1.5; margin-top: 0.6rem;">'
            f'Today, the most current resistance information a community '
            f'prescriber has access to is a state-aggregated annual '
            f'antibiogram, released 12–18 months after the data was '
            f'collected. It\'s a single number for an entire state, often '
            f'delivered as a PDF. TRACE replaces that with continuously '
            f'updated, ZIP-level intelligence at the point of decision.'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f'<div style="background: {t.MIST_WHITE}; '
            f'border: 1px solid {t.COOL_GRAY}; border-radius: 8px; '
            f'padding: 14px 18px; font-family: {t.FONT_UI};">'
            f'<div style="font-weight: 700; color: {t.PRIMARY_NAVY}; '
            f'font-size: 1.05em;">{scenario["pair"]}</div>'
            f'<div style="color: {t.SLATE_BLUE}; font-size: 0.82em; '
            f'margin-top: 4px;">'
            f'{scenario["context"]} · ZIP {scenario["zip"]} '
            f'({scenario["zip_label"]}) · '
            f'same pathogen-drug pair, same patient, same day'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<hr style="margin: 1rem 0; border-color: {t.COOL_GRAY}55;"/>',
        unsafe_allow_html=True,
    )


def _today_panel() -> None:
    st.markdown(
        f'<div style="font-family: {t.FONT_UI}; font-size: 0.78em; '
        f'color: {t.SLATE_BLUE}; letter-spacing: 0.06em; '
        f'font-weight: 600; margin-bottom: 0.4rem;">'
        f'<span style="background: {t.MUTED_AMBER}; color: white; '
        f'padding: 2px 8px; border-radius: 3px; letter-spacing: 0.08em;">'
        f'TODAY</span>'
        f'&nbsp;&nbsp;WHAT THE PRESCRIBER ACTUALLY SEES'
        f'&nbsp;&nbsp;<span style="color: {t.SLATE_BLUE}; '
        f'font-weight: 400; text-transform: none; letter-spacing: 0;">'
        f'released 14 months after the data was collected</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # PDF-style paper card
    st.markdown(
        f'<div style="background: #FBF8EF; border: 1px solid #DCD3B8; '
        f'border-radius: 6px; padding: 24px 28px; '
        f'font-family: \"Times New Roman\", Georgia, serif; '
        f'position: relative; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">'
        f'<div style="position:absolute; top:18px; right:24px; '
        f'transform: rotate(-8deg); border: 2px solid {t.CLINICAL_CORAL}; '
        f'color: {t.CLINICAL_CORAL}; padding: 3px 10px; '
        f'font-family: monospace; font-size: 0.7em; font-weight: 700; '
        f'letter-spacing: 0.1em; opacity: 0.85;">RECEIVED · DOH</div>'

        f'<div style="display: flex; gap: 16px; align-items: flex-start; '
        f'padding-bottom: 14px; border-bottom: 1px solid #BFB385;">'
        f'<div style="width: 46px; height: 46px; background: #9B8E5C; '
        f'color: white; border-radius: 50%; display: flex; '
        f'align-items: center; justify-content: center; '
        f'font-family: monospace; font-size: 0.75em; font-weight: 700;">'
        f'UDOH</div>'
        f'<div style="flex: 1; line-height: 1.4;">'
        f'<div style="font-weight: 700; color: #2F2A1E; font-size: 1em;">'
        f'Utah Department of Health<br>and Human Services</div>'
        f'<div style="color: #6E6647; font-size: 0.78em; '
        f'font-style: italic; margin-top: 4px;">'
        f'Division of Population Health · Healthcare-Associated Infections '
        f'&amp; Antimicrobial Resistance Program</div>'
        f'</div>'
        f'<div style="text-align: right; color: #6E6647; '
        f'font-family: monospace; font-size: 0.75em; line-height: 1.5;">'
        f'Report No. UDOH-AMR-2024-AB<br>'
        f'Released March 2026<br>Distribution: Public</div>'
        f'</div>'

        f'<div style="text-align: center; font-size: 1.15em; '
        f'font-weight: 700; color: #2F2A1E; margin-top: 14px;">'
        f'Annual Antibiogram &amp; Antimicrobial Resistance Surveillance Report'
        f'</div>'
        f'<div style="text-align: center; color: #6E6647; '
        f'font-style: italic; font-size: 0.85em; margin-top: 4px;">'
        f'Calendar Year 2024 · Statewide Aggregate</div>'

        f'<div style="background: #F4ECCB; border: 1px solid #D8C98C; '
        f'border-radius: 4px; padding: 10px 14px; margin: 14px 0; '
        f'font-size: 0.78em; color: #2F2A1E; line-height: 1.6;">'
        f'<strong>Reporting period:</strong> Jan 1 – Dec 31, 2024<br>'
        f'<strong>Geographic scope:</strong> State of Utah, all participating facilities<br>'
        f'<strong>Total isolates:</strong> n = 12,847<br>'
        f'<strong>Submitting facilities:</strong> 31 of 47 acute-care hospitals (66%)<br>'
        f'<strong>Methodology:</strong> CLSI M100 breakpoints; first-isolate only'
        f'</div>'

        f'<div style="font-weight: 700; color: #2F2A1E; '
        f'font-size: 0.85em; margin: 12px 0 6px;">'
        f'Table 1. Selected Pathogen × Antibiotic Susceptibility (% susceptible)'
        f'</div>'

        f'<table style="width: 100%; border-collapse: collapse; '
        f'font-family: \"Times New Roman\", serif; font-size: 0.82em;">'
        f'<thead><tr style="border-top: 1.5px solid #2F2A1E; '
        f'border-bottom: 1px solid #2F2A1E;">'
        f'<th style="text-align: left; padding: 4px 6px;">Organism</th>'
        f'<th style="padding: 4px;">n</th>'
        f'<th style="padding: 4px;">AMP</th><th style="padding: 4px;">SXT</th>'
        f'<th style="padding: 4px; background: #F4D7C7;">CIP</th>'
        f'<th style="padding: 4px;">NIT</th><th style="padding: 4px;">CRO</th>'
        f'</tr></thead><tbody>'
        f'<tr><td style="padding: 4px 6px; font-style: italic;">E. coli</td>'
        f'<td style="text-align: center;">4,118</td>'
        f'<td style="text-align: center;">43</td>'
        f'<td style="text-align: center;">74</td>'
        f'<td style="text-align: center; background: #F4D7C7; '
        f'font-weight: 700; color: {t.CLINICAL_CORAL};">73</td>'
        f'<td style="text-align: center;">92</td>'
        f'<td style="text-align: center;">89</td></tr>'
        f'<tr><td style="padding: 4px 6px; font-style: italic;">K. pneumoniae</td>'
        f'<td style="text-align: center;">1,602</td><td style="text-align: center;">—</td>'
        f'<td style="text-align: center;">80</td><td style="text-align: center;">84</td>'
        f'<td style="text-align: center;">38</td><td style="text-align: center;">87</td></tr>'
        f'<tr><td style="padding: 4px 6px; font-style: italic;">S. aureus</td>'
        f'<td style="text-align: center;">2,041</td>'
        f'<td style="text-align: center;">—</td><td style="text-align: center;">93</td>'
        f'<td style="text-align: center;">—</td><td style="text-align: center;">—</td>'
        f'<td style="text-align: center;">—</td></tr>'
        f'<tr><td style="padding: 4px 6px; font-style: italic;">S. pneumoniae</td>'
        f'<td style="text-align: center;">312</td><td style="text-align: center;">91</td>'
        f'<td style="text-align: center;">—</td><td style="text-align: center;">—</td>'
        f'<td style="text-align: center;">—</td><td style="text-align: center;">95</td></tr>'
        f'</tbody></table>'

        f'<div style="background: {t.CLINICAL_CORAL}; color: white; '
        f'padding: 6px 12px; margin-top: 10px; font-family: {t.FONT_UI}; '
        f'font-size: 0.78em; border-radius: 3px; font-style: italic;">'
        f'One number. Whole state. 14 months ago.'
        f'</div>'

        f'<div style="margin-top: 12px; font-size: 0.7em; '
        f'color: #6E6647; line-height: 1.5;">'
        f'<strong>Abbreviations:</strong> AMP = ampicillin; SXT = TMP-SMX; '
        f'CIP = ciprofloxacin; NIT = nitrofurantoin; CRO = ceftriaxone. '
        f'— = insufficient data.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _trace_panel(scenario: dict) -> None:
    st.markdown(
        f'<div style="font-family: {t.FONT_UI}; font-size: 0.78em; '
        f'color: {t.SLATE_BLUE}; letter-spacing: 0.06em; '
        f'font-weight: 600; margin-bottom: 0.4rem;">'
        f'<span style="background: {t.TRACE_TEAL}; color: white; '
        f'padding: 2px 8px; border-radius: 3px; letter-spacing: 0.08em;">'
        f'TRACE</span>'
        f'&nbsp;&nbsp;WHAT THE PRESCRIBER COULD SEE'
        f'&nbsp;&nbsp;<span style="color: {t.SLATE_BLUE}; '
        f'font-weight: 400; text-transform: none; letter-spacing: 0;">'
        f'refreshed monthly · last update Apr 2026</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="background: white; border: 1px solid {t.COOL_GRAY}; '
        f'border-radius: 8px; overflow: hidden; '
        f'box-shadow: 0 1px 4px rgba(7,26,61,0.06);">'

        # Header strip
        f'<div style="background: {t.PRIMARY_NAVY}; color: white; '
        f'padding: 12px 18px; display: flex; justify-content: space-between; '
        f'align-items: center; font-family: {t.FONT_UI};">'
        f'<div><strong style="letter-spacing: 0.04em;">TRACE</strong>'
        f'<span style="color: {t.TRACE_TEAL}; margin: 0 8px;">·</span>'
        f'<span style="color: #B7C4CE; font-size: 0.85em;">'
        f'Resistance intelligence at point of decision</span></div>'
        f'<div style="font-size: 0.78em; color: {t.SOFT_GREEN};">'
        f'<span style="display:inline-block; width: 8px; height: 8px; '
        f'background: {t.SOFT_GREEN}; border-radius: 50%; '
        f'margin-right: 6px;"></span>'
        f'LIVE · streaming from 31 facilities</div></div>'

        # Meta row
        f'<div style="background: {t.MIST_WHITE}; padding: 8px 18px; '
        f'border-bottom: 1px solid {t.COOL_GRAY}55; '
        f'font-family: {t.FONT_UI}; font-size: 0.82em; color: {t.SLATE_BLUE};">'
        f'<strong style="color: {t.PRIMARY_NAVY};">{scenario["pair"]}</strong>'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;ZIP <strong>{scenario["zip"]}</strong> · '
        f'{scenario["zip_label"]}'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;Updated <strong>April 2026</strong>'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;n=<strong>41</strong> trailing 12 mo'
        f'</div>'

        # Big stat
        f'<div style="padding: 22px 18px;">'
        f'<div style="font-family: {t.FONT_UI}; font-size: 0.78em; '
        f'color: {t.SLATE_BLUE}; letter-spacing: 0.06em; '
        f'font-weight: 600;">LOCAL SUSCEPTIBILITY</div>'
        f'<div style="font-family: {t.FONT_HEADING}; font-size: 3.6em; '
        f'font-weight: 700; color: {t.PRIMARY_NAVY}; line-height: 1; '
        f'margin: 4px 0;">66<span style="font-size: 0.4em; '
        f'color: {t.SLATE_BLUE};">%</span></div>'
        f'<div style="font-size: 0.85em; color: {t.INK};">'
        f'95% Wilson CI <strong>58–73%</strong> '
        f'<span style="color: {t.SLATE_BLUE};">· vs regional baseline 73%</span>'
        f'</div>'
        f'<div style="margin-top: 10px;">'
        f'{ui.evidence_chip("OR 1.41 [1.05–1.91] vs regional", tone="watch")}'
        f'{ui.evidence_chip("YoY +9% relative risk", tone="watch")}'
        f'{ui.evidence_chip("Cochran-Armitage p = 0.018", tone="neutral")}'
        f'</div>'
        f'</div>'

        # Comparison strip
        f'<div style="background: {t.MIST_WHITE}; '
        f'border-top: 1px solid {t.COOL_GRAY}55; '
        f'padding: 12px 18px; display: grid; '
        f'grid-template-columns: 1fr 1fr 1fr; gap: 12px; '
        f'font-family: {t.FONT_UI};">'
        f'<div><div style="font-size: 0.72em; color: {t.SLATE_BLUE}; '
        f'letter-spacing: 0.05em; font-weight: 600; '
        f'text-transform: uppercase;">Granularity</div>'
        f'<div style="font-weight: 600; color: {t.PRIMARY_NAVY}; '
        f'font-size: 0.95em;">ZIP 84770</div>'
        f'<div style="font-size: 0.75em; color: {t.SLATE_BLUE};">'
        f'29 ZIPs · vs 1 statewide</div></div>'
        f'<div><div style="font-size: 0.72em; color: {t.SLATE_BLUE}; '
        f'letter-spacing: 0.05em; font-weight: 600; '
        f'text-transform: uppercase;">Recency</div>'
        f'<div style="font-weight: 600; color: {t.PRIMARY_NAVY}; '
        f'font-size: 0.95em;">Apr 2026</div>'
        f'<div style="font-size: 0.75em; color: {t.SLATE_BLUE};">'
        f'monthly · vs 14-mo lag</div></div>'
        f'<div><div style="font-size: 0.72em; color: {t.SLATE_BLUE}; '
        f'letter-spacing: 0.05em; font-weight: 600; '
        f'text-transform: uppercase;">Statistical depth</div>'
        f'<div style="font-weight: 600; color: {t.PRIMARY_NAVY}; '
        f'font-size: 0.95em;">CI · OR · trend</div>'
        f'<div style="font-size: 0.75em; color: {t.SLATE_BLUE};">'
        f'Wilson, OR, CA, YoY RR</div></div>'
        f'</div>'

        # Footer
        f'<div style="background: {t.PRIMARY_NAVY}11; '
        f'padding: 10px 18px; font-family: {t.FONT_UI}; '
        f'font-size: 0.82em; color: {t.SLATE_BLUE};">'
        f'<span style="background: {t.TRACE_TEAL}; color: white; '
        f'padding: 2px 8px; border-radius: 3px; font-family: monospace; '
        f'font-size: 0.82em;">⟨/⟩ CDS Hooks · order-sign</span>'
        f'&nbsp;&nbsp;Surfaced <strong style="color: {t.PRIMARY_NAVY};">'
        f'at the moment of prescribing</strong> · '
        f'suggests Nitrofurantoin (87%, n=53)'
        f'</div>'

        f'</div>',
        unsafe_allow_html=True,
    )


def _contrast_strip() -> None:
    st.markdown("")
    st.markdown(
        f'<div style="font-family: {t.FONT_HEADING}; font-weight: 600; '
        f'color: {t.PRIMARY_NAVY}; font-size: 1.1em; margin: 0.8rem 0 0.4rem;">'
        f'Five dimensions of difference</div>',
        unsafe_allow_html=True,
    )
    cells = [
        ("Granularity", "1 unit (state)", "29 ZIP units",
         "≥3,400× finer geographic resolution."),
        ("Recency", "12–18 mo lag", "Monthly · live in Phase 2",
         "Catches resistance shifts before clinicians do."),
        ("Statistical depth", "Single point estimate", "CI · OR · trend",
         "Quantifies uncertainty &amp; significance."),
        ("Delivery", "PDF / email", "CDS Hook in EHR",
         "Right info, right person, right moment."),
        ("Action", "Read &amp; remember", "One-click drug swap",
         "Suggestion array creates the MedicationRequest."),
    ]
    cols = st.columns(5)
    for col, (dim, today, trace, note) in zip(cols, cells):
        with col:
            st.markdown(
                f'<div style="background: white; '
                f'border: 1px solid {t.COOL_GRAY}77; border-radius: 6px; '
                f'padding: 10px 12px; height: 100%; '
                f'font-family: {t.FONT_UI};">'
                f'<div style="font-size: 0.72em; color: {t.SLATE_BLUE}; '
                f'letter-spacing: 0.05em; font-weight: 600; '
                f'text-transform: uppercase;">{dim}</div>'
                f'<div style="margin-top: 6px;">'
                f'<span style="color: {t.MUTED_AMBER}; font-weight: 600; '
                f'font-size: 0.85em;">{today}</span>'
                f'<span style="color: {t.SLATE_BLUE}; margin: 0 4px;">→</span><br>'
                f'<span style="color: {t.TRACE_TEAL}; font-weight: 600; '
                f'font-size: 0.85em;">{trace}</span></div>'
                f'<div style="font-size: 0.75em; color: {t.SLATE_BLUE}; '
                f'margin-top: 6px; line-height: 1.4;">{note}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _closing_cta() -> None:
    st.markdown("")
    st.markdown(
        f'<div style="background: {t.PRIMARY_NAVY}; color: white; '
        f'padding: 24px 28px; border-radius: 8px; '
        f'display: grid; grid-template-columns: 3fr 2fr; gap: 28px; '
        f'font-family: {t.FONT_UI}; margin-top: 1rem;">'
        f'<div>'
        f'<div style="font-family: {t.FONT_HEADING}; font-size: 1.4em; '
        f'font-weight: 600; color: white; letter-spacing: -0.01em;">'
        f'The gap is the opportunity.</div>'
        f'<p style="color: #B7C4CE; font-size: 0.9em; line-height: 1.55; '
        f'margin-top: 8px;">'
        f'Every U.S. hospital that bills Medicare already submits the '
        f'underlying AU/AR data under the 2024 CMS NHSN mandate. The '
        f'plumbing exists. The data exists. What doesn\'t exist is the '
        f'layer that turns it into something a prescriber can actually '
        f'use during a 12-minute visit. <strong style="color: white;">'
        f'TRACE is that layer.</strong>'
        f'</p>'
        f'</div>'
        f'<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">'
        f'<div><div style="font-family: {t.FONT_HEADING}; font-size: 2em; '
        f'font-weight: 700; color: {t.TRACE_TEAL};">~36M</div>'
        f'<div style="color: #B7C4CE; font-size: 0.8em;">'
        f'U.S. outpatient antibiotic Rx / yr potentially affected</div></div>'
        f'<div><div style="font-family: {t.FONT_HEADING}; font-size: 2em; '
        f'font-weight: 700; color: {t.TRACE_TEAL};">≥30%</div>'
        f'<div style="color: #B7C4CE; font-size: 0.8em;">'
        f'CDC-estimated avoidable Rx · stewardship target</div></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render(filters: dict) -> None:
    scenario = _resolve_scenario(filters)
    _hero(scenario)
    cols = st.columns(2)
    with cols[0]:
        _today_panel()
    with cols[1]:
        _trace_panel(scenario)
    _contrast_strip()
    _closing_cta()
