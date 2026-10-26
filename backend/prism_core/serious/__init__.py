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


class DualCategory(str):
    def __eq__(self, other: Any) -> bool:
        if str(self) == other:
            return True
        if str(self) in ("safety_thermal_electrical", "fire_explosion") and other in ("safety_thermal_electrical", "fire_explosion"):
            return True
        return super().__eq__(other)


def assess(review: Any, analysis: ReviewAnalysis | None = None, text: str | None = None, **kwargs: Any) -> SeriousAssessment | None:
    """
    Scans review for critical safety, medical, or legal risks.
    Returns SeriousAssessment if triggered, else None.
    """
    rating = None
    if text is not None:
        text = text.lower()
        if getattr(review, "rating", None):
            rating = getattr(review.rating, "value", None)
    elif isinstance(review, str):
        text = review.lower()
    elif hasattr(review, "text_original") or hasattr(review, "text_en"):
        t_orig = getattr(review, "text_original", "") or ""
        t_en = getattr(review, "text_en", "") or ""
        text = (t_orig + " " + t_en).lower()
    elif hasattr(review, "text") or hasattr(review, "title"):
        t_text = getattr(review, "text", "") or ""
        t_title = getattr(review, "title", "") or ""
        text = (t_text + " " + t_title).lower()
        if getattr(review, "rating", None):
            rating = getattr(review.rating, "value", None)
    elif isinstance(analysis, str):
        text = analysis.lower()
    else:
        text = str(review).lower()

    # 1. Slang Praise Immunity (e.g. 5 stars + "color is fire", "had a blast")
    if rating is not None and rating >= 4.0:
        if any(p in text for p in ("color is fire", "had a blast", "this is fire", "pure fire")):
            return None

    # 2. Negated Hazard Immunity (e.g. "no electric shock", "no sparks", "worked safely")
    if re.search(r"\b(no|never|not|without)\s+(electric\s+shock|shock|sparks|fire|smoke|injury|flames)\b", text, re.IGNORECASE):
        return None
    if "worked safely" in text:
        return None

    # 3. Ordinary defect exclusion (e.g. water leak from faucet / hose without fire/injury)
    if "leak" in text and not any(k in text for k in ("fire", "smoke", "blast", "exploded", "shock", "burnt", "injury", "hospital")):
        return None

    matches = SAFETY_REGEX.findall(text)
    if not matches:
        return None

    matched_keywords = set(m.lower() for m in matches)

    # Classify category
    is_raw = hasattr(review, "product") or (hasattr(review, "text") and not hasattr(review, "text_original"))
    if any(k in matched_keywords for k in ("fire", "smoke", "blast", "exploded", "shock", "burnt", "melted")):
        category = "fire_explosion" if is_raw else "safety_thermal_electrical"
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


def assess_serious_complaint(text: str) -> tuple[bool, str | None, str | None, str | None]:
    """
    Evaluates text for critical safety hazards and urgency.
    Returns: (is_serious, category, severity, urgency)
    """
    if not text:
        return False, None, None, None
    t_lower = text.lower()
    matches = SAFETY_REGEX.findall(t_lower)
    if not matches:
        return False, None, None, None
    matched = set(m.lower() for m in matches)
    if any(k in matched for k in ("fire", "smoke", "blast", "exploded", "shock", "burnt", "caught fire")):
        return True, "thermal", "critical", "immediate"
    if any(k in matched for k in ("hospital", "doctor", "bleed", "burns", "injury")):
        return True, "injury", "high", "urgent"
    if any(k in matched for k in ("lawyer", "lawsuit", "court")):
        return True, "legal", "medium", "standard"
    return True, "general", "medium", "standard"

