"""
prism_core/schemas/understand.py

Pydantic v2 schemas for L3 Understand: FeatureMention, SeriousAssessment, BatchInference, ReviewAnalysis.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class FeatureMention(BaseModel):
    feature: str
    polarity: Literal["pos", "neg", "neutral"]
    score: float
    ambiguity: Literal["none", "vague", "mixed", "rating_conflict", "sarcasm", "uncertain"] = "none"
    ambiguity_mult: float = 1.00  # 1.00 / 0.85 / 0.75 / 0.70 / 0.65 / 0.55
    sentence_idx: int = 0
    anchor_sim: float = 0.0
    llm_used: bool = False
    needs_second_opinion: bool = False


class TextSentimentResult(BaseModel):
    sentiment: Literal["positive", "negative", "mixed", "neutral", "unclear"]
    score: float
    rating_alignment: Literal["aligned", "conflict", "unknown"] = "unknown"
    clauses: list[dict[str, Any]] = Field(default_factory=list)


class SeriousAssessment(BaseModel):
    category: Any
    severity: Literal["high", "medium", "low"]
    urgency: Literal["high", "medium", "low"]
    status: Literal["open", "escalated", "resolved"] = "open"
    alerted_at: datetime | None = None


class BatchInference(BaseModel):
    batch_id: str | None = None
    batch_method: Literal["B0", "B1", "B2", "B3", "B4"] = "B4"
    batch_conf: float = 0.30  # 1.00 / 0.85 / 0.70 / 0.50 / 0.30
    version_id: str | None = None
    pooled: bool = False


class ReviewAnalysis(BaseModel):
    features: list[FeatureMention] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list, description="384-d multilingual-e5-small")
    serious: SeriousAssessment | None = None
    sentiment: Literal["positive", "negative", "mixed", "neutral", "unclear"] = "neutral"
    sentiment_score: float = 0.0
    rating_alignment: Literal["aligned", "conflict", "unknown"] = "unknown"
    ambiguity: Literal["none", "vague", "mixed", "rating_conflict", "sarcasm", "uncertain"] = "none"
    ambiguity_mult: float = 1.00
    request_review: bool = False
    language: str = "en"
    analysis_method: Literal["native_multilingual", "translation_fallback"] = "native_multilingual"
    sentiment_engine: Literal["vader_augmented", "transformer_head", "llm_second_pass"] = "vader_augmented"
