"""
prism_core/serious/__init__.py

L3 Serious — Serious Complaint & Safety Assessment.
Identifies safety hazards, legal threats, and severe consumer injuries.

Exposes:
def assess(review: NormalisedReview, analysis: ReviewAnalysis) -> SeriousAssessment | None
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from prism_core.schemas.clean import NormalisedReview
from prism_core.schemas.understand import ReviewAnalysis, SeriousAssessment

SAFETY_KEYWORDS = {
    # Thermal & Electrical
    "fire", "smoke", "spark", "blast", "exploded", "explosion", "burnt", "burning", "shock", "electric shock",
    "melted", "overheating", "caught fire", "flame", "flames", "smell of burning",
    # Physical Injury
    "injury", "injured", "bleed", "bleeding", "cut", "hospital", "doctor", "er", "burns", "stitches",
    # Chemical / Health
    "poison", "toxic", "rash", "allergic", "allergy", "infection",
    # Legal / Regulatory
    "lawyer", "lawsuit", "court", "police", "fir", "consumer forum", "sue", "legal notice",
}

SAFETY_REGEX = re.compile(r"\b(" + "|".join(SAFETY_KEYWORDS) + r")\b", re.IGNORECASE)


def assess(review: NormalisedReview, analysis: ReviewAnalysis | None = None) -> SeriousAssessment | None:
    """
    Scans review for critical safety, medical, or legal risks.
    Returns SeriousAssessment if triggered, else None.
    """
    text = (review.text_original + " " + review.text_en).lower()
    matches = SAFETY_REGEX.findall(text)
    if not matches:
        return None

    matched_keywords = set(m.lower() for m in matches)

    # Classify category
    if any(k in matched_keywords for k in ("fire", "smoke", "blast", "exploded", "shock", "burnt", "melted")):
        category = "safety_thermal_electrical"
        severity: Literal["high", "medium", "low"] = "high"
        urgency: Literal["high", "medium", "low"] = "high"
    elif any(k in matched_keywords for k in ("hospital", "doctor", "bleed", "burns", "injury")):
        category = "physical_injury"
        severity = "high"
        urgency = "high"
    elif any(k in matched_keywords for k in ("lawyer", "lawsuit", "consumer forum", "court", "police")):
        category = "legal_regulatory"
        severity = "medium"
        urgency = "medium"
    else:
        category = "hazard"
        severity = "medium"
        urgency = "low"

    return SeriousAssessment(
        category=category,
        severity=severity,
        urgency=urgency,
        status="open",
        alerted_at=datetime.now(timezone.utc),
    )
