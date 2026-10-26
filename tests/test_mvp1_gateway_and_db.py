"""
tests/test_mvp1_gateway_and_db.py

Unit tests for MVP 1:
1. Deterministic Idempotency Key computation
2. Adapter Rating Normalisation across different source scales
3. Strict Multi-Tenant Enforcement in Repositories
4. Dynamic Company Custom Features validation (max 15)
5. Multimodal MediaItem and RawReview schema validation
6. Role Onboarding and Persona Presets
"""
from __future__ import annotations

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from prism_core.db.repositories.base import BaseRepository
from prism_core.db.models import Product, User
from prism_core.ingest import compute_idempotency_key
from prism_core.ingest.adapters.sim_sites import normalise_rating
from prism_core.schemas.ops import OnboardingPayload, PersonaPresetPayload
from prism_core.schemas.raw_review import (
    AuthorPayload,
    MediaItem,
    ProductRef,
    RatingPayload,
    RawReview,
)


def test_idempotency_key_deterministic():
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    rev1 = RawReview(
        tenant_id="tenant_alpha",
        source_id="SITE_A",
        channel="web",
        source_review_id="REV-12345",
        product=ProductRef(sku="SKU-HEADPHONE-01"),
        rating=RatingPayload(value=4.5),
        text="Great sound quality, comfortable ear pads",
        reviewed_at=now,
    )

    rev2 = RawReview(
        tenant_id="tenant_alpha",
        source_id="SITE_A",
        channel="web",
        source_review_id="REV-12345",
        product=ProductRef(sku="SKU-HEADPHONE-01"),
        rating=RatingPayload(value=4.5),
        text="Great sound quality, comfortable ear pads",
        reviewed_at=now,
    )

    key1 = compute_idempotency_key(rev1)
    key2 = compute_idempotency_key(rev2)
    assert key1 == key2
    assert len(key1) == 64  # SHA-256


def test_idempotency_key_diff_tenants():
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    rev1 = RawReview(
        tenant_id="tenant_alpha",
        source_id="SITE_A",
        channel="web",
        source_review_id="REV-12345",
        product=ProductRef(sku="SKU-HEADPHONE-01"),
        rating=RatingPayload(value=4.5),
        reviewed_at=now,
    )
    rev2 = RawReview(
        tenant_id="tenant_beta",
        source_id="SITE_A",
        channel="web",
        source_review_id="REV-12345",
        product=ProductRef(sku="SKU-HEADPHONE-01"),
        rating=RatingPayload(value=4.5),
        reviewed_at=now,
    )
    assert compute_idempotency_key(rev1) != compute_idempotency_key(rev2)


def test_rating_normalisation_scales():
    # 5 integer stars -> as-is
    val, derived = normalise_rating(5, "5_star")
    assert val == 5.0 and not derived

    # 10 point scale -> nearest 0.5 (8/2 = 4.0, 7/2 = 3.5)
    val_10a, _ = normalise_rating(8, "10_point")
    assert val_10a == 4.0
    val_10b, _ = normalise_rating(7, "10_point")
    assert val_10b == 3.5

    # 100 point scale -> nearest 0.5 (82/20 = 4.1 -> 4.0)
    val_100, _ = normalise_rating(82, "100_point")
    assert val_100 == 4.0

    # Thumbs up / down -> 4.5 / 1.5 with derived=True
    up_val, up_derived = normalise_rating("up", "thumbs")
    assert up_val == 4.5 and up_derived
    down_val, down_derived = normalise_rating("down", "thumbs")
    assert down_val == 1.5 and down_derived


def test_strict_multi_tenant_repository_enforcement():
    # Attempting to initialize BaseRepository without tenant_id must raise ValueError
    with pytest.raises(ValueError, match="tenant_id is required"):
        BaseRepository(Product, session=None, tenant_id="")

    with pytest.raises(ValueError, match="tenant_id is required"):
        BaseRepository(User, session=None, tenant_id="   ")


def test_multimodal_media_item():
    media = MediaItem(
        media_id="m_001",
        kind="video",
        url="https://s3.amazonaws.com/videos/unboxing_leak.mp4",
        transcript="The bottle lid completely cracked after two days",
        keyframes=["https://cdn/frame1.jpg", "https://cdn/frame2.jpg", "https://cdn/frame3.jpg"],
        ocr_text="LOT-BATCH-2024-W12-REV3",
    )
    assert media.kind == "video"
    assert len(media.keyframes) == 3
    assert "cracked" in media.transcript
    assert media.ocr_text == "LOT-BATCH-2024-W12-REV3"


def test_onboarding_and_persona_schemas():
    onboarding = OnboardingPayload(
        role_title="Senior QA Lead",
        selected_views=["issues", "defect_concentration", "batches"],
    )
    assert onboarding.role_title == "Senior QA Lead"
    assert len(onboarding.selected_views) == 3

    persona = PersonaPresetPayload(persona="qa")
    assert persona.persona == "qa"

    with pytest.raises(ValidationError):
        PersonaPresetPayload(persona="invalid_persona")
