"""
prism_core/schemas/clean.py

Pydantic v2 schemas for L2 Clean: NormalisedReview and TrustVerdict.
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class NormalisedReview(BaseModel):
    lang: str = Field(..., description="BCP 47 with script tag e.g. hi-Latn")
    script: str = Field(..., description="Latin | Devanagari | etc.")
    text_original: str
    text_en: str
    emojis: list[str] = Field(default_factory=list)
    lang_tier: Literal[1, 2, 3] = 1
    lang_tier_penalty: bool = False


class GateResult(BaseModel):
    gate: Literal["G1", "G2", "G3", "G4", "G5", "G6"]
    verdict: Literal["pass", "warn", "fail"]
    reason_code: str
    score_delta: float
    detail: dict[str, Any] = Field(default_factory=dict)


class TrustVerdict(BaseModel):
    trust_score: float = Field(..., ge=0.0, le=1.0)
    verdict: Literal["clean", "suspicious", "rejected"]
    text_status: Literal["accepted", "rejected_short", "rejected_spam", "rejected_dup", "none"]
    rating_status: Literal["counted", "downweighted", "excluded"]
    gates: list[GateResult] = Field(default_factory=list)
