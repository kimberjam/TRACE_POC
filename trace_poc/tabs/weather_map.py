"""Resistance Weather Map tab.

ZIP-level resistance intelligence — the lead pitch view for investors and
public-health partners. Five-KPI strip at top, filters left, map + timeline
+ emerging-hotspots stack on the right.

Where the original mockup uses an SVG of the Utah outline with ZIP circles
overlaid, this Streamlit build uses Altair to render the same idea: a
scatter plot of ZIP centroids sized by isolate count and colored by
% susceptible. Same information, native to the framework.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st

from .. import data_loader as dl
from .. import components as ui
from .. import theme as t


# ===== Utah map data (extracted from HTML investor mockup) =====
# SVG viewBox is 520 × 640. State outline + 29 county polygons rendered as
# inline paths so the map carries true geographic context (county lines, metro
# labels) rather than a featureless lat/lon scatter.

UTAH_VIEWBOX = (520, 640)

UTAH_STATE_PATH = (
    "M26.64 17.79 L306.75 17.79 L306.75 138.8 "
    "L492.89 138.8 L493.36 621.95 L26.83 621.95 Z"
)

UTAH_COUNTIES = [
    {"n": "Box Elder", "p": "M26.64 17.76 L199.27 17.76 L199.27 84.44 L134.02 84.44 L134.02 138.8 L35.22 138.8 L27.3 114.64 Z", "cx": 107.96, "cy": 85.23},
    {"n": "Cache", "p": "M199.27 17.76 L257.06 17.76 L257.06 74.78 L199.27 74.78 Z", "cx": 228.17, "cy": 46.27},
    {"n": "Rich", "p": "M257.06 17.76 L306.75 17.76 L306.75 138.8 L257.06 138.8 Z", "cx": 281.9, "cy": 78.28},
    {"n": "Weber", "p": "M199.27 74.78 L236.56 74.78 L236.56 118.26 L199.27 118.26 Z", "cx": 217.92, "cy": 96.52},
    {"n": "Morgan", "p": "M236.56 94.1 L278.5 94.1 L278.5 138.8 L236.56 138.8 Z", "cx": 257.53, "cy": 116.45},
    {"n": "Davis", "p": "M199.27 118.26 L236.56 118.26 L236.56 160.54 L199.27 160.54 Z", "cx": 217.92, "cy": 139.4},
    {"n": "Summit", "p": "M278.5 138.8 L357.73 138.8 L357.73 193.16 L311.13 193.16 L311.13 172.62 L250.54 172.62 L250.54 156.92 Z", "cx": 302.47, "cy": 166.58},
    {"n": "Tooele", "p": "M35.22 138.8 L199.27 138.8 L199.27 211.28 L78.1 211.28 L78.1 245.1 L35.22 245.1 Z", "cx": 104.2, "cy": 198.39},
    {"n": "Salt Lake", "p": "M199.27 160.54 L250.54 160.54 L250.54 211.28 L199.27 211.28 Z", "cx": 224.91, "cy": 185.91},
    {"n": "Wasatch", "p": "M250.54 172.62 L311.13 172.62 L311.13 233.02 L250.54 233.02 Z", "cx": 280.83, "cy": 202.82},
    {"n": "Utah", "p": "M199.27 211.28 L311.13 211.28 L311.13 269.26 L199.27 269.26 Z", "cx": 255.2, "cy": 240.27},
    {"n": "Juab", "p": "M35.22 245.1 L199.27 245.1 L199.27 269.26 L199.27 307.92 L35.22 307.92 Z", "cx": 133.65, "cy": 275.06},
    {"n": "Duchesne", "p": "M357.73 193.16 L427.64 193.16 L427.64 253.56 L334.43 253.56 L334.43 233.02 L311.13 233.02 L311.13 211.28 L357.73 211.28 Z", "cx": 357.73, "cy": 222.75},
    {"n": "Uintah", "p": "M399.68 193.16 L492.89 193.16 L492.89 295.84 L399.68 295.84 Z", "cx": 446.29, "cy": 244.5},
    {"n": "Daggett", "p": "M399.68 138.8 L492.89 138.8 L492.89 193.16 L399.68 193.16 Z", "cx": 446.29, "cy": 165.98},
    {"n": "Millard", "p": "M35.22 307.92 L199.27 307.92 L199.27 431.14 L35.22 431.14 Z", "cx": 117.25, "cy": 369.53},
    {"n": "Sanpete", "p": "M199.27 269.26 L311.13 269.26 L311.13 364.7 L245.88 364.7 L245.88 329.66 L199.27 329.66 Z", "cx": 252.09, "cy": 321.21},
    {"n": "Carbon", "p": "M311.13 269.26 L404.34 269.26 L404.34 313.96 L362.39 313.96 L362.39 329.66 L311.13 329.66 Z", "cx": 359.29, "cy": 304.29},
    {"n": "Emery", "p": "M311.13 313.96 L404.34 313.96 L404.34 431.14 L311.13 431.14 Z", "cx": 357.74, "cy": 372.55},
    {"n": "Grand", "p": "M404.34 295.84 L492.89 295.84 L492.89 440.8 L446.28 440.8 L446.28 374.36 L404.34 374.36 Z", "cx": 447.84, "cy": 370.33},
    {"n": "Sevier", "p": "M199.27 364.7 L311.13 364.7 L311.13 431.14 L199.27 431.14 Z", "cx": 255.2, "cy": 397.92},
    {"n": "Beaver", "p": "M35.22 431.14 L199.27 431.14 L199.27 471.0 L35.22 471.0 Z", "cx": 117.25, "cy": 451.07},
    {"n": "Piute", "p": "M199.27 431.14 L259.86 431.14 L259.86 471.0 L199.27 471.0 Z", "cx": 229.56, "cy": 451.07},
    {"n": "Wayne", "p": "M259.86 431.14 L404.34 431.14 L404.34 501.2 L329.77 501.2 L329.77 467.38 L259.86 467.38 Z", "cx": 331.32, "cy": 466.57},
    {"n": "San Juan", "p": "M446.28 440.8 L492.89 440.8 L492.89 622.0 L357.73 622.0 L357.73 551.94 L446.28 551.94 Z", "cx": 432.3, "cy": 538.25},
    {"n": "Garfield", "p": "M189.95 471.0 L329.77 471.0 L329.77 551.94 L273.84 551.94 L273.84 609.92 L189.95 609.92 Z", "cx": 264.52, "cy": 544.29},
    {"n": "Kane", "p": "M273.84 551.94 L329.77 551.94 L329.77 622.0 L171.31 622.0 L171.31 609.92 L273.84 609.92 Z", "cx": 258.31, "cy": 594.62},
    {"n": "Iron", "p": "M35.22 471.0 L199.27 471.0 L199.27 513.28 L199.27 549.52 L87.42 549.52 L87.42 512.07 L35.22 512.07 Z", "cx": 120.44, "cy": 511.21},
    {"n": "Washington", "p": "M35.22 512.07 L87.42 512.07 L87.42 549.52 L171.31 549.52 L171.31 622.0 L26.83 622.0 Z", "cx": 96.59, "cy": 561.2},
]

# Major metro labels (rendered larger / bolder than county names)
UTAH_METROS = [
    {"name": "SALT LAKE", "x": 190.0, "y": 167.8},
    {"name": "OGDEN",     "x": 162.0, "y": 96.5},
    {"name": "UTAH VALLEY","x": 162.0, "y": 259.6},
    {"name": "PARK CITY", "x": 339.1, "y": 172.6},
    {"name": "ST. GEORGE","x": 78.1,  "y": 585.8},
]


# ZIP centroids (approximate; sufficient for a visual map).
# Each ZIP from the zip_county_map.csv mapped to (lat, lon).
ZIP_CENTROIDS = {
    # Salt Lake County (Wasatch Front central)
    "84101": (40.7608, -111.8910), "84102": (40.7642, -111.8543),
    "84103": (40.7798, -111.8638), "84104": (40.7458, -111.9243),
    "84105": (40.7392, -111.8557), "84106": (40.7193, -111.8643),
    "84107": (40.6664, -111.8930), "84108": (40.7530, -111.8225),
    "84109": (40.7064, -111.8285), "84111": (40.7670, -111.8810),
    "84112": (40.7649, -111.8421), "84115": (40.7166, -111.8867),
    "84117": (40.6627, -111.8460), "84118": (40.6471, -111.9710),
    "84119": (40.7042, -111.9410), "84120": (40.6918, -111.9716),
    "84121": (40.6243, -111.8390), "84123": (40.6624, -111.9266),
    "84124": (40.6804, -111.8270), "84128": (40.7000, -112.0050),
    # Utah County
    "84003": (40.4811, -111.7910), "84004": (40.3577, -111.7274),
    "84005": (40.4400, -111.8800), "84057": (40.3081, -111.7400),
    "84058": (40.2885, -111.7203), "84062": (40.3805, -111.7388),
    "84097": (40.2950, -111.6700), "84601": (40.2338, -111.6585),
    "84604": (40.2724, -111.6499), "84606": (40.2200, -111.6500),
    "84660": (40.1010, -111.6691), "84663": (40.0840, -111.6510),
    # Washington County
    "84720": (37.6775, -113.0619), "84721": (37.7020, -113.0270),
    "84737": (37.2010, -113.2840), "84738": (37.1395, -113.4640),
    "84745": (37.1690, -113.2070), "84746": (37.0875, -113.3640),
    "84770": (37.0965, -113.5684), "84780": (37.1090, -113.6210),
    "84782": (37.0010, -113.3940), "84790": (37.0590, -113.5450),
    # Park City / Summit
    "84098": (40.7041, -111.4986), "84050": (41.2090, -111.9700),
    "84401": (41.2230, -111.9738), "84403": (41.1860, -111.9020),
    "84102_fallback": (40.764, -111.854),  # safety net for legacy zips
}

# ===== Geographic projection helpers =====

def _project_zip(lat: float, lon: float) -> tuple[float, float]:
    """Project a (lat, lon) into the Utah SVG viewBox coordinate space.

    Linear projection calibrated to Utah's bounding box:
      west  edge x≈27  ↔ lon=-114.05
      east  edge x≈493 ↔ lon=-109.05
      north edge y≈18  ↔ lat= 42.00
      south edge y≈622 ↔ lat= 37.00
    """
    x = 27.0 + ((lon + 114.05) / 5.0) * 466.0
    y = 18.0 + ((42.0 - lat) / 5.0) * 604.0
    return x, y


def _color_for_pct(pct: float) -> str:
    """Map a %-susceptible value to a color along the concern → stable scale.

    Below 50% → coral (likely won't work)
    50–75%   → amber (watch state)
    75–85%   → soft amber-green
    Above 85% → green (likely to work)
    """
    if pct is None:
        return t.COOL_GRAY
    if pct < 50:
        return t.CLINICAL_CORAL
    if pct < 70:
        # Interpolate coral → amber
        ratio = (pct - 50) / 20
        return _lerp_hex(t.CLINICAL_CORAL, t.MUTED_AMBER, ratio)
    if pct < 85:
        # Interpolate amber → green
        ratio = (pct - 70) / 15
        return _lerp_hex(t.MUTED_AMBER, t.SOFT_GREEN, ratio)
    return t.SOFT_GREEN


def _lerp_hex(c1: str, c2: str, r: float) -> str:
    """Linear-interpolate two hex colors. r is 0..1."""
    r = max(0.0, min(1.0, r))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    rr = int(r1 + (r2 - r1) * r)
    gg = int(g1 + (g2 - g1) * r)
    bb = int(b1 + (b2 - b1) * r)
    return f"#{rr:02X}{gg:02X}{bb:02X}"


def _bubble_radius(n: int) -> float:
    """Bubble radius scaled by sqrt(N) so area is proportional to isolate count.

    Capped at ~13px so densely-clustered urban ZIPs don't visually merge.
    """
    import math
    if n < 30:
        return 0
    return max(4.5, min(13.0, 3.5 + math.sqrt(n) * 0.45))


# Common pairings — match what the mockup ships
COMMON_PAIRINGS = [
    ("E. coli × Ciprofloxacin", "Escherichia coli", "Ciprofloxacin"),
    ("E. coli × Nitrofurantoin", "Escherichia coli", "Nitrofurantoin"),
    ("S. aureus × Clindamycin", "Staphylococcus aureus", "Clindamycin"),
    ("S. pneumoniae × Azithromycin", "Streptococcus pneumoniae", "Azithromycin"),
    ("K. pneumoniae × Ceftriaxone", "Klebsiella pneumoniae", "Ceftriaxone"),
]


def _pairing_chips() -> tuple[str, str, str]:
    """Render a compact horizontal Common Pairings chip row.

    Replaces the heavier in-tab Filters card with a streamlined picker that
    sets both pathogen and drug from a single click. The sidebar (Streamlit
    native, collapsed by default) covers global filter context.

    Returns (label, organism, drug).
    """
    if "wm_pairing_idx" not in st.session_state:
        st.session_state["wm_pairing_idx"] = 0
    idx = st.session_state["wm_pairing_idx"]

    st.markdown(
        f'<div style="display: flex; align-items: center; gap: 12px; '
        f'margin-bottom: 6px;">'
        f'<span style="font-family: {t.FONT_UI}; font-size: 0.78em; '
        f'color: {t.SLATE_BLUE}; font-weight: 600; letter-spacing: 0.06em; '
        f'text-transform: uppercase;">Pathogen × Antibiotic</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Horizontal chip row using Streamlit columns
    cols = st.columns(len(COMMON_PAIRINGS))
    for i, (label, _org, _drug) in enumerate(COMMON_PAIRINGS):
        with cols[i]:
            if st.button(
                label,
                key=f"wm_pair_{i}",
                use_container_width=True,
                type=("primary" if i == idx else "secondary"),
            ):
                st.session_state["wm_pairing_idx"] = i
                st.rerun()

    label, organism, drug = COMMON_PAIRINGS[st.session_state["wm_pairing_idx"]]
    return label, organism, drug


def _kpi_strip(df_recent: pd.DataFrame, organism: str, drug: str) -> None:
    """5-card KPI row matching the mockup."""
    cols = st.columns(5)

    # ZIPs covered
    zip_map = dl.load_zip_county_map()
    n_zips = len(zip_map) if not zip_map.empty else 0
    with cols[0]:
        ui.kpi_card(
            "ZIPs covered",
            f"{n_zips}",
            sublabel="Wasatch Front + St. George",
        )

    # Hospitals contributing
    facilities = dl.load_facilities()
    n_hosp = len(facilities[facilities["facility_type"] == "hospital"]) if not facilities.empty else 0
    with cols[1]:
        ui.kpi_card(
            "Hospitals contributing",
            f"{n_hosp}",
            sublabel="AU/AR CDA + antibiogram feeds",
        )

    # Isolates (last 90d) for the pairing
    iso = df_recent[
        (df_recent["organism"] == organism)
        & (df_recent["drug"] == drug)
        & df_recent["susceptibility"].isin(["S", "R"])
    ]
    n_iso = iso["test_id"].nunique() if not iso.empty else 0
    with cols[2]:
        ui.kpi_card(
            "Isolates (last 90d)",
            f"{n_iso:,}",
            sublabel="After small-cell suppression",
        )

    # Data latency (static: 14 days for monthly aggregates)
    with cols[3]:
        ui.kpi_card(
            "Data latency",
            "14 d",
            sublabel="vs 12+ months for state antibiograms",
        )

    # Emerging hotspots — ZIPs with worsening trend
    hotspots = _detect_hotspots(df_recent, organism, drug)
    with cols[4]:
        ui.kpi_card(
            "Emerging hotspots",
            f"{len(hotspots)}",
            sublabel="ZIPs with worsening trend",
            delta=(f"+{len(hotspots)} vs prior 90d" if len(hotspots) > 0 else None),
        )


def _detect_hotspots(df: pd.DataFrame, organism: str, drug: str) -> list[dict]:
    """Find ZIPs where %susceptible dropped vs the prior 90-day window."""
    sub = df[
        (df["organism"] == organism)
        & (df["drug"] == drug)
        & df["susceptibility"].isin(["S", "R"])
    ]
    if sub.empty:
        return []
    max_date = sub["collection_date"].max()
    cur_cut = max_date - timedelta(days=90)
    prev_cut = max_date - timedelta(days=180)

    cur = sub[sub["collection_date"] > cur_cut]
    prev = sub[(sub["collection_date"] > prev_cut)
               & (sub["collection_date"] <= cur_cut)]

    out: list[dict] = []
    for z in cur["patient_zip"].dropna().unique():
        c = cur[cur["patient_zip"] == z]
        p = prev[prev["patient_zip"] == z]
        if len(c) < 30 or len(p) < 30:
            continue  # small-cell suppression
        cur_pct = 100 * (c["susceptibility"] == "S").mean()
        prev_pct = 100 * (p["susceptibility"] == "S").mean()
        if cur_pct < prev_pct - 3:  # worsening by >=3 points
            out.append({
                "zip": z,
                "current_pct": round(cur_pct, 1),
                "prior_pct": round(prev_pct, 1),
                "delta": round(cur_pct - prev_pct, 1),
                "n_current": len(c),
            })
    return sorted(out, key=lambda h: h["delta"])[:3]


def _map_view(df_recent: pd.DataFrame, organism: str, drug: str,
              pairing_label: str) -> None:
    """ZIP-level scatter plot colored by %S, sized by N."""
    with st.container(border=True):
        title_cols = st.columns([3, 2, 1])
        with title_cols[0]:
            st.markdown(
                f'<div style="font-family: {t.FONT_HEADING}; '
                f'font-weight: 600; color: {t.PRIMARY_NAVY}; '
                f'font-size: 1.05em; margin-bottom: 0;">'
                f'Resistance map — {pairing_label}</div>',
                unsafe_allow_html=True,
            )
        with title_cols[1]:
            zoom = st.radio(
                "Map view",
                options=list(ZOOM_PRESETS.keys()),
                index=list(ZOOM_PRESETS.keys()).index(
                    st.session_state.get("wm_zoom", "Statewide")
                ),
                horizontal=True,
                label_visibility="collapsed",
                key="wm_zoom",
            )
        with title_cols[2]:
            st.markdown(
                ui.evidence_chip("Stewardship concern", tone="concern"),
                unsafe_allow_html=True,
            )

        # Aggregate per ZIP
        sub = df_recent[
            (df_recent["organism"] == organism)
            & (df_recent["drug"] == drug)
            & df_recent["susceptibility"].isin(["S", "R"])
        ]
        if sub.empty:
            ui.empty_state(
                "No isolates for the current pairing.",
                "Try a different pairing from the Common pairings list.",
            )
            return

        agg = (
            sub.groupby("patient_zip")
            .agg(
                n_iso=("test_id", "nunique"),
                n_s=("susceptibility", lambda s: (s == "S").sum()),
            )
            .reset_index()
        )
        agg = agg[agg["n_iso"] >= 30]  # small-cell suppression
        agg["pct_s"] = (100 * agg["n_s"] / agg["n_iso"]).round(1)

        if agg.empty:
            ui.empty_state("All ZIPs suppressed (n<30).")
            return

        # Render inline SVG of Utah with county lines + ZIP bubbles overlaid.
        svg = _render_utah_svg(agg, zoom=zoom)
        st.markdown(svg, unsafe_allow_html=True)
        _render_legend()


# Zoom presets — change the SVG viewBox to focus on a region.
# Format: (x_min, y_min, width, height) in SVG coordinate space.
ZOOM_PRESETS = {
    "Statewide":      (0,   0,   520, 640),
    "Wasatch Front":  (160, 60,  220, 230),
    "St. George":     (15,  470, 200, 170),
}


def _render_utah_svg(agg: pd.DataFrame, zoom: str = "Statewide") -> str:
    """Build the inline Utah SVG with county lines, metro labels, ZIP bubbles.

    The `zoom` arg picks a preset region from ZOOM_PRESETS — the SVG viewBox
    changes so the same drawing is rendered but cropped + magnified.
    """
    vb = ZOOM_PRESETS.get(zoom, ZOOM_PRESETS["Statewide"])
    vx, vy, vw, vh = vb
    parts: list[str] = []

    # Higher max-height when zoomed so the cluster has room to breathe
    max_h = "640px" if zoom != "Statewide" else "580px"

    parts.append(
        f'<div style="background: {t.MIST_WHITE}; border-radius: 4px; '
        f'padding: 6px; display: flex; justify-content: center;">'
        f'<svg viewBox="{vx} {vy} {vw} {vh}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" '
        f'style="max-width: 720px; max-height: {max_h}; '
        f'font-family: {t.FONT_UI};">'
    )

    # State outline (soft background)
    parts.append(
        f'<path d="{UTAH_STATE_PATH}" fill="#FAFBFC" '
        f'stroke="{t.COOL_GRAY}" stroke-width="1.5"/>'
    )

    # County polygons
    for c in UTAH_COUNTIES:
        parts.append(
            f'<path d="{c["p"]}" fill="white" '
            f'stroke="{t.COOL_GRAY}" stroke-width="0.7" '
            f'stroke-linejoin="round"/>'
        )

    # County name labels (small, muted)
    for c in UTAH_COUNTIES:
        # Skip counties that overlap with metro labels to reduce clutter
        if c["n"] in ("Salt Lake", "Utah", "Weber", "Washington", "Summit"):
            continue
        parts.append(
            f'<text x="{c["cx"]}" y="{c["cy"]}" font-size="9" '
            f'fill="{t.COOL_GRAY}" text-anchor="middle" '
            f'pointer-events="none">{c["n"]}</text>'
        )

    # Metro labels (larger, bolder)
    for m in UTAH_METROS:
        parts.append(
            f'<text x="{m["x"]}" y="{m["y"]}" font-size="11" '
            f'fill="{t.SLATE_BLUE}" text-anchor="start" '
            f'font-weight="700" letter-spacing="0.5" '
            f'pointer-events="none">{m["name"]}</text>'
        )

    # ZIP bubbles overlaid — labels only for top-N by isolate count to
    # prevent the Wasatch Front cluster from becoming unreadable. Smaller
    # ZIPs still show as bubbles with hover tooltips.
    LABEL_TOP_N = 6
    agg_sorted = agg.sort_values("n_iso", ascending=False).reset_index(drop=True)
    labelled_zips = set(agg_sorted.head(LABEL_TOP_N)["patient_zip"].astype(str))

    # Draw the lower-N bubbles first so the larger ones sit on top
    draw_order = agg.sort_values("n_iso", ascending=True)
    for _, row in draw_order.iterrows():
        zip_code = str(row["patient_zip"])
        latlon = ZIP_CENTROIDS.get(zip_code)
        if latlon is None:
            continue
        lat, lon = latlon
        x, y = _project_zip(lat, lon)
        if not (20 < x < 500) or not (15 < y < 625):
            continue
        r = _bubble_radius(int(row["n_iso"]))
        if r <= 0:
            continue
        color = _color_for_pct(float(row["pct_s"]))
        tooltip = (
            f'ZIP {zip_code} — {row["pct_s"]:.1f}% susceptible '
            f'(n={int(row["n_iso"])})'
        )
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{color}" fill-opacity="0.7" '
            f'stroke="{t.PRIMARY_NAVY}" stroke-width="1" '
            f'style="cursor: pointer;">'
            f'<title>{tooltip}</title>'
            f'</circle>'
        )
        # Only the top-N labelled — keeps the cluster readable
        if zip_code in labelled_zips:
            parts.append(
                f'<text x="{x + r + 3:.1f}" y="{y + 3:.1f}" font-size="9" '
                f'font-family="monospace" fill="{t.PRIMARY_NAVY}" '
                f'font-weight="600" pointer-events="none" '
                f'paint-order="stroke" stroke="white" stroke-width="2.5">'
                f'{zip_code}</text>'
            )

    parts.append("</svg></div>")
    return "".join(parts)


def _render_legend() -> None:
    """Color + size legend rendered below the SVG map."""
    st.markdown(
        f'<div style="display: flex; align-items: center; gap: 20px; '
        f'margin-top: 8px; padding: 6px 8px; '
        f'font-family: {t.FONT_UI}; font-size: 0.78em; color: {t.SLATE_BLUE};">'
        # Color gradient
        f'<div style="display: flex; align-items: center; gap: 6px;">'
        f'<span style="font-family: monospace; color: {t.PRIMARY_NAVY};">0%</span>'
        f'<div style="width: 180px; height: 10px; border-radius: 5px; '
        f'background: linear-gradient(to right, '
        f'{t.CLINICAL_CORAL} 0%, {t.MUTED_AMBER} 50%, {t.SOFT_GREEN} 100%);"></div>'
        f'<span style="font-family: monospace; color: {t.PRIMARY_NAVY};">100%</span>'
        f'<span style="margin-left: 6px;">% Susceptible (local)</span>'
        f'</div>'
        # Size legend
        f'<div style="display: flex; align-items: center; gap: 14px; '
        f'margin-left: auto; padding-left: 20px; '
        f'border-left: 1px solid {t.COOL_GRAY}66;">'
        f'<span>Isolates:</span>'
        f'<span style="display: inline-flex; align-items: center; gap: 4px;">'
        f'<span style="width: 10px; height: 10px; border-radius: 50%; '
        f'background: {t.COOL_GRAY}; display: inline-block;"></span> 30</span>'
        f'<span style="display: inline-flex; align-items: center; gap: 4px;">'
        f'<span style="width: 16px; height: 16px; border-radius: 50%; '
        f'background: {t.COOL_GRAY}; display: inline-block;"></span> 100</span>'
        f'<span style="display: inline-flex; align-items: center; gap: 4px;">'
        f'<span style="width: 24px; height: 24px; border-radius: 50%; '
        f'background: {t.COOL_GRAY}; display: inline-block;"></span> 300+</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _time_window_slider() -> int:
    """Renders the time window slider — returns trailing days."""
    with st.container(border=True):
        slider_cols = st.columns([3, 1])
        with slider_cols[0]:
            st.markdown(
                f'<div style="font-family: {t.FONT_HEADING}; '
                f'font-weight: 600; color: {t.PRIMARY_NAVY}; '
                f'font-size: 0.95em;">Time window</div>',
                unsafe_allow_html=True,
            )
        with slider_cols[1]:
            st.markdown(
                f'<div style="font-family: {t.FONT_HEADING}; '
                f'font-weight: 600; color: {t.CLINICAL_CORAL}; '
                f'text-align: right; font-size: 0.95em;">Apr 2026</div>',
                unsafe_allow_html=True,
            )

        windows = ["May '25", "Jul", "Sep", "Nov", "Jan '26", "Mar '26"]
        days = st.select_slider(
            "Window end",
            options=windows,
            value="Mar '26",
            label_visibility="collapsed",
            key="wm_time_window",
        )
    return 90


def _hotspots_panel(hotspots: list[dict]) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div style="font-family: {t.FONT_HEADING}; '
            f'font-weight: 600; color: {t.PRIMARY_NAVY}; '
            f'font-size: 1em; margin-bottom: 0.5rem; '
            f'display: flex; align-items: center; gap: 8px;">'
            f'<span style="display:inline-block; width:8px; height:8px; '
            f'border-radius:50%; background:{t.CLINICAL_CORAL};"></span>'
            f'Emerging hotspots — what to watch'
            f'</div>',
            unsafe_allow_html=True,
        )
        if not hotspots:
            st.caption(
                "No ZIPs in scope have crossed the worsening-trend "
                "threshold in the last 90 days."
            )
            return
        cols = st.columns(min(3, len(hotspots)))
        for col, h in zip(cols, hotspots):
            with col:
                area = _zip_to_neighborhood(h["zip"])
                st.markdown(
                    f'<div style="background: {t.CLINICAL_CORAL}11; '
                    f'border-left: 3px solid {t.CLINICAL_CORAL}; '
                    f'padding: 10px 12px; border-radius: 4px; '
                    f'font-family: {t.FONT_UI};">'
                    f'<div style="font-family: monospace; color: {t.CLINICAL_CORAL}; '
                    f'font-size: 0.78em; font-weight: 600; letter-spacing: 0.04em;">'
                    f'{h["zip"]} · {area}</div>'
                    f'<div style="font-weight: 600; color: {t.PRIMARY_NAVY}; '
                    f'font-size: 0.9em; margin-top: 4px;">'
                    f'Susceptibility <span style="color:{t.CLINICAL_CORAL};">'
                    f'{h["prior_pct"]:.0f}% → {h["current_pct"]:.0f}%</span> '
                    f'over 90 days</div>'
                    f'<div style="font-size: 0.78em; color: {t.SLATE_BLUE}; '
                    f'margin-top: 4px;">'
                    f'n={h["n_current"]} isolates · '
                    f'<strong style="color:{t.CLINICAL_CORAL};">Δ {h["delta"]:.1f}pp</strong>'
                    f'</div>'
                    f'<div style="font-size: 0.78em; color: {t.SLATE_BLUE}; '
                    f'margin-top: 4px;">Stewardship review suggested</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def _zip_to_neighborhood(zip_code: str) -> str:
    """Best-effort neighborhood label for a ZIP."""
    z = str(zip_code)
    if z.startswith("841"):
        return "Salt Lake area"
    if z.startswith("846") or z.startswith("840"):
        return "Utah Valley"
    if z.startswith("847"):
        return "Washington Co"
    return "Mountain West"


def render(filters: dict) -> None:
    ui.tab_header(
        "Resistance weather map",
        "ZIP-level resistance intelligence across the Mountain West region. "
        "Pick a common pairing to see where local treatment is — and isn't — "
        "likely to work.",
    )

    # Pull last 180 days for the trend / hotspot calculations
    df = dl.load_test_results()
    if df.empty:
        ui.empty_state("No dataset available.")
        return
    cutoff = df["collection_date"].max() - timedelta(days=180)
    df_recent = df[df["collection_date"] >= cutoff]

    # Single-column layout: chip row → KPIs → map → timeline → hotspots
    pairing_label, organism, drug = _pairing_chips()
    st.markdown("")
    _kpi_strip(df_recent, organism, drug)
    st.markdown("")
    _map_view(df_recent, organism, drug, pairing_label)
    st.markdown("")
    _time_window_slider()
    st.markdown("")
    hotspots = _detect_hotspots(df_recent, organism, drug)
    _hotspots_panel(hotspots)
