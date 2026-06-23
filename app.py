"""TRACE — unified POC.

Antibiotic stewardship and antimicrobial resistance dashboard.
Aligned with the CDC NHSN AUR module data structure.

Two top-level modes:
  - Investor Demo: 6-tab dashboard (Resistance Weather Map / Point of Care /
    Stewardship View / Today vs TRACE / About & Architecture / Admin)
  - EHR Sandbox: simulated EHR with TRACE Antibiogram side panel

Run:  streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from trace_poc import data_loader as dl
from trace_poc import theme as t
from trace_poc import components as ui
from trace_poc.tabs import (
    weather_map,
    clinical_context,
    stewardship,
    today_vs_trace,
    about_architecture,
    admin,
    ehr_sandbox,
)


# ----- Page config -----

_FAVICON = Path(__file__).parent / "assets" / "favicon.png"

st.set_page_config(
    page_title="TRACE — Resistance Intelligence",
    page_icon=str(_FAVICON) if _FAVICON.exists() else "🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ----- Custom CSS: load fonts, compact spacing, sticky banner, wide tabs -----

_CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Reduce default Streamlit page padding so more fits above the fold */
.block-container {{
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 1500px;
}}

/* Body + UI text */
html, body, [class*="css"], .stMarkdown, .stText, .stMetric,
[data-testid="stSidebar"], [data-testid="stAppViewContainer"] {{
    font-family: {t.FONT_UI};
    color: {t.INK};
}}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {{
    font-family: {t.FONT_HEADING};
    color: {t.PRIMARY_NAVY};
    font-weight: 600;
    letter-spacing: -0.01em;
}}

/* Compact heading sizes */
.stMarkdown h1 {{ font-size: 1.6em; margin: 0.4em 0 0.3em; }}
.stMarkdown h2 {{ font-size: 1.3em; margin: 0.4em 0 0.3em; }}
.stMarkdown h3 {{ font-size: 1.05em; margin: 0.3em 0 0.25em; }}
.stMarkdown h4 {{ font-size: 0.95em; margin: 0.25em 0 0.2em; }}

/* Metric (KPI) display */
[data-testid="stMetricValue"] {{
    font-family: {t.FONT_HEADING};
    color: {t.PRIMARY_NAVY};
    font-weight: 600;
    font-size: 1.7em !important;
    line-height: 1.1;
}}

[data-testid="stMetricLabel"] {{
    color: {t.SLATE_BLUE};
    text-transform: uppercase;
    font-size: 0.68em !important;
    letter-spacing: 0.06em;
    font-weight: 600;
}}

[data-testid="stMetricDelta"] {{
    font-size: 0.8em;
}}

/* TAB LIST: fixed below the brand header so users can switch at any
   scroll position. Width spans the viewport; padding matches the content
   area's margins. */
div[data-baseweb="tab-list"] {{
    gap: 4px !important;
    border-bottom: 1px solid {t.COOL_GRAY}88;
    overflow-x: auto;
    scrollbar-width: thin;
    position: fixed !important;
    top: 2.5rem !important;  /* flush below the brand header (no top banner) */
    left: 0 !important;
    right: 0 !important;
    z-index: 99 !important;
    background: {t.MIST_WHITE} !important;
    padding: 6px 5% 0 5% !important;
    box-shadow: 0 2px 6px rgba(7,26,61,0.04);
}}

/* Push content down so it doesn't hide behind the fixed brand + tabs.
   Brand (~2.5rem) + tab list (~3rem) = ~5.5rem, with a small buffer.
   padding-bottom clears the fixed bottom status bar (~1.5rem). */
section[data-testid="stMain"] {{
    padding-top: 0 !important;
}}

[data-testid="stMainBlockContainer"],
.stMainBlockContainer,
.block-container {{
    padding-top: 5.5rem !important;
    padding-bottom: 2rem !important;
}}

div[data-baseweb="tab-list"] button {{
    font-family: {t.FONT_UI};
    font-weight: 500;
    color: {t.SLATE_BLUE};
    background: transparent;
    padding: 10px 22px !important;
    min-width: 165px;
    white-space: nowrap;
    font-size: 0.95em;
}}

div[data-baseweb="tab-list"] button[aria-selected="true"] {{
    color: {t.PRIMARY_NAVY} !important;
    font-weight: 600;
}}

div[data-baseweb="tab-highlight"] {{
    background-color: {t.TRACE_TEAL} !important;
    height: 3px !important;
}}

/* Smaller table font */
[data-testid="stDataFrame"] {{
    font-family: {t.FONT_TABLE};
    font-size: 0.9em;
}}

/* Sidebar surface */
[data-testid="stSidebar"] > div:first-child {{
    background-color: {t.MIST_WHITE};
    border-right: 1px solid {t.COOL_GRAY}33;
}}

[data-testid="stSidebar"] .block-container {{
    padding-top: 1.5rem !important;
}}

/* Bordered containers */
[data-testid="stVerticalBlockBorderWrapper"] {{
    border-color: {t.COOL_GRAY}55 !important;
    background: white;
}}

/* Captions */
.stCaption, [data-testid="stCaptionContainer"] {{
    color: {t.SLATE_BLUE} !important;
    font-size: 0.82em !important;
}}

/* Dividers */
hr {{
    border-color: {t.COOL_GRAY}55;
    margin: 0.25rem 0 !important;
}}

/* Primary button: TRACE Teal */
.stButton button[kind="primary"] {{
    background-color: {t.TRACE_TEAL};
    color: white;
    border: 1px solid {t.TRACE_TEAL};
    font-family: {t.FONT_UI};
    font-weight: 600;
}}

.stButton button[kind="primary"]:hover {{
    background-color: {t.PRIMARY_NAVY};
    border-color: {t.PRIMARY_NAVY};
    color: white;
}}

/* ===== Sidebar toggle labels ===== */
/* COLLAPSED state — small scenario icon in the header row (top-right).
   Real testid (per inspector on Streamlit 1.58): stExpandSidebarButton */
button[data-testid="stExpandSidebarButton"] {{
    display: inline-flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 4px !important;
    padding: 3px 10px !important;
    margin: 0 !important;
    background: transparent !important;
    border: 1px solid {t.COOL_GRAY}88 !important;
    border-radius: 4px !important;
    width: auto !important;
    min-width: auto !important;
    height: auto !important;
    overflow: visible !important;
    cursor: pointer !important;
    color: {t.SLATE_BLUE} !important;
    box-shadow: none !important;
}}

button[data-testid="stExpandSidebarButton"]::before {{
    content: "⚙ Scenario" !important;
    color: {t.SLATE_BLUE} !important;
    font-family: {t.FONT_UI} !important;
    font-weight: 500 !important;
    font-size: 11px !important;
    letter-spacing: 0.03em !important;
    white-space: nowrap !important;
    line-height: 1 !important;
}}

/* EXPANDED state — "Collapse" label next to the close arrow inside the
   sidebar. Streamlit's default keeps this button at opacity:0 unless the
   sidebar is hovered; we force it visible always. */
button[data-testid="stCollapseSidebarButton"],
section[data-testid="stSidebar"] button[kind="headerNoPadding"] {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    color: {t.SLATE_BLUE} !important;
    font-family: {t.FONT_UI} !important;
    font-size: 0.85em !important;
    font-weight: 500 !important;
    opacity: 1 !important;
    visibility: visible !important;
}}

/* Override Streamlit's hover-only fade-in on the in-sidebar collapse btn */
section[data-testid="stSidebar"] button[kind="headerNoPadding"],
section[data-testid="stSidebar"] [data-testid="stCollapseSidebarButton"],
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button {{
    opacity: 1 !important;
    visibility: visible !important;
    transition: none !important;
}}

button[data-testid="stCollapseSidebarButton"]::before,
section[data-testid="stSidebar"] button[kind="headerNoPadding"]::before {{
    content: "Collapse" !important;
    color: {t.SLATE_BLUE} !important;
    font-family: {t.FONT_UI} !important;
    font-weight: 500 !important;
    font-size: 0.85em !important;
    padding-right: 4px !important;
    white-space: nowrap !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
    padding-top: 0.5rem;
}}

/* Tighten Streamlit column gaps */
[data-testid="stHorizontalBlock"] {{
    gap: 0.5rem !important;
}}

/* Tighten vertical spacing between blocks */
[data-testid="stVerticalBlock"] > [data-testid="element-container"] {{
    margin-bottom: 0.1rem;
}}

/* FIXED brand header + tabs — position: sticky is unreliable inside
   Streamlit's container hierarchy (silently clipped by emotion-cache
   wrappers in unpredictable ways across versions). Using position: fixed
   pins both elements to the viewport regardless of container behavior. */

.trace-sticky-top {{
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 100 !important;
    background: {t.MIST_WHITE} !important;
    margin: 0 !important;
    padding: 0 !important;
    border-bottom: 1px solid {t.COOL_GRAY}55 !important;
}}

/* Make Streamlit's app header thin and transparent so our brand sits at
   the top, but DON'T hide stToolbar entirely — it contains the sidebar
   Filters/expand button which we need to keep visible. */
header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 0 !important;
    min-height: 0 !important;
    overflow: visible !important;  /* let the Filters button render outside */
}}

/* Hide Streamlit Cloud's dev decorations (Share, star, edit, GitHub,
   kebab menu, status widget) — none of these are useful for end users.
   Target each container by testid so the Filters expand button (also a
   child of stToolbar) stays untouched. */
[data-testid="stDecoration"],
[data-testid="stToolbarActions"],
[data-testid="stStatusWidget"],
[data-testid="stMainMenu"],
header[data-testid="stHeader"] [data-testid="stToolbarActionButton"],
header[data-testid="stHeader"] [data-testid="stAppDeployButton"],
[data-testid="stAppDeployButton"] {{
    display: none !important;
}}

/* Filters / sidebar expand button — tucked into the top-right of the
   brand header row, to the left of the mode pills. */
button[data-testid="stExpandSidebarButton"] {{
    position: fixed !important;
    top: 0.55rem !important;
    right: 19rem !important;
    z-index: 101 !important;
    margin: 0 !important;
}}

.trace-demo-banner {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 100;
    background: {t.MIST_WHITE};
    border-top: 1px solid {t.COOL_GRAY}55;
    padding: 3px 24px;
    font-family: {t.FONT_UI};
    font-size: 0.72em;
    color: {t.SLATE_BLUE};
    text-align: center;
    letter-spacing: 0.02em;
    line-height: 1.2;
}}

.trace-demo-banner strong {{
    color: {t.SLATE_BLUE};
    letter-spacing: 0.06em;
}}

.trace-header-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 24px 4px 24px;
    background: {t.MIST_WHITE};
}}

.trace-brand-block {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.trace-brand-block .wordmark {{
    font-family: {t.FONT_HEADING};
    font-size: 1.3em;
    font-weight: 700;
    color: {t.PRIMARY_NAVY};
    letter-spacing: 0.02em;
}}

.trace-brand-block .sub {{
    font-family: {t.FONT_UI};
    font-size: 0.78em;
    color: {t.SLATE_BLUE};
    border-left: 1px solid {t.COOL_GRAY};
    padding-left: 12px;
    margin-left: 6px;
}}

.trace-mode-pills {{
    display: flex;
    gap: 18px;
    font-family: {t.FONT_UI};
    font-size: 0.85em;
}}

.trace-mode-pills a {{
    color: {t.SLATE_BLUE};
    text-decoration: none;
    font-weight: 500;
    padding: 4px 0;
    border-bottom: 2px solid transparent;
}}

.trace-mode-pills a.active {{
    color: {t.PRIMARY_NAVY};
    font-weight: 600;
    border-bottom-color: {t.CLINICAL_CORAL};
}}

/* Context pill (top-right of nav strip) */
.trace-ctx-pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: {t.COOL_GRAY}22;
    border-radius: 16px;
    padding: 4px 14px;
    font-family: {t.FONT_UI};
    font-size: 0.82em;
    color: {t.SLATE_BLUE};
}}

.trace-ctx-pill .dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: {t.SOFT_GREEN};
    display: inline-block;
}}
</style>
"""


