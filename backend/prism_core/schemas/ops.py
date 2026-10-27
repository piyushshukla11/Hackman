"""
prism_core/schemas/ops.py

Pydantic v2 schemas for Operations, Output Cards, and Auth responses.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

from prism_core.schemas.diagnose import ConfidenceBreakdown


class ProbeResult(BaseModel):
    healthy: bool
    latency_ms: int
    message: str | None = None


class SourceHealthSchema(BaseModel):
    source_id: str
    checked_at: datetime
    status: str
    lag_seconds: int
    items_24h: int
    expected_24h: int
    error_rate: float
    schema_drift: dict[str, Any] = Field(default_factory=dict)


class MemberSnippet(BaseModel):
    review_id: str
    text_original: str | None = None
    text_en: str | None = None
    rating: float
    channel: str
    verified_purchase: bool
    batch_id: str | None = None
    reviewed_at: str
    role: str = "member"


class IssueCard(BaseModel):
    id: str
    product_id: str
    feature: str
    polarity: Literal["neg", "pos"] = "neg"
    issue_type: Literal["isolated", "batch", "systemic", "channel_specific", "praise"]
    severity: Literal["high", "medium", "low"]
    confidence: float
    confidence_breakdown: ConfidenceBreakdown | None = None
    defect_concentration: float = 0.0
    dominant_batch_id: str | None = None
    p_value: float = 1.0
    lead_time_days: int = 0
    size: int
    channels: dict[str, int] = Field(default_factory=dict)
    first_seen: date
    last_seen: date
    status: str
    sample_members: list[MemberSnippet] = Field(default_factory=list)


class Investigation(BaseModel):
    survey_id: str
    issue_id: str
    review_id: str
    status: str
    questions: list[dict[str, Any]]
    answers: dict[str, Any] | None = None
    summary: str | None = None
    confidence_delta: float = 0.0


class HealthIndex(BaseModel):
    product_id: str
    overall_health: float = Field(..., ge=0.0, le=100.0)
    rating_component: float
    sentiment_component: float
    open_issue_penalty: float
    open_issues_count: int


class TrendIndex(BaseModel):
    product_id: str
    granularity: str = "week"
    points: list[dict[str, Any]] = Field(default_factory=list)


class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    role_title: str | None = None
    selected_views: list[str] = Field(default_factory=list)
    has_completed_onboarding: bool = False
    tenant_id: str


class OnboardingPayload(BaseModel):
    role_title: str = Field(..., description="Custom title e.g. Senior QA Lead, VP CX, Head of Product")
    selected_views: list[str] = Field(..., description="Selected dashboard module IDs")


class PersonaPresetPayload(BaseModel):
    persona: Literal["qa", "cx", "pm", "exec"]
