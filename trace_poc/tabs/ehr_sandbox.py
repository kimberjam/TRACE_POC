"""EHR Sandbox view — simulated EHR with TRACE Antibiogram side panel.

Shows how TRACE integrates into an existing clinical workflow via CDS Hooks,
rather than asking clinicians to leave the chart to consult another system.

This is investor-demo and clinical-design-credibility surface. It pulls real
susceptibility data from the synthetic dataset for whichever patient is
selected, so the TRACE panel content is data-driven, not hardcoded.

Layout matches the mockup:
  - Top: simulated EHR sub-header (Mountain Health · EHR Sandbox)
  - Patient header strip
  - Left: Today's Schedule sidebar
  - Center: Chart Review tabs with Vitals / Problems / Meds / Results
  - Right: TRACE · ANTIBIOGRAM side panel with live alert
  - Footer: CDS Hooks connection status bar
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import data_loader as dl
from .. import metrics as m
from .. import theme as t


# ----- Sample patient roster -----

PATIENTS = [
    {
        "id": "MH",
        "name": "Hernandez, Maria",
        "age": 34, "sex": "F",
        "time": "08:30",
        "reason": "Dysuria × 2 days",
        "tag": None,
        "mrn": "MRN-41003872",
        "dob": "1991-03-14",
        "zip": "84101",
        "exam": "Exam 1",
        "pcp": "Okonkwo, Adaeze MD",
        "scenario": {
            "organism": "Escherichia coli",
            "specimen": "Urine",
            "encounter": "Outpatient",
            "infection": "Uncomplicated UTI",
        },
    },
    {
        "id": "JP",
        "name": "Park, James",
        "age": 68, "sex": "M",
        "time": "09:00",
        "reason": "Productive cough, fever × 4 days",
        "tag": "PCN",
        "mrn": "MRN-44209118",
        "dob": "1957-11-02",
        "zip": "84401",
        "exam": "Exam 3",
        "pcp": "Okonkwo, Adaeze MD",
        "scenario": {
            "organism": "Streptococcus pneumoniae",
            "specimen": "Respiratory",
            "encounter": "Inpatient",
            "infection": "Community-acquired pneumonia",
        },
    },
    {
        "id": "SA",
        "name": "Ahmadi, Sarah",
        "age": 52, "sex": "F",
        "time": "10:15",
        "reason": "Red, warm forearm for 3 days",
        "tag": "MRSA",
        "mrn": "MRN-50118923",
        "dob": "1973-06-22",
        "zip": "84105",
        "exam": "Exam 2",
        "pcp": "Okonkwo, Adaeze MD",
        "scenario": {
            "organism": "Staphylococcus aureus",
            "specimen": "Wound",
            "encounter": "Outpatient",
            "infection": "Skin & soft tissue infection",
        },
    },
    {
        "id": "RC",
        "name": "Chen, Robert",
        "age": 71, "sex": "M",
        "time": "09:45",
        "reason": "Outpatient pre-op clearance — elective knee replacement; routine UA",
        "tag": None,
        "mrn": "MRN-38291004",
        "dob": "1954-09-12",
        "zip": "84112",
        "exam": "Exam 4",
        "pcp": "Okonkwo, Adaeze MD",
        "scenario": {
            "organism": "Escherichia coli",
            "specimen": "Urine",
            "encounter": "Outpatient",
            "infection": "Asymptomatic bacteriuria",
        },
    },
    {
        "id": "RB",
        "name": "Bennett, Rebecca",
        "age": 29, "sex": "F",
        "time": "14:20",
        "reason": "Dysuria × 2 days — third UTI in 18 months",
        "tag": None,
        "mrn": "MRN-51228745",
        "dob": "1996-11-30",
        "zip": "84109",
        "exam": "Exam 1",
        "pcp": "Okonkwo, Adaeze MD",
        "scenario": {
            "organism": "Escherichia coli",
            "specimen": "Urine",
            "encounter": "Outpatient",
            "infection": "Recurrent UTI",
        },
    },
]


# ----- Per-patient hardcoded chart context -----

PATIENT_CONTEXT = {
    "JP": {
        "visit": [
            ("Reason for visit", "Productive cough, fever × 4 days"),
            ("BP", "138/82"),
            ("Heart rate", "98"),
            ("Temperature", "101.6°F"),
            ("Respirations", "20"),
            ("SpO₂", "96% RA"),
        ],
        "problems": [
            ("J18.1 · ICD-10", "Lobar pneumonia, unspecified organism",
             "Onset 2026-04-22 · active", "PRIMARY"),
            ("I25.10 · ICD-10", "Atherosclerotic heart disease",
             "Onset 2016-09-03 · active", None),
            ("J44.9 · ICD-10", "COPD, unspecified",
             "Onset 2018-03-17 · active", None),
        ],
        "meds": [
            ("Atorvastatin", "40 mg PO qHS · since 2016-09-03"),
            ("Metoprolol succinate", "50 mg PO daily · since 2016-09-03"),
            ("Tiotropium", "18 mcg INH daily · since 2018-03-17"),
        ],
        "results": [
            ("2026-04-22 05:40", "WBC", "16.2", "H"),
            ("2026-04-22 05:40", "Procalcitonin", "2.4", "H"),
            ("2026-04-22 06:15", "Chest X-ray", "RLL consolidation", "A"),
        ],
    },

    # Hernandez, Maria — uncomplicated UTI, healthy young female
    "MH": {
        "visit": [
            ("Reason for visit", "Dysuria, urinary frequency × 2 days"),
            ("BP", "118/74"),
            ("Heart rate", "82"),
            ("Temperature", "99.4°F"),
            ("Respirations", "16"),
            ("SpO₂", "99% RA"),
        ],
        "problems": [
            ("N39.0 · ICD-10", "Urinary tract infection, site not specified",
             "Onset 2026-04-22 · active", "PRIMARY"),
            ("Z79.3 · ICD-10",
             "Long-term use of hormonal contraceptives",
             "Active since 2018-04 · active", None),
        ],
        "meds": [
            ("Drospirenone-EE", "3 mg / 30 mcg PO daily · since 2018-04-12"),
            ("Cetirizine", "10 mg PO PRN allergies · since 2022-03-15"),
        ],
        "results": [
            ("2026-04-22 09:15", "Urine dipstick — leuk esterase", "Positive", "A"),
            ("2026-04-22 09:15", "Urine dipstick — nitrite", "Positive", "A"),
            ("2026-04-22 09:15", "Urine WBC", "> 25 / hpf", "H"),
            ("2026-04-22 09:20", "Urine culture", "Pending · expected 24–48h", None),
        ],
    },

    # Ahmadi, Sarah — skin and soft-tissue infection, prior MRSA
    "SA": {
        "visit": [
            ("Reason for visit", "Red, warm, tender forearm × 3 days; "
             "no fluctuance"),
            ("BP", "132/80"),
            ("Heart rate", "92"),
            ("Temperature", "100.8°F"),
            ("Respirations", "18"),
            ("SpO₂", "98% RA"),
        ],
        "problems": [
            ("L03.114 · ICD-10",
             "Cellulitis of left upper limb",
             "Onset 2026-04-19 · active", "PRIMARY"),
            ("Z16.11 · ICD-10",
             "Resistance to penicillins — prior MRSA isolate",
             "Documented 2024-08-03 · active", "MRSA"),
            ("I10 · ICD-10", "Essential hypertension",
             "Onset 2019-02-11 · active", None),
        ],
        "meds": [
            ("Lisinopril", "10 mg PO daily · since 2019-02-11"),
            ("Hydrochlorothiazide", "12.5 mg PO daily · since 2019-02-11"),
        ],
        "results": [
            ("2026-04-22 10:30", "WBC", "13.8", "H"),
            ("2026-04-22 10:30", "CRP", "42 mg/L", "H"),
            ("2024-08-03", "Wound culture (prior episode)",
             "S. aureus, methicillin-resistant", "A"),
            ("2026-04-22 10:45", "Wound culture (current)",
             "Pending · expected 48–72h", None),
        ],
    },

    # Chen, Robert — pre-op clearance, routine UA, asymptomatic
    "RC": {
        "visit": [
            ("Reason for visit", "Pre-op clearance — elective right TKA"),
            ("BP", "136/82"),
            ("Heart rate", "72"),
            ("Temperature", "98.4°F"),
            ("Respirations", "14"),
            ("SpO₂", "97% RA"),
        ],
        "problems": [
            ("M17.11 · ICD-10",
             "Unilateral primary osteoarthritis, right knee",
             "Onset 2022-06-09 · active", "PRIMARY"),
            ("I25.10 · ICD-10", "Atherosclerotic heart disease",
             "Onset 2017-03-14 · active", None),
            ("E11.9 · ICD-10",
             "Type 2 diabetes mellitus without complications",
             "Onset 2014-11-20 · active", None),
        ],
        "meds": [
            ("Atorvastatin", "40 mg PO qHS · since 2017-03-14"),
            ("Metformin", "1,000 mg PO BID · since 2014-11-20"),
            ("Aspirin", "81 mg PO daily · since 2017-03-14"),
            ("Acetaminophen", "650 mg PO TID PRN knee pain · since 2022-07-01"),
        ],
        "results": [
            ("2026-04-22 08:00", "Urine dipstick — leuk esterase",
             "Negative", None),
            ("2026-04-22 08:00", "Urine dipstick — nitrite",
             "Negative", None),
            ("2026-04-22 08:00", "Urine WBC", "2 / hpf", None),
            ("2026-04-22 07:45", "HbA1c", "6.8%", None),
            ("2026-04-22 07:45", "Basic metabolic panel", "Within range", None),
        ],
    },

    # Bennett, Rebecca — recurrent UTI, treatment-history relevant
    "RB": {
        "visit": [
            ("Reason for visit", "Dysuria × 2 days — third UTI in 18 months"),
            ("BP", "120/76"),
            ("Heart rate", "80"),
            ("Temperature", "99.6°F"),
            ("Respirations", "16"),
            ("SpO₂", "99% RA"),
        ],
        "problems": [
            ("N39.0 · ICD-10",
             "Urinary tract infection, recurrent",
             "Onset 2026-04-22 · active", "PRIMARY"),
            ("Z87.440 · ICD-10",
             "Personal history of recurrent UTI",
             "Documented 2025-10-18 · active", None),
        ],
        "meds": [
            ("Combined oral contraceptive", "1 tab PO daily · since 2021-05-10"),
            ("Ibuprofen", "400 mg PO PRN pain · since 2024-01-08"),
        ],
        "results": [
            ("2026-04-22 14:35", "Urine dipstick — leuk esterase",
             "Positive", "A"),
            ("2026-04-22 14:35", "Urine dipstick — nitrite", "Positive", "A"),
            ("2026-04-22 14:35", "Urine WBC", "> 50 / hpf", "H"),
            ("2025-10-18", "Prior urine culture",
             "E. coli — R to TMP-SMX, S to nitrofurantoin", "A"),
            ("2025-03-04", "Prior urine culture",
             "E. coli — S to nitrofurantoin, S to fosfomycin", None),
            ("2026-04-22 14:50", "Urine culture (current)",
             "Pending · expected 24–48h", None),
        ],
    },
}


# ----- Sub-components -----

def _ehr_subheader() -> None:
    st.markdown(
        f'<div style="background: {t.PRIMARY_NAVY}; color: white; '
        f'padding: 10px 20px; margin: 0 -1rem 0 -1rem; '
        f'font-family: {t.FONT_UI}; font-size: 0.9em; '
        f'display: flex; align-items: center; justify-content: space-between;">'
        f'<div><span style="color: {t.TRACE_TEAL};">●</span>&nbsp;&nbsp;'
        f'<strong style="letter-spacing: 0.05em;">MOUNTAIN HEALTH</strong>'
        f'&nbsp;·&nbsp;EHR Sandbox</div>'
        f'<div style="display: flex; gap: 22px; font-size: 0.92em;">'
        f'<span style="background: {t.SLATE_BLUE}; padding: 4px 10px; '
        f'border-radius: 3px;">Schedule</span>'
        f'<span>Inbox <span style="background: {t.CLINICAL_CORAL}; '
        f'color: white; padding: 1px 6px; border-radius: 8px; '
        f'font-size: 0.8em;">12</span></span>'
        f'<span>Chart Search</span>'
        f'<span>Reports</span>'
        f'<span style="font-family: monospace;">&lt;/&gt; FHIR</span>'
        f'</div>'
        f'<div style="text-align: right; line-height: 1.2;">'
        f'<div style="background: {t.MUTED_AMBER}; color: white; '
        f'padding: 2px 8px; border-radius: 3px; font-size: 0.78em; '
        f'letter-spacing: 0.08em; display: inline-block;">'
        f'SANDBOX · SIMULATED EHR</div>'
        f'<div style="font-size: 0.8em; margin-top: 4px; opacity: 0.85;">'
        f'Internal Medicine · Red Rock Regional · 22:45</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _patient_header(patient: dict) -> None:
    st.markdown(
        f'<div style="background: #FDFCF5; '
        f'border-bottom: 1px solid {t.COOL_GRAY}; '
        f'padding: 12px 20px; margin: 0 -1rem 0 -1rem; '
        f'font-family: {t.FONT_UI};">'
        f'<div style="display: flex; align-items: center; gap: 16px;">'
        f'<div style="background: {t.COOL_GRAY}; color: {t.PRIMARY_NAVY}; '
        f'width: 48px; height: 48px; border-radius: 6px; '
        f'display: flex; align-items: center; justify-content: center; '
        f'font-family: {t.FONT_HEADING}; font-weight: 600; font-size: 1.1em;">'
        f'{patient["id"]}</div>'
        f'<div style="flex: 1;">'
        f'<div style="font-family: {t.FONT_HEADING}; font-size: 1.4em; '
        f'font-weight: 600; color: {t.PRIMARY_NAVY};">{patient["name"]}'
        f'<span style="font-size: 0.7em; font-weight: 400; '
        f'color: {t.SLATE_BLUE}; margin-left: 8px;">'
        f'({patient["sex"]}, {patient["age"]} y)</span></div>'
        f'<div style="color: {t.SLATE_BLUE}; font-size: 0.88em; margin-top: 4px;">'
        f'<span style="font-family: monospace;">MRN {patient["mrn"]}</span>'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;DOB {patient["dob"]}'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;ZIP {patient["zip"]}'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;{patient["exam"]}'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;PCP {patient["pcp"]}</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _schedule_sidebar(active_id: str) -> str:
    """Return the id of the currently-selected patient."""
    st.markdown(
        f'<div style="font-family: {t.FONT_UI}; font-size: 0.72em; '
        f'color: {t.SLATE_BLUE}; letter-spacing: 0.08em; '
        f'font-weight: 600; margin-bottom: 8px;">'
        f'TODAY\'S SCHEDULE · APR 22</div>',
        unsafe_allow_html=True,
    )

    selected_id = active_id
    for p in PATIENTS:
        is_active = p["id"] == active_id
        bg = f"{t.TRACE_TEAL}22" if is_active else "transparent"
        border_left = (f"3px solid {t.TRACE_TEAL}" if is_active
                       else f"3px solid transparent")
        tag_html = ""
        if p["tag"] == "PCN":
            tag_html = (f'<span style="background: {t.MUTED_AMBER}22; '
                        f'color: #8A5F0F; padding: 1px 6px; '
                        f'border-radius: 3px; font-size: 0.7em; '
                        f'font-weight: 600;">PCN</span>')
        elif p["tag"] == "MRSA":
            tag_html = (f'<span style="background: {t.CLINICAL_CORAL}22; '
                        f'color: {t.CLINICAL_CORAL}; padding: 1px 6px; '
                        f'border-radius: 3px; font-size: 0.7em; '
                        f'font-weight: 600;">MRSA</span>')

        st.markdown(
            f'<div style="background: {bg}; border-left: {border_left}; '
            f'padding: 8px 10px; margin: 2px 0; font-family: {t.FONT_UI};">'
            f'<div style="display: flex; gap: 8px; align-items: flex-start;">'
            f'<div style="background: {t.COOL_GRAY}; color: {t.PRIMARY_NAVY}; '
            f'min-width: 26px; height: 26px; border-radius: 4px; '
            f'display: flex; align-items: center; justify-content: center; '
            f'font-size: 0.72em; font-weight: 600;">{p["id"]}</div>'
            f'<div style="flex: 1; min-width: 0;">'
            f'<div style="font-weight: 600; color: {t.PRIMARY_NAVY}; '
            f'font-size: 0.85em;">{p["name"]}</div>'
            f'<div style="font-size: 0.75em; color: {t.SLATE_BLUE}; '
            f'line-height: 1.3; margin-top: 2px;">'
            f'<strong>{p["time"]}</strong> · {p["reason"]}</div>'
            f'</div>{tag_html}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div style="margin-top: 24px; font-family: {t.FONT_UI}; '
        f'font-size: 0.72em; color: {t.SLATE_BLUE}; '
        f'letter-spacing: 0.08em; font-weight: 600;">ACTIVITIES</div>',
        unsafe_allow_html=True,
    )
    for label in ["Chart Review", "Problem List", "Medications", "Orders", "Notes"]:
        is_active = label == "Chart Review"
        color = t.PRIMARY_NAVY if is_active else t.SLATE_BLUE
        bg = f"{t.TRACE_TEAL}22" if is_active else "transparent"
        st.markdown(
            f'<div style="background: {bg}; padding: 6px 10px; '
            f'margin: 1px 0; font-family: {t.FONT_UI}; font-size: 0.85em; '
            f'color: {color}; font-weight: {"600" if is_active else "400"};">'
            f'{"■" if is_active else "□"}&nbsp;&nbsp;{label}</div>',
            unsafe_allow_html=True,
        )

    return selected_id


def _chart_section_header(title: str) -> None:
    st.markdown(
        f'<div style="font-family: {t.FONT_UI}; font-size: 0.72em; '
        f'color: {t.SLATE_BLUE}; letter-spacing: 0.08em; '
        f'font-weight: 600; margin-bottom: 8px;">{title}</div>',
        unsafe_allow_html=True,
    )


def _chart_center(patient: dict) -> None:
    # Tab bar (visual only)
    tabs_html = ""
    chart_tabs = ["Chart Review", "Problem List", "Medications",
                  "Results Review", "Orders", "Notes"]
    for i, label in enumerate(chart_tabs):
        is_active = (i == 0)
        weight = "600" if is_active else "500"
        color = t.PRIMARY_NAVY if is_active else t.SLATE_BLUE
        border = (f'border-bottom: 3px solid {t.TRACE_TEAL};'
                  if is_active else 'border-bottom: 3px solid transparent;')
        tabs_html += (
            f'<span style="padding: 10px 16px; font-family: {t.FONT_UI}; '
            f'font-weight: {weight}; color: {color}; {border} '
            f'font-size: 0.92em;">{label}</span>'
        )
    st.markdown(
        f'<div style="display: flex; gap: 0; border-bottom: 1px solid '
        f'{t.COOL_GRAY}; margin-bottom: 16px;">{tabs_html}</div>',
        unsafe_allow_html=True,
    )

    context = PATIENT_CONTEXT.get(patient["id"])
    if context is None:
        ui_fallback(patient)
        return

    # Two-column card grid
    grid = st.columns(2)

    with grid[0]:
        with st.container(border=True):
            _chart_section_header("VISIT & VITALS")
            for label, value in context["visit"]:
                st.markdown(
                    f'<div style="display: flex; padding: 4px 0; '
                    f'border-bottom: 1px dotted {t.COOL_GRAY}66; '
                    f'font-family: {t.FONT_UI};">'
                    f'<div style="flex: 1; color: {t.SLATE_BLUE}; '
                    f'font-size: 0.88em;">{label}</div>'
                    f'<div style="flex: 1; color: {t.INK}; font-weight: 500; '
                    f'font-size: 0.92em;">{value}</div></div>',
                    unsafe_allow_html=True,
                )

    with grid[1]:
        with st.container(border=True):
            _chart_section_header("ACTIVE PROBLEMS")
            for code, name, onset, badge in context["problems"]:
                badge_html = ""
                if badge:
                    badge_html = (
                        f'&nbsp;<span style="background: {t.CLINICAL_CORAL}; '
                        f'color: white; padding: 1px 6px; border-radius: 3px; '
                        f'font-size: 0.7em; font-weight: 600;">{badge}</span>'
                    )
                st.markdown(
                    f'<div style="padding: 6px 0; '
                    f'border-bottom: 1px dotted {t.COOL_GRAY}66; '
                    f'font-family: {t.FONT_UI};">'
                    f'<div style="font-family: monospace; '
                    f'color: {t.SLATE_BLUE}; font-size: 0.78em;">{code}{badge_html}</div>'
                    f'<div style="color: {t.INK}; font-weight: 600; '
                    f'font-size: 0.92em; margin-top: 2px;">{name}</div>'
                    f'<div style="color: {t.SLATE_BLUE}; font-size: 0.8em;">'
                    f'{onset}</div></div>',
                    unsafe_allow_html=True,
                )

    grid2 = st.columns(2)
    with grid2[0]:
        with st.container(border=True):
            _chart_section_header("MEDICATIONS & ALLERGIES")
            for name, detail in context["meds"]:
                st.markdown(
                    f'<div style="padding: 6px 0; '
                    f'border-bottom: 1px dotted {t.COOL_GRAY}66; '
                    f'font-family: {t.FONT_UI};">'
                    f'<div style="color: {t.INK}; font-weight: 600; '
                    f'font-size: 0.9em;">{name}</div>'
                    f'<div style="color: {t.SLATE_BLUE}; font-size: 0.82em;">'
                    f'{detail}</div></div>',
                    unsafe_allow_html=True,
                )

    with grid2[1]:
        with st.container(border=True):
            _chart_section_header("RECENT RESULTS")
            for time, test, result, flag in context["results"]:
                flag_color = (
                    t.CLINICAL_CORAL if flag in ("H", "A") else t.SLATE_BLUE
                )
                st.markdown(
                    f'<div style="display: grid; '
                    f'grid-template-columns: 1.3fr 1.3fr 1.5fr 0.5fr; '
                    f'gap: 8px; padding: 6px 0; align-items: center; '
                    f'border-bottom: 1px dotted {t.COOL_GRAY}66; '
                    f'font-family: {t.FONT_UI}; font-size: 0.85em;">'
                    f'<div style="color: {t.SLATE_BLUE}; '
                    f'font-family: monospace;">{time}</div>'
                    f'<div style="color: {t.INK}; font-weight: 500;">{test}</div>'
                    f'<div style="color: {t.INK};">{result}</div>'
                    f'<div style="color: {flag_color}; font-weight: 600; '
                    f'text-align: right;">{flag}</div></div>',
                    unsafe_allow_html=True,
                )


def ui_fallback(patient: dict) -> None:
    st.info(
        f"Detailed chart content for {patient['name']} not yet authored. "
        f"Select James Park (JP) from the schedule to see the full Chart "
        f"Review demo."
    )


def _trace_panel(patient: dict, df: pd.DataFrame) -> None:
    organism = patient["scenario"]["organism"]
    zip_code = patient["zip"]

    # Pull the actual susceptibility profile for this organism × this ZIP
    sub = df[
        (df["organism"] == organism)
        & (df["patient_zip"] == zip_code)
        & df["susceptibility"].isin(["S", "R"])
    ]
    # Fallback: if no data in this exact ZIP, expand to the county
    if sub.empty:
        county = dl.load_zip_county_map()
        c = county[county["zip"] == zip_code]
        if not c.empty:
            cname = c["county"].iloc[0]
            sub = df[
                (df["organism"] == organism)
                & (df["county"] == cname)
                & df["susceptibility"].isin(["S", "R"])
            ]

    n = sub["test_id"].nunique() if not sub.empty else 0

    # Panel header
    st.markdown(
        f'<div style="background: {t.PRIMARY_NAVY}; color: white; '
        f'padding: 10px 14px; font-family: {t.FONT_UI}; '
        f'display: flex; justify-content: space-between; align-items: center;">'
        f'<div><span style="color: {t.TRACE_TEAL};">●</span>&nbsp;&nbsp;'
        f'<strong style="letter-spacing: 0.08em;">TRACE · ANTIBIOGRAM</strong>'
        f'</div>'
        f'<div style="background: {t.SOFT_GREEN}; color: white; '
        f'padding: 2px 10px; border-radius: 3px; font-size: 0.72em; '
        f'letter-spacing: 0.06em; font-weight: 600;">ENABLED</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Alert card (only fires for cases where coverage is concerning)
    alert_text = ""
    if organism == "Streptococcus pneumoniae":
        alert_text = (
            "Elevated local resistance for S. pneumoniae in ZIP "
            f"{zip_code}"
        )
        body = (
            f"Patient's ZIP polygon <strong>{zip_code}</strong> has the "
            f"following local susceptibility for S. pneumoniae across "
            f"<strong>{n} isolates</strong> over the last 12 months. Values "
            f"shown with Wilson-score 95% CIs; comparisons use regional "
            f"baseline across 12 ZIPs."
        )
    elif organism == "Staphylococcus aureus":
        alert_text = "Elevated local MRSA prevalence in recent isolates"
        body = (
            f"MRSA accounts for an elevated share of S. aureus isolates "
            f"in ZIP <strong>{zip_code}</strong> over the last 90 days "
            f"(n={n} isolates). This patient has a documented prior MRSA isolate. "
            f"Local susceptibility context is shown below."
        )
    else:
        alert_text = "Local susceptibility available"
        body = (
            f"Local susceptibility for {organism} in ZIP "
            f"<strong>{zip_code}</strong> across {n} isolates over the "
            f"last 12 months."
        )

    st.markdown(
        f'<div style="background: #FFFBED; '
        f'border-left: 4px solid {t.MUTED_AMBER}; '
        f'padding: 14px; margin-top: 10px; font-family: {t.FONT_UI};">'
        f'<div style="display: flex; gap: 10px; align-items: flex-start;">'
        f'<div style="color: {t.MUTED_AMBER}; font-size: 1.2em;">⚠</div>'
        f'<div style="flex: 1;">'
        f'<div style="font-weight: 600; color: {t.PRIMARY_NAVY}; '
        f'font-size: 0.95em;">{alert_text}</div>'
        f'<div style="color: {t.INK}; font-size: 0.85em; margin-top: 8px; '
        f'line-height: 1.4;">{body}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    # Susceptibility quick view
    if not sub.empty:
        sus_table = m.susceptibility_table(sub, organism).head(5)
        st.markdown(
            f'<div style="font-family: {t.FONT_UI}; '
            f'font-size: 0.72em; color: {t.SLATE_BLUE}; '
            f'letter-spacing: 0.08em; font-weight: 600; '
            f'margin: 16px 0 8px 0;">SELECTED LOCAL SUSCEPTIBILITY INDICATORS</div>',
            unsafe_allow_html=True,
        )
        for _, row in sus_table.iterrows():
            pct = row["pct_susceptible"]
            n_iso = int(row["n_isolates"])
            # Color the bar based on susceptibility level
            if pct >= 85:
                color = t.SOFT_GREEN
            elif pct >= 70:
                color = t.MUTED_AMBER
            else:
                color = t.CLINICAL_CORAL
            st.markdown(
                f'<div style="font-family: {t.FONT_UI}; margin: 8px 0;">'
                f'<div style="display: flex; justify-content: space-between; '
                f'font-size: 0.85em; margin-bottom: 3px;">'
                f'<span style="color: {t.INK}; font-weight: 500;">'
                f'{row["drug"]}</span>'
                f'<span style="color: {color}; font-weight: 600;">'
                f'{pct:.0f}% (n={n_iso})</span></div>'
                f'<div style="background: {t.COOL_GRAY}33; height: 6px; '
                f'border-radius: 3px; overflow: hidden;">'
                f'<div style="background: {color}; width: {pct}%; '
                f'height: 100%;"></div></div></div>',
                unsafe_allow_html=True,
            )

    # Footer chip
    st.markdown(
        f'<div style="margin-top: 12px; padding: 8px 0; '
        f'border-top: 1px solid {t.COOL_GRAY}44; '
        f'font-family: {t.FONT_UI}; font-size: 0.78em; '
        f'color: {t.SLATE_BLUE};">'
        f'<strong style="color: {t.PRIMARY_NAVY};">TRACE</strong> · '
        f'ZIP {zip_code} · updated Apr 2026<br/>'
        f'Full local antibiogram · Method: Wilson-score CI, n≥30 threshold · '
        f'<a href="#" style="color: {t.SLATE_BLUE};">Dismiss</a>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _footer_status_bar() -> None:
    st.markdown(
        f'<div style="background: {t.PRIMARY_NAVY}; color: white; '
        f'padding: 8px 20px; margin: 1rem -1rem -1rem -1rem; '
        f'font-family: {t.FONT_UI}; font-size: 0.78em; '
        f'display: flex; justify-content: space-between; '
        f'align-items: center;">'
        f'<div><span style="color: {t.SOFT_GREEN};">●</span>&nbsp;&nbsp;'
        f'TRACE Antibiogram Service · '
        f'<span style="font-family: monospace;">trace.health/antibiogram</span>'
        f' · connected via CDS Hooks 1.1 protocol</div>'
        f'<div>FHIR R4 · SMART on FHIR · CDS Hooks 1.1</div>'
        f'<div style="opacity: 0.85;">1 hook fired this session</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ----- Main render -----

def render(filters: dict) -> None:
    """Render the EHR Sandbox view."""
    _ehr_subheader()

    # Patient picker (defaults to James Park — pneumonia, most complete chart)
    if "ehr_patient_id" not in st.session_state:
        st.session_state["ehr_patient_id"] = "JP"

    # Allow URL-style switch via the schedule sidebar (rendered below)
    selected_id = st.session_state["ehr_patient_id"]
    patient = next((p for p in PATIENTS if p["id"] == selected_id), PATIENTS[1])

    _patient_header(patient)

    # Optional patient-picker UI above the three-column layout
    picker_cols = st.columns([4, 2])
    with picker_cols[1]:
        new_id = st.selectbox(
            "Switch patient (demo)",
            options=[p["id"] for p in PATIENTS],
            format_func=lambda i: next(
                p["name"] for p in PATIENTS if p["id"] == i
            ),
            index=[p["id"] for p in PATIENTS].index(selected_id),
            label_visibility="collapsed",
            key="ehr_patient_picker",
        )
        if new_id != selected_id:
            st.session_state["ehr_patient_id"] = new_id
            st.rerun()
    with picker_cols[0]:
        st.markdown(
            f'<div style="font-family: {t.FONT_UI}; font-size: 0.85em; '
            f'color: {t.SLATE_BLUE}; padding-top: 4px;">'
            f'Use the patient picker (top right) to switch charts. '
            f'The TRACE side panel updates with each patient\'s ZIP-level '
            f'susceptibility profile.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # Load data for the TRACE panel
    df = dl.load_test_results()

    # Three-column layout
    sched_col, chart_col, trace_col = st.columns([1.4, 4, 2.2])

    with sched_col:
        _schedule_sidebar(selected_id)

    with chart_col:
        _chart_center(patient)

    with trace_col:
        # CR-12: TRACE only fires when there is a clinical indication.
        # Robert Chen is pre-op clearance with no active infection — panel hidden.
        if patient["scenario"]["infection"] == "Asymptomatic bacteriuria":
            st.markdown(
                f'<div style="background: {t.PRIMARY_NAVY}; color: white; '
                f'padding: 10px 14px; font-family: {t.FONT_UI}; '
                f'display: flex; justify-content: space-between; '
                f'align-items: center;">'
                f'<div><span style="color: {t.TRACE_TEAL};">●</span>&nbsp;&nbsp;'
                f'<strong style="letter-spacing: 0.08em;">TRACE · ANTIBIOGRAM</strong>'
                f'</div>'
                f'<div style="background: {t.COOL_GRAY}; color: {t.PRIMARY_NAVY}; '
                f'padding: 2px 10px; border-radius: 3px; font-size: 0.72em; '
                f'letter-spacing: 0.06em; font-weight: 600;">NOT ACTIVATED</div>'
                f'</div>'
                f'<div style="padding: 14px; font-family: {t.FONT_UI}; '
                f'font-size: 0.85em; color: {t.SLATE_BLUE}; line-height: 1.5; '
                f'border: 1px solid {t.COOL_GRAY}44; border-top: none; '
                f'border-radius: 0 0 6px 6px;">'
                f'<strong style="color: {t.PRIMARY_NAVY};">No active infection context.</strong><br/>'
                f'TRACE activates when there is a clinical indication for '
                f'antimicrobial therapy. This patient is presenting for '
                f'pre-operative clearance with no active infection. '
                f'Local susceptibility data is available but not surfaced '
                f'for asymptomatic presentations.'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            _trace_panel(patient, df)

    _footer_status_bar()