# ----- Sticky brand header + mode pills -----

def _sticky_header(mode: str) -> None:
    investor_class = "active" if mode == "investor" else ""
    ehr_class = "active" if mode == "ehr_sandbox" else ""

    st.markdown(
        f'<div class="trace-sticky-top">'
        f'<div class="trace-header-row">'
        f'<div class="trace-brand-block">'
        f'<div style="display:inline-block; width:24px; height:24px;">{t.LOGO_SVG_SMALL}</div>'
        f'<span class="wordmark">TRACE</span>'
        f'</div>'
        f'<div class="trace-mode-pills">'
        f'<a class="{investor_class}" href="?mode=investor" target="_self">Investor Demo</a>'
        f'<a class="{ehr_class}" href="?mode=ehr_sandbox" target="_self">EHR Sandbox</a>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ----- Fixed bottom status bar: DEMO DATA notice -----

def _demo_footer_banner() -> None:
    st.markdown(
        f'<div class="trace-demo-banner">'
        f'<strong>DEMO DATA</strong>'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;Illustrative only'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;Not live clinical data'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;Values are synthetic, geographically plausible'
        f'</div>',
        unsafe_allow_html=True,
    )


# ----- Sidebar: shared filters (Investor Demo only) -----

DEMO_SCENARIOS = {
    "— pick a demo scenario —": None,
    "ED pneumonia in Salt Lake County": {
        "counties": ["Salt Lake"],
        "encounter": "ED",
        "specimen": "Respiratory",
        "organism": "Streptococcus pneumoniae",
    },
    "Outpatient UTI across the Wasatch Front": {
        "counties": ["Salt Lake", "Utah"],
        "encounter": "Outpatient",
        "specimen": "Urine",
        "organism": "Escherichia coli",
    },
    "ICU pneumonia, Pseudomonas risk": {
        "counties": ["Salt Lake"],
        "encounter": "ICU",
        "specimen": "Respiratory",
        "organism": "Pseudomonas aeruginosa",
    },
    "S. aureus bacteremia, statewide": {
        "counties": ["Salt Lake", "Utah", "Washington"],
        "encounter": "Inpatient",
        "specimen": "Blood",
        "organism": "Staphylococcus aureus",
    },
    "Group A Strep pharyngitis, outpatient": {
        "counties": ["Salt Lake", "Utah", "Washington"],
        "encounter": "Outpatient",
        "specimen": "Throat",
        "organism": "Group A Strep",
    },
    "C. difficile, inpatient stewardship review": {
        "counties": ["Salt Lake"],
        "encounter": "Inpatient",
        "specimen": "Stool",
        "organism": "C. difficile",
    },
}


def render_sidebar() -> dict:
    """Render shared global filters; return the active filter state."""
    with st.sidebar:
        st.markdown(
            f'<div style="font-family: {t.FONT_HEADING}; '
            f'color: {t.PRIMARY_NAVY}; font-weight: 600; '
            f'font-size: 1.05em; margin-bottom: 0.4rem;">Filters</div>',
            unsafe_allow_html=True,
        )

        scenario_choice = st.selectbox(
            "Demo scenario",
            options=list(DEMO_SCENARIOS.keys()),
            index=0,
            help="Pre-set views for investors and clinical reviewers. "
                 "Selecting a scenario overrides the filters below.",
        )
        scenario = DEMO_SCENARIOS[scenario_choice]

        st.caption("Or set filters manually:")

        all_counties = ["Salt Lake", "Utah", "Washington"]
        counties = st.multiselect(
            "County",
            options=all_counties,
            default=scenario["counties"] if scenario else all_counties,
        )

        encounter_options = ["ED", "ICU", "Inpatient", "Outpatient"]
        encounter = st.selectbox(
            "Encounter setting",
            options=encounter_options,
            index=encounter_options.index(scenario["encounter"]) if scenario else 0,
        )

        specimen_options = ["Blood", "Nares", "Respiratory", "Stool",
                            "Throat", "Urine", "Wound"]
        specimen = st.selectbox(
            "Specimen type",
            options=specimen_options,
            index=specimen_options.index(scenario["specimen"]) if scenario else 5,
        )

        organism_options = [
            "Escherichia coli",
            "Klebsiella pneumoniae",
            "Staphylococcus aureus",
            "MRSA",
            "Streptococcus pneumoniae",
            "Pseudomonas aeruginosa",
            "Enterococcus species",
            "Haemophilus influenzae",
            "Group A Strep",
            "C. difficile",
        ]
        organism = st.selectbox(
            "Organism",
            options=organism_options,
            index=organism_options.index(scenario["organism"]) if scenario else 0,
        )

        st.markdown("---")
        st.caption(
            "Running on a fully synthetic, statistically calibrated dataset. "
            "See **About & Architecture** for sources."
        )

    return {
        "counties": counties,
        "encounter_setting": encounter,
        "specimen_type": specimen,
        "organism": organism,
        "scenario_label": scenario_choice if scenario else None,
    }


# ----- Main -----

def _resolve_mode() -> str:
    """Resolve current mode from query params or session state."""
    qp = st.query_params
    if "mode" in qp:
        m = qp["mode"]
        if m in ("investor", "ehr_sandbox"):
            st.session_state["mode"] = m
    return st.session_state.get("mode", "investor")


def _resolve_drilldown() -> None:
    """If the user clicked a ZIP bubble on the map, capture the drill-down
    intent from query params into session_state. The query params get
    cleared so a refresh doesn't re-trigger the drill-down."""
    qp = st.query_params
    if "focus_zip" in qp:
        zip_code = qp["focus_zip"]
        organism = qp.get("focus_organism", "")
        # Look up county for the ZIP
        zip_map = dl.load_zip_county_map()
        county = "—"
        if not zip_map.empty:
            match = zip_map[zip_map["zip"] == zip_code]
            if not match.empty:
                county = match.iloc[0]["county"]
        st.session_state["drilldown"] = {
            "zip": zip_code,
            "organism": organism,
            "county": county,
        }
        # Clear so refresh doesn't re-trigger
        for k in ("focus_zip", "focus_organism"):
            if k in qp:
                del st.query_params[k]
    if "clear_drilldown" in qp:
        st.session_state.pop("drilldown", None)
        if "clear_drilldown" in qp:
            del st.query_params["clear_drilldown"]


def _drilldown_banner() -> None:
    """Show a TRACE-branded banner when a ZIP drill-down is active."""
    dd = st.session_state.get("drilldown")
    if not dd:
        return
    st.markdown(
        f'<div style="background: {t.TRACE_TEAL}1A; '
        f'border: 1px solid {t.TRACE_TEAL}; border-radius: 6px; '
        f'padding: 10px 16px; margin: 0.5rem 0 1rem 0; '
        f'font-family: {t.FONT_UI}; font-size: 0.9em; '
        f'display: flex; justify-content: space-between; '
        f'align-items: center; gap: 12px;">'
        f'<div>'
        f'<strong style="color: {t.PRIMARY_NAVY};">'
        f'Drilling down:</strong> '
        f'<span style="color: {t.INK};">'
        f'{dd["organism"] or "all organisms"} in ZIP <strong>{dd["zip"]}</strong> '
        f'({dd["county"]} County)'
        f'</span>'
        f'<span style="color: {t.SLATE_BLUE}; margin-left: 12px; '
        f'font-size: 0.88em;">Switch to <strong>Clinical Context View</strong> '
        f'for local susceptibility detail on this scope.</span>'
        f'</div>'
        f'<a href="?clear_drilldown=1" target="_self" '
        f'style="background: white; border: 1px solid {t.COOL_GRAY}; '
        f'color: {t.SLATE_BLUE}; padding: 4px 12px; border-radius: 4px; '
        f'font-size: 0.82em; font-weight: 500; text-decoration: none;">'
        f'Clear ×</a>'
        f'</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    # Inject CSS once
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    if dl.find_data_dir() is None:
        st.error(
            "Could not locate the synthetic dataset. Set the `TRACE_DATA_DIR` "
            "environment variable to point at `trace_poc_data/`, or copy / "
            "symlink the dataset into `./data/utah_synthetic/`."
        )
        st.stop()

    mode = _resolve_mode()
    _sticky_header(mode)

    if mode == "ehr_sandbox":
        # EHR Sandbox doesn't use the standard sidebar filters
        ehr_sandbox.render({})
        return

    # Investor Demo mode: read drill-down state from query params (if any),
    # then render the shared sidebar + tabs.
    _resolve_drilldown()
    filters = render_sidebar()

    # If a drill-down is active, override the filters' organism + county
    dd = st.session_state.get("drilldown")
    if dd:
        if dd.get("organism"):
            filters["organism"] = dd["organism"]
        if dd.get("county") and dd["county"] != "—":
            filters["counties"] = [dd["county"]]

    _drilldown_banner()

    tabs = st.tabs([
        "About & Architecture",
        "Today vs TRACE",
        "Resistance Weather Map",
        "Stewardship View",
        "Clinical Context View",
    ])
    with tabs[0]:
        about_architecture.render(filters)
    with tabs[1]:
        today_vs_trace.render(filters)
    with tabs[2]:
        weather_map.render(filters)
    with tabs[3]:
        stewardship.render(filters)
    with tabs[4]:
        clinical_context.render(filters)

    _demo_footer_banner()


if __name__ == "__main__":
    main()
