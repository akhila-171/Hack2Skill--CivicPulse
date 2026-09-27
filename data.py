"""
data.py
Synthetic data generation for the CivicPulse prototype.

In a real deployment, WARDS would come from census / municipal GIS data,
and COMPLAINTS would come from WhatsApp / IVR / web-form ingestion
pipelines. Here we simulate both so the prioritization + dashboard logic
can be demoed end-to-end without live integrations.
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

# ---------------------------------------------------------------------------
# 1. Ward master data (population + existing infrastructure index)
# ---------------------------------------------------------------------------
# infra_index: 0-100, higher = better existing infrastructure (roads, water,
# electricity, health facilities per capita). Lower infra_index = bigger gap.
WARDS = [
    {"ward": "Ward 1 - Old Town",        "lat": 17.4399, "lon": 78.4983, "population": 68000, "infra_index": 32, "budget_allocated_lakh": 12},
    {"ward": "Ward 2 - Riverside",       "lat": 17.4483, "lon": 78.5081, "population": 41000, "infra_index": 55, "budget_allocated_lakh": 20},
    {"ward": "Ward 3 - Industrial Belt", "lat": 17.4210, "lon": 78.4750, "population": 92000, "infra_index": 28, "budget_allocated_lakh": 15},
    {"ward": "Ward 4 - Green Hills",     "lat": 17.4650, "lon": 78.5200, "population": 25000, "infra_index": 78, "budget_allocated_lakh": 8},
    {"ward": "Ward 5 - New Colony",      "lat": 17.4050, "lon": 78.5300, "population": 54000, "infra_index": 46, "budget_allocated_lakh": 18},
    {"ward": "Ward 6 - Lakeview",        "lat": 17.4800, "lon": 78.4600, "population": 37000, "infra_index": 61, "budget_allocated_lakh": 10},
    {"ward": "Ward 7 - Market Area",     "lat": 17.4300, "lon": 78.5150, "population": 73000, "infra_index": 35, "budget_allocated_lakh": 14},
    {"ward": "Ward 8 - Hillside Slums",  "lat": 17.3950, "lon": 78.4900, "population": 61000, "infra_index": 18, "budget_allocated_lakh": 6},
    {"ward": "Ward 9 - Tech Corridor",   "lat": 17.4550, "lon": 78.3800, "population": 33000, "infra_index": 82, "budget_allocated_lakh": 25},
    {"ward": "Ward 10 - Outer Ring",     "lat": 17.3800, "lon": 78.5450, "population": 45000, "infra_index": 24, "budget_allocated_lakh": 9},
]

CATEGORIES = [
    "Water Supply", "Road Condition", "Electricity", "Sanitation/Waste",
    "Public Health", "Street Lighting", "Drainage", "Public Transport",
]

LANGUAGES = ["Hindi", "Telugu", "English", "Urdu", "Tamil", "Bengali"]
CHANNELS = ["WhatsApp", "Voice Call (IVR)", "Web Form", "SMS"]
STATUSES = ["Received", "Under Review", "Prioritized", "Funded", "Resolved"]

# A tiny illustrative phrase bank per category/language, standing in for a
# real ASR + translation + NLU pipeline (Whisper + multilingual LLM).
SAMPLE_PHRASES = {
    "Water Supply":     {"Hindi": "Hamare mohalle mein 3 din se paani nahi aa raha",
                          "Telugu": "Maa colony lo neellu randi 3 rojula nunchi",
                          "English": "No water supply in our area for 3 days"},
    "Road Condition":   {"Hindi": "Sadak mein bahut bade gaddhe hain",
                          "Telugu": "Road midha peddha gunthalu unnayi",
                          "English": "The road has large potholes causing accidents"},
    "Electricity":      {"Hindi": "Roz 4-5 ghante bijli chali jaati hai",
                          "Telugu": "Prathi roju 4-5 gantalu current potundi",
                          "English": "Power cuts for 4-5 hours daily"},
    "Sanitation/Waste": {"Hindi": "Kachra kai dino se uthaya nahi gaya",
                          "Telugu": "Chettu chala rojula nunchi theeyaledu",
                          "English": "Garbage hasn't been collected for days"},
}
DEFAULT_PHRASE = {"Hindi": "Is samasya ko jaldi thik karein",
                   "Telugu": "Dayachesi samasya parishkarinchandi",
                   "English": "Please resolve this issue urgently"}


def _sample_text(category: str, language: str) -> tuple[str, str]:
    """Return (original_text, translated_text) simulating ASR+translation."""
    bank = SAMPLE_PHRASES.get(category, DEFAULT_PHRASE)
    if language in bank:
        original = bank[language]
    elif language in DEFAULT_PHRASE:
        original = DEFAULT_PHRASE[language]
    else:
        original = DEFAULT_PHRASE["English"]
    translated = bank.get("English", DEFAULT_PHRASE["English"])
    if language == "English":
        translated = original
    return original, translated


def generate_wards_df() -> pd.DataFrame:
    return pd.DataFrame(WARDS)


def generate_complaints_df(n: int = 400) -> pd.DataFrame:
    """Simulate n citizen complaints arriving over the last 90 days,
    weighted so low-infra / high-population wards get more complaints
    (mirrors real-world reporting patterns)."""
    wards_df = generate_wards_df()
    weights = (wards_df["population"] / wards_df["population"].sum()) * \
              (100 - wards_df["infra_index"]) / 100
    weights = weights / weights.sum()

    rows = []
    now = datetime.now()
    for i in range(n):
        ward_row = wards_df.sample(weights=weights).iloc[0]
        category = random.choice(CATEGORIES)
        language = random.choices(
            LANGUAGES, weights=[30, 25, 20, 10, 8, 7], k=1
        )[0]
        channel = random.choices(CHANNELS, weights=[45, 25, 20, 10], k=1)[0]
        original_text, translated_text = _sample_text(category, language)
        urgency = int(np.clip(np.random.normal(6, 2), 1, 10))
        days_ago = random.randint(0, 90)
        status = random.choices(
            STATUSES, weights=[35, 25, 15, 15, 10], k=1
        )[0]

        rows.append({
            "complaint_id": f"CMP-{i+1:04d}",
            "ward": ward_row["ward"],
            "category": category,
            "language": language,
            "channel": channel,
            "original_text": original_text,
            "translated_text": translated_text,
            "urgency": urgency,
            "status": status,
            "submitted_at": now - timedelta(days=days_ago,
                                             hours=random.randint(0, 23)),
        })

    return pd.DataFrame(rows)
