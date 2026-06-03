"""Hand-curated guideline-aligned content for the TRACE POC.

This module is the placeholder for the future RAG layer. The interface
(`get_scenarios()`, `lookup_scenario()`) is designed so that when we build the
real retrieval-augmented system in Phase 2, the UI calls don't need to change
— the static lookup is just swapped for a retrieval call.

Content is faithful to published IDSA / ATS / SHEA / IDSA-PIDS guidance. It is
**curated by hand for the POC**, not generated. Citations point to the
authoritative source guideline so a clinician reviewer can verify any claim.

Each scenario captures:
  - scenario_key: (infection_site, care_setting, suspected_organism)
  - first_line: list of regimens (drug or drug combination)
  - alternatives: alternative regimens (allergy, resistance, special populations)
  - duration: typical course length
  - contraindications: things to watch for
  - stewardship_notes: de-escalation, IV-to-PO, duration optimization
  - evidence_grade: IDSA-style strength + quality
  - source: guideline name, year, recommendation reference

Demo scope: 8 scenarios spanning the most common stewardship-relevant
infections. Phase 2 expands this to cover full guideline corpora.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class GuidelineScenario:
    scenario_key: tuple[str, str, str]  # (infection_site, care_setting, organism)
    display_name: str
    first_line: list[str]
    alternatives: list[str]
    duration: str
    contraindications: list[str]
    stewardship_notes: list[str]
    evidence_grade: str
    source: str
    source_url: Optional[str] = None


# ----- Scenario library -----

_SCENARIOS: dict[tuple[str, str, str], GuidelineScenario] = {}


def _register(scenario: GuidelineScenario) -> None:
    _SCENARIOS[scenario.scenario_key] = scenario


# Uncomplicated UTI — outpatient — E. coli (most common stewardship scenario)
_register(GuidelineScenario(
    scenario_key=("UTI", "Outpatient", "Escherichia coli"),
    display_name="Uncomplicated cystitis (outpatient, E. coli)",
    first_line=[
        "Nitrofurantoin 100 mg PO BID × 5 days",
        "Trimethoprim-sulfamethoxazole 160/800 mg PO BID × 3 days "
        "(if local E. coli resistance to TMP-SMX < 20%)",
        "Fosfomycin 3 g PO × 1 dose",
    ],
    alternatives=[
        "Cephalexin 500 mg PO QID × 5–7 days (β-lactam, lower efficacy)",
        "Amoxicillin-clavulanate 500/125 mg PO BID × 5–7 days",
    ],
    duration="3–7 days depending on agent",
    contraindications=[
        "Nitrofurantoin: avoid if CrCl < 30 mL/min or in pyelonephritis",
        "TMP-SMX: avoid in third trimester pregnancy",
        "Fluoroquinolones: not first-line — reserved for complicated UTI / "
        "pyelonephritis per FDA safety guidance",
    ],
    stewardship_notes=[
        "Fluoroquinolones should NOT be used for uncomplicated cystitis when "
        "alternatives exist (collateral damage, C. difficile, tendon risk).",
        "Choice should be informed by local susceptibility — use the TRACE "
        "Susceptibility Snapshot to verify TMP-SMX < 20% resistance locally.",
    ],
    evidence_grade="Strong recommendation, high-quality evidence",
    source="IDSA Uncomplicated Cystitis & Pyelonephritis Guideline (2010, "
           "updated 2024 review)",
    source_url="https://www.idsociety.org/practice-guideline/uncomplicated-utis/",
))

# Complicated UTI / pyelonephritis — inpatient
_register(GuidelineScenario(
    scenario_key=("UTI", "Inpatient", "Escherichia coli"),
    display_name="Pyelonephritis / complicated UTI (inpatient)",
    first_line=[
        "Ceftriaxone 1 g IV daily",
        "Piperacillin-tazobactam 3.375 g IV q6h (if risk factors for resistant "
        "organisms)",
    ],
    alternatives=[
        "Ertapenem 1 g IV daily (if ESBL-producing organism suspected or "
        "confirmed)",
        "Ciprofloxacin 400 mg IV q12h (if susceptible and FQ acceptable)",
    ],
    duration="7–14 days total (IV until clinically improved, then transition "
             "to oral once susceptibilities known)",
    contraindications=[
        "Avoid empiric carbapenem unless ESBL risk factors present "
        "(prior ESBL isolate, recent broad-spectrum antibiotics, healthcare "
        "exposure)",
    ],
    stewardship_notes=[
        "De-escalate to narrowest effective oral agent within 48–72h once "
        "culture and susceptibilities return.",
        "Switch IV → PO when clinically stable, tolerating oral, and a "
        "susceptible oral agent is available.",
    ],
    evidence_grade="Strong recommendation, moderate-to-high evidence",
    source="IDSA Complicated UTI Guideline (2010, periodic update)",
    source_url="https://www.idsociety.org/practice-guideline/uncomplicated-utis/",
))

# Community-acquired pneumonia — outpatient
_register(GuidelineScenario(
    scenario_key=("Pneumonia", "Outpatient", "Streptococcus pneumoniae"),
    display_name="Community-acquired pneumonia (outpatient)",
    first_line=[
        "Amoxicillin 1 g PO TID (healthy adults, no comorbidities)",
        "Amoxicillin-clavulanate 875/125 mg PO BID + macrolide "
        "(if comorbidities)",
    ],
    alternatives=[
        "Doxycycline 100 mg PO BID (macrolide alternative)",
        "Levofloxacin 750 mg PO daily (β-lactam allergy; not preferred due to "
        "collateral damage)",
    ],
    duration="5 days minimum; extend only if clinically not improved by day 3",
    contraindications=[
        "Macrolide monotherapy not recommended where local S. pneumoniae "
        "macrolide resistance > 25%",
        "Fluoroquinolones: reserve for severe allergy or contraindication to "
        "first-line",
    ],
    stewardship_notes=[
        "Five days is sufficient for most uncomplicated CAP — longer courses "
        "do not improve outcomes and increase adverse events.",
        "Reassess at 48–72h. If clinically stable and afebrile, complete "
        "course at home.",
    ],
    evidence_grade="Strong recommendation, moderate evidence",
    source="IDSA/ATS Community-Acquired Pneumonia Guideline (2019)",
    source_url="https://www.thoracic.org/statements/copd-pneumonia.php",
))

# CAP — inpatient
_register(GuidelineScenario(
    scenario_key=("Pneumonia", "Inpatient", "Streptococcus pneumoniae"),
    display_name="Community-acquired pneumonia (inpatient, non-ICU)",
    first_line=[
        "Ceftriaxone 1–2 g IV daily + azithromycin 500 mg IV/PO daily",
        "Ampicillin-sulbactam 3 g IV q6h + macrolide (alternative β-lactam)",
    ],
    alternatives=[
        "Levofloxacin 750 mg IV/PO daily (β-lactam allergy or contraindication)",
        "Add MRSA coverage (vancomycin) only if MRSA risk factors or prior "
        "MRSA isolation",
        "Add Pseudomonas coverage (pip-tazo or cefepime) only if Pseudomonas "
        "risk factors present",
    ],
    duration="5 days, extended to 7 days only if slow response or complicated",
    contraindications=[
        "Avoid empiric MRSA / Pseudomonas coverage unless specific risk "
        "factors present — broad-spectrum overuse drives resistance",
    ],
    stewardship_notes=[
        "De-escalate β-lactam to narrower agent or oral therapy at 48–72h if "
        "stable, afebrile, and tolerating PO.",
        "Stop empiric MRSA / Pseudomonas coverage at 48h if no growth or no "
        "epidemiologic risk confirmed.",
    ],
    evidence_grade="Strong recommendation, moderate-to-high evidence",
    source="IDSA/ATS Community-Acquired Pneumonia Guideline (2019)",
    source_url="https://www.thoracic.org/statements/copd-pneumonia.php",
))

# Hospital-acquired / ICU pneumonia — Pseudomonas / MRSA risk
_register(GuidelineScenario(
    scenario_key=("Pneumonia", "ICU", "Pseudomonas aeruginosa"),
    display_name="Hospital-acquired pneumonia (ICU, Pseudomonas risk)",
    first_line=[
        "Piperacillin-tazobactam 4.5 g IV q6h (extended infusion) + "
        "vancomycin 15–20 mg/kg IV q8–12h",
        "Cefepime 2 g IV q8h + vancomycin (alternative anti-pseudomonal "
        "β-lactam)",
    ],
    alternatives=[
        "Meropenem 1 g IV q8h + vancomycin (if ESBL risk or β-lactam allergy)",
        "Linezolid 600 mg IV/PO q12h (vancomycin alternative for MRSA "
        "coverage)",
    ],
    duration="7 days (shortened from historical 14–21 day courses; not "
             "inferior in trials)",
    contraindications=[
        "Avoid aminoglycoside monotherapy",
        "Use linezolid cautiously with serotonergic agents (serotonin syndrome "
        "risk)",
    ],
    stewardship_notes=[
        "De-escalate based on culture and susceptibilities by day 3.",
        "Discontinue MRSA coverage if no MRSA isolated and nasal MRSA PCR "
        "negative.",
        "Seven-day course non-inferior to longer courses for most HAP/VAP — "
        "use 7 days unless complicated.",
    ],
    evidence_grade="Strong recommendation, high evidence",
    source="IDSA/ATS Management of Adults with HAP and VAP Guideline (2016)",
    source_url="https://www.idsociety.org/practice-guideline/hap_vap/",
))

# MRSA bacteremia
_register(GuidelineScenario(
    scenario_key=("Bloodstream", "Inpatient", "Staphylococcus aureus"),
    display_name="S. aureus bacteremia (empiric, awaiting MRSA status)",
    first_line=[
        "Vancomycin 15–20 mg/kg IV q8–12h (target AUC 400–600 mg·h/L)",
        "Add cefazolin 2 g IV q8h if MSSA confirmed (de-escalate from vanc)",
    ],
    alternatives=[
        "Daptomycin 6–10 mg/kg IV daily (MRSA, persistent bacteremia, or "
        "vancomycin failure)",
        "Ceftaroline 600 mg IV q8–12h (vancomycin alternative for MRSA)",
    ],
    duration="Minimum 14 days IV from first negative blood culture for "
             "uncomplicated bacteremia; longer for endocarditis or metastatic "
             "infection",
    contraindications=[
        "Do not use vancomycin oral for bacteremia (no systemic absorption)",
        "Daptomycin is inactivated by pulmonary surfactant — do not use for "
        "pneumonia",
    ],
    stewardship_notes=[
        "Infectious Disease consultation for ALL cases of S. aureus "
        "bacteremia improves outcomes (IDSA-supported quality measure).",
        "De-escalate to cefazolin within 24h of MSSA confirmation — cefazolin "
        "is superior to vancomycin for MSSA.",
        "Source control (line removal, drainage) is essential.",
    ],
    evidence_grade="Strong recommendation, high evidence",
    source="IDSA MRSA Treatment Guideline (2011, periodic update)",
    source_url="https://www.idsociety.org/practice-guideline/mrsa/",
))

# Group A Strep pharyngitis
_register(GuidelineScenario(
    scenario_key=("Pharyngitis", "Outpatient", "Group A Strep"),
    display_name="Group A streptococcal pharyngitis",
    first_line=[
        "Penicillin V 500 mg PO BID-TID × 10 days",
        "Amoxicillin 50 mg/kg PO daily (or 1 g daily for adults) × 10 days",
    ],
    alternatives=[
        "Cephalexin 500 mg PO BID × 10 days (non-anaphylactic penicillin "
        "allergy)",
        "Azithromycin 500 mg PO × 1, then 250 mg daily × 4 days "
        "(true β-lactam allergy)",
    ],
    duration="10 days for penicillin / amoxicillin; 5 days for azithromycin",
    contraindications=[
        "Macrolide resistance in GAS is rising — use only for true β-lactam "
        "allergy",
        "Do not treat asymptomatic GAS carriers",
    ],
    stewardship_notes=[
        "Use rapid antigen test or culture to confirm GAS before treating — "
        "viral pharyngitis is more common and does not require antibiotics.",
        "Penicillin V remains first-line — GAS has not developed penicillin "
        "resistance.",
    ],
    evidence_grade="Strong recommendation, high evidence",
    source="IDSA Group A Streptococcal Pharyngitis Guideline (2012)",
    source_url="https://www.idsociety.org/practice-guideline/group-a-strep-pharyngitis/",
))

# C. difficile
_register(GuidelineScenario(
    scenario_key=("GI", "Inpatient", "C. difficile"),
    display_name="Clostridioides difficile infection (initial episode)",
    first_line=[
        "Fidaxomicin 200 mg PO BID × 10 days (preferred — lower recurrence)",
        "Vancomycin 125 mg PO QID × 10 days (alternative if fidaxomicin "
        "unavailable)",
    ],
    alternatives=[
        "Metronidazole 500 mg PO TID × 10 days — NO LONGER first-line "
        "(reserved for non-severe and only when fidaxomicin or oral "
        "vancomycin are unavailable)",
    ],
    duration="10 days for initial episode; extend or change agent for "
             "recurrent disease",
    contraindications=[
        "Avoid concurrent unnecessary antibiotics (perpetuates dysbiosis)",
        "Do not use IV vancomycin for CDI (no colonic exposure)",
    ],
    stewardship_notes=[
        "Discontinue precipitating antibiotics if clinically possible.",
        "Avoid PPIs and opioids during treatment when feasible.",
        "Refer for fecal microbiota transplant for second recurrence.",
    ],
    evidence_grade="Strong recommendation, moderate-to-high evidence",
    source="IDSA/SHEA Clostridioides difficile Infection Guideline "
           "(2017, 2021 focused update)",
    source_url="https://www.idsociety.org/practice-guideline/clostridioides-difficile-2021-focused-update/",
))


# ----- Public API -----

def get_all_scenarios() -> list[GuidelineScenario]:
    """Return every scenario in the library."""
    return list(_SCENARIOS.values())


def list_scenario_keys() -> list[tuple[str, str, str]]:
    """Return the (infection_site, care_setting, organism) keys available."""
    return list(_SCENARIOS.keys())


def lookup_scenario(
    infection_site: str,
    care_setting: str,
    organism: str,
) -> Optional[GuidelineScenario]:
    """Retrieve a single scenario by its key. Returns None if not found.

    This is the interface a future RAG layer will replace — same signature,
    different implementation underneath.
    """
    return _SCENARIOS.get((infection_site, care_setting, organism))


def infection_sites() -> list[str]:
    return sorted({k[0] for k in _SCENARIOS})


def care_settings_for_site(infection_site: str) -> list[str]:
    return sorted({k[1] for k in _SCENARIOS if k[0] == infection_site})


def organisms_for(infection_site: str, care_setting: str) -> list[str]:
    return sorted({
        k[2] for k in _SCENARIOS
        if k[0] == infection_site and k[1] == care_setting
    })
