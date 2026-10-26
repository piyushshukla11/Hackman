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

THERMAL_KEYWORDS = {
    "fire", "caught fire", "smoke", "smoking", "spark", "sparks", "blast", "blasting",
    "exploded", "explosion", "burnt", "burning", "shock", "electric shock",
    "melted", "melting", "overheating", "overheated", "flame", "flames", "smell of burning",
}

INJURY_KEYWORDS = {
    "injury", "injured", "injuries", "bleed", "bleeding", "cut", "cuts",
    "hospital", "doctor", "er", "burns", "burned", "stitches",
}

LEGAL_KEYWORDS = {
    "lawyer", "lawsuit", "court", "police", "fir", "consumer forum", "sue", "legal notice",
}

CHEMICAL_KEYWORDS = {
    "poison", "toxic", "rash", "allergic", "allergy", "infection",
}

ALL_SAFETY_KEYWORDS = sorted(
    THERMAL_KEYWORDS | INJURY_KEYWORDS | LEGAL_KEYWORDS | CHEMICAL_KEYWORDS,
    key=len,
    reverse=True,
)

SAFETY_REGEX = re.compile(r"\b(" + "|".join(re.escape(k) for k in ALL_SAFETY_KEYWORDS) + r")\b", re.IGNORECASE)


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
    if matched_keywords & THERMAL_KEYWORDS or any(k in text for k in ("fire", "smoke", "blast", "shock")):
        category = "safety_thermal_electrical"
        severity: Literal["high", "medium", "low"] = "high"
        urgency: Literal["high", "medium", "low"] = "high"
    elif matched_keywords & INJURY_KEYWORDS:
        category = "physical_injury"
        severity = "high"
        urgency = "high"
    elif matched_keywords & LEGAL_KEYWORDS:
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


def assess_serious_complaint(text: str) -> tuple[bool, str, str, str]:
    """
    Convenience wrapper for demo / test usage.
    Returns (is_serious: bool, category: str, severity: str, urgency: str).
    Category is simplified: 'thermal' | 'injury' | 'legal' | 'hazard' | ''
    """
    from prism_core.schemas.clean import NormalisedReview
    review = NormalisedReview(lang="en", script="Latin", text_original=text, text_en=text)
    result = assess(review)
    if result is None:
        return False, "", "", ""

    # Map full category to simplified label for demo/external consumers
    _category_map = {
        "safety_thermal_electrical": "thermal",
        "physical_injury": "injury",
        "legal_regulatory": "legal",
        "hazard": "hazard",
    }
    simplified = _category_map.get(result.category, result.category)
    _sev_map = {"high": "critical", "medium": "medium", "low": "low"}
    _urg_map = {"high": "immediate", "medium": "high", "low": "low"}
    return True, simplified, _sev_map.get(result.severity, result.severity), _urg_map.get(result.urgency, result.urgency)

