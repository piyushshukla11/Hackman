"""
prism_core/schemas/raw_review.py

Pydantic v2 schemas for the RawReview envelope and nested structures.
Includes Multimodal Item (audio STT transcript, 3-keyframe capture, and label OCR text).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


class ProductRef(BaseModel):
    sku: str | None = None
    external_id: str | None = None
    name: str | None = None
    category: str | None = None

    @model_validator(mode="after")
    def check_identifier(self) -> ProductRef:
        if not self.sku and not self.external_id:
            raise ValueError("ProductRef must contain either 'sku' or 'external_id'")
        return self


class RatingPayload(BaseModel):
    value: float = Field(..., ge=0.5, le=5.0, description="Normalized rating in {0.5, 1.0, ..., 5.0}")
    scale: str = "5_star"
    raw_value: Any = None
    derived: bool = False


class AuthorPayload(BaseModel):
    id_hash: str | None = None
    display_name: str | None = None
    verified_buyer: bool = False
    review_count: int | None = None


class OrderPayload(BaseModel):
    order_id: str | None = None
    purchase_date: date | None = None
    dispatch_date: date | None = None
    warehouse: str | None = None
    seller: str | None = None


class MediaItem(BaseModel):
    media_id: str
    kind: Literal["image", "video"]
    url: str
    transcript: str | None = Field(default=None, description="Spoken complaints extracted via ffmpeg + STT")
    keyframes: list[str] = Field(default_factory=list, description="Candidate keyframe URLs (max 3)")
    ocr_text: str | None = Field(default=None, description="Extracted barcode/serial label text")


class ContactPayload(BaseModel):
    email: str | None = None
    phone: str | None = None
    consent_followup: bool = False


class ProvenancePayload(BaseModel):
    ip_hash: str | None = None
    user_agent: str | None = None
    captured_by: str | None = None
    adapter_id: str | None = None


class RawReview(BaseModel):
    tenant_id: str
    source_id: str
    channel: str
    kind: Literal["review", "rating_only"] = "review"
    source_review_id: str | None = None
    product: ProductRef
    rating: RatingPayload
    text: str | None = None
    title: str | None = None
    reviewed_at: datetime
    author: AuthorPayload = Field(default_factory=AuthorPayload)
    order: OrderPayload | None = None
    batch_code: str | None = None
    media: list[MediaItem] = Field(default_factory=list)
    contact: ContactPayload | None = None
    provenance: ProvenancePayload = Field(default_factory=ProvenancePayload)
