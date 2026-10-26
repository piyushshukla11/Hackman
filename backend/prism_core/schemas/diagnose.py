"""
prism_core/schemas/diagnose.py

Pydantic v2 schemas for L4 Diagnose: Cluster, Comparison, ConfidenceBreakdown, TrendPoint.
"""
from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class Cluster(BaseModel):
    id: str
    product_id: str
    feature: str
    polarity: Literal["neg", "pos"] = "neg"
    issue_type: Literal["isolated", "batch", "systemic", "channel_specific", "praise"]
    severity: Literal["high", "medium", "low"]
    first_seen: date
    last_seen: date
    size: int
    channels: dict[str, int] = Field(default_factory=dict)
    batches: dict[str, float] = Field(default_factory=dict)
    versions: list[str] = Field(default_factory=list)
    defect_concentration: float = Field(default=0.0, description="% share in dominant batch")
    dominant_batch_id: str | None = None
    p_value: float = Field(default=1.0, description="Statistical significance p < 0.001")
    lead_time_days: int = Field(default=0, description="Lead-time advantage in days")


class Comparison(BaseModel):
    lens: str
    a: str
    b: str
    metric: str
    delta: float
    ci_low: float
    ci_high: float
    p_value: float
    n_a: int
    n_b: int
    verdict: Literal["better", "worse", "no_change", "insufficient_data"]
    top_features: list[str] = Field(default_factory=list)


class ConfidenceBreakdown(BaseModel):
    frequency: float
    density: float
    consistency: float
    temporal: float
    evidence: float
    ambiguity_penalty: float
    coherence_bonus: float
    survey_delta: float
    final: float = Field(..., ge=0.0, le=1.0)
    level: Literal["act", "monitor", "gather"]  # >=0.75 / 0.45-0.74 / <0.45


class TrendPointSchema(BaseModel):
    product_id: str
    feature: str
    channel: str
    window: date
    n: int
    neg_rate: float
    neg_ci_low: float
    neg_ci_high: float
    rating_mean_trusted: float
    rating_mean_all: float
    pattern: str | None = None
