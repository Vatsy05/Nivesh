"""
Static Indian market event annotations for chart overlays.
No database dependency — data is hardcoded and versioned here.
"""
from typing import List, Dict, Any

# Event types: crash | recovery | policy | political | other
MARKET_EVENTS: List[Dict[str, Any]] = [
    # ── COVID Era ──────────────────────────────────────────────────────────────
    {
        "date": "2020-03-23",
        "label": "COVID Crash (Nifty -38%)",
        "short_label": "COVID Low",
        "type": "crash",
        "description": "Nifty 50 hit its COVID-era bottom at 7,511 on 23 March 2020.",
    },
    {
        "date": "2020-11-09",
        "label": "Vaccine Rally",
        "short_label": "Vaccine",
        "type": "recovery",
        "description": "Pfizer COVID-19 vaccine efficacy announced; global markets surged.",
    },
    # ── RBI Policy Cycle ────────────────────────────────────────────────────────
    {
        "date": "2022-05-04",
        "label": "RBI Emergency Rate Hike",
        "short_label": "RBI Hike",
        "type": "policy",
        "description": "RBI hiked repo rate by 40 bps in an unscheduled meeting — start of tightening cycle.",
    },
    {
        "date": "2022-06-08",
        "label": "RBI +50 bps Hike",
        "short_label": "+50 bps",
        "type": "policy",
        "description": "RBI raised repo rate by 50 bps to 4.90%.",
    },
    {
        "date": "2023-04-06",
        "label": "RBI Rate Pause",
        "short_label": "RBI Pause",
        "type": "policy",
        "description": "RBI paused rate hikes, signalling end of tightening cycle.",
    },
    {
        "date": "2025-02-07",
        "label": "RBI Rate Cut",
        "short_label": "Rate Cut",
        "type": "policy",
        "description": "RBI cut repo rate by 25 bps to 6.25% — first cut in 5 years.",
    },
    # ── Political / Macro ────────────────────────────────────────────────────────
    {
        "date": "2024-06-04",
        "label": "Election Results 2024",
        "short_label": "Elections",
        "type": "political",
        "description": "India general election results — NDA returned to power with reduced majority.",
    },
    {
        "date": "2023-01-25",
        "label": "Adani-Hindenburg Report",
        "short_label": "Hindenburg",
        "type": "crash",
        "description": "Hindenburg Research published short-seller report on Adani Group.",
    },
    # ── Global Macro ─────────────────────────────────────────────────────────────
    {
        "date": "2022-02-24",
        "label": "Russia-Ukraine War",
        "short_label": "Russia-Ukraine",
        "type": "crash",
        "description": "Russia invaded Ukraine — global commodities and markets shocked.",
    },
    {
        "date": "2023-03-10",
        "label": "SVB Bank Collapse",
        "short_label": "SVB",
        "type": "crash",
        "description": "Silicon Valley Bank collapsed — global banking sector panic.",
    },
]


def get_events_in_range(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Return market events between start_date and end_date (inclusive, YYYY-MM-DD strings)."""
    return [
        e for e in MARKET_EVENTS
        if start_date <= e["date"] <= end_date
    ]
