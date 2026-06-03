"""TRACE brand palette and design tokens.

Single source of truth for all color and typography decisions. Every other
module imports from here — never hardcode a color value elsewhere.

Brand rules:
  - Navy carries trust, structure, navigation, and stable frame elements
  - Teal carries active intelligence, selected states, "completed signal"
  - Warm colors (amber, coral) are reserved for true clinical concern —
    never decorative, never general emphasis
  - Cool surfaces (Mist White background, Cool Gray borders) keep the
    interface calm for screen-heavy clinical users
"""

# ===== Primary palette =====
PRIMARY_NAVY = "#071A3D"      # Logo, headers, navigation, trust surfaces
TRACE_TEAL = "#4FB7B2"        # Active states, selected indicators, accents
SLATE_BLUE = "#334B6B"        # Secondary UI, subheads, chart support
COOL_GRAY = "#AAB6C2"         # Borders, helper text, disabled states
MIST_WHITE = "#F7FAFC"        # Background, card surfaces
INK = "#101828"               # Primary body text, dense labels

# ===== Functional status (warm = clinical concern only) =====
MUTED_AMBER = "#D89A2B"       # Moderate concern, stewardship watch
CLINICAL_CORAL = "#D9674E"    # High concern, worsening trend
SOFT_GREEN = "#4E9F7A"        # Stable, success, validated ingestion
SOFT_BLUE = "#5B7FA6"         # Neutral information, secondary context

# ===== Derived chart palettes =====
# Sequential teal scheme (for ordinal data, susceptibility heatmaps)
TEAL_SEQUENTIAL = [
    "#E5F4F2", "#BFE3DF", "#8FCFC8", "#6CC8C0",
    TRACE_TEAL, "#3B9690", "#2A716D", "#1B524F",
]

# Sequential navy scheme (for categorical / county-level)
NAVY_SEQUENTIAL = [
    "#E8ECF4", "#C0C7DA", "#8B96B5", "#5C6B92",
    SLATE_BLUE, "#1F2E45", PRIMARY_NAVY, "#030C1F",
]

# Categorical scheme for county / facility comparisons
CATEGORICAL = [PRIMARY_NAVY, TRACE_TEAL, SLATE_BLUE, MUTED_AMBER, SOFT_BLUE]

# Resistance / concern color scale (low → high concern)
CONCERN_SCALE = [SOFT_GREEN, MUTED_AMBER, CLINICAL_CORAL]

# ===== Typography stacks =====
# Avenir Next is an Apple system font; Aptos is a Microsoft font.
# Both fall back gracefully to Inter (open-source, Google Fonts) on systems
# that don't have them.
FONT_HEADING = "'Avenir Next', 'Aptos', 'Inter', system-ui, sans-serif"
FONT_UI = "'Aptos', 'Inter', system-ui, sans-serif"
FONT_TABLE = "'Inter', 'Aptos', system-ui, sans-serif"

# ===== Logo SVG =====
# Segmented ring: navy ring with a teal accent arc at the top-right,
# evoking surveillance / completed signal.
LOGO_SVG = """
<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"
     width="40" height="40" style="display: block;">
  <circle cx="20" cy="20" r="14" fill="none"
          stroke="{navy}" stroke-width="4"/>
  <path d="M 20 6 A 14 14 0 0 1 32.12 13" fill="none"
        stroke="{teal}" stroke-width="4" stroke-linecap="round"/>
</svg>
""".strip().format(navy=PRIMARY_NAVY, teal=TRACE_TEAL)

# Compact inline variant for the sticky header (24px)
LOGO_SVG_SMALL = """
<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"
     width="24" height="24" style="display: block;">
  <circle cx="20" cy="20" r="14" fill="none"
          stroke="{navy}" stroke-width="5"/>
  <path d="M 20 6 A 14 14 0 0 1 32.12 13" fill="none"
        stroke="{teal}" stroke-width="5" stroke-linecap="round"/>
</svg>
""".strip().format(navy=PRIMARY_NAVY, teal=TRACE_TEAL)
