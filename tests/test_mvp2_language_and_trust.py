"""
tests/test_mvp2_language_and_trust.py

Unit tests for MVP 2:
- Language & Script Detection (Devanagari, Tamil, Latin)
- Hinglish (Romanized Hindi) detection
- In-memory PII masking and restoration
- Trust Cascade Gates G1-G6 and verdict logic
- EmbeddingProvider vector properties (384-d, unit L2 norm)
"""
from __future__ import annotations

import pytest
import numpy as np

from prism_core.language import extract_emojis
from prism_core.ml.embeddings import EmbeddingProvider
from prism_core.ml.hinglish_detector import HinglishDetector
from prism_core.ml.language_detector import LanguageDetector
from prism_core.ml.translator import mask_pii, restore_pii
from prism_core.schemas.clean import NormalisedReview
from prism_core.schemas.raw_review import AuthorPayload, ProductRef, RatingPayload, RawReview
from prism_core.trust import score as score_trust


def test_language_and_script_detection():
    detector = LanguageDetector()

    # Devanagari Hindi
    lang, script, tier = detector.detect("यह हेडफोन बहुत अच्छा है")
    assert script == "Devanagari"
    assert lang == "hi"
    assert tier == 1

    # Tamil
    lang, script, tier = detector.detect("இந்த தயாரிப்பு மிகவும் பயனுள்ளதாக உள்ளது")
    assert script == "Tamil"
    assert lang == "ta"
    assert tier == 1

    # Standard English
    lang, script, tier = detector.detect("The battery life is outstanding and sound is crisp.")
    assert script == "Latin"
    assert lang == "en"
    assert tier == 1


def test_hinglish_detector():
    detector = HinglishDetector()

    # Clear Hinglish
    hinglish_text = "ye product bilkul bekar hai, mera paisa barbaad ho gaya mat khareedo"
    assert detector.is_hinglish(hinglish_text) is True

    # Standard English
    english_text = "The ear cushions are comfortable for long flights."
    assert detector.is_hinglish(english_text) is False


def test_pii_masking_in_memory():
    raw_text = "Call me at +91 9876543210 or email test.user@example.com regarding order ORD-99887766."
    masked, mapping = mask_pii(raw_text)

    assert "+91 9876543210" not in masked
    assert "test.user@example.com" not in masked
    assert "ORD-99887766" not in masked
    assert "[PHONE_0]" in masked or "[EMAIL_0]" in masked

    restored = restore_pii(masked, mapping)
    assert restored == raw_text


def test_trust_cascade_gates():
    # 1. G1: Short text (< 2 words) -> rejected_short, rating counted
    norm_short = NormalisedReview(
        lang="en", script="Latin", text_original="Good", text_en="Good"
    )
    res_short = score_trust(norm_short)
    assert res_short.text_status == "rejected_short"
    assert res_short.rating_status == "counted"

    # 2. G2: Exact dupe -> rejected_dup, excluded
    norm_clean = NormalisedReview(
        lang="en", script="Latin", text_original="Battery drains very quickly in cold weather.", text_en="Battery drains very quickly in cold weather."
    )
    res_dupe = score_trust(norm_clean, is_exact_dupe=True)
    assert res_dupe.verdict == "rejected"
    assert res_dupe.text_status == "rejected_dup"
    assert res_dupe.rating_status == "excluded"

    # 3. G3: Near dupe (>= 0.95 similarity) -> rejected_dup, excluded
    res_near = score_trust(norm_clean, near_dupe_max_sim=0.96)
    assert res_near.verdict == "rejected"
    assert res_near.text_status == "rejected_dup"
    assert res_near.rating_status == "excluded"

    # 4. G4: Promo link spam -> rejected_spam, excluded
    norm_promo = NormalisedReview(
        lang="en", script="Latin", text_original="Visit http://freescam.com and use code DISCOUNT50 for free gifts", text_en="Visit http://freescam.com"
    )
    res_promo = score_trust(norm_promo)
    assert res_promo.verdict == "rejected"
    assert res_promo.text_status == "rejected_spam"
    assert res_promo.rating_status == "excluded"

    # 5. Clean review with verified purchase provenance bonus (+0.15)
    from datetime import datetime, timezone
    raw_verified = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-001"),
        rating=RatingPayload(value=4.0),
        reviewed_at=datetime.now(timezone.utc),
        author=AuthorPayload(verified_buyer=True),
    )
    res_clean = score_trust(norm_clean, raw=raw_verified)
    assert res_clean.verdict == "clean"
    assert res_clean.text_status == "accepted"
    assert res_clean.rating_status == "counted"
    assert res_clean.trust_score >= 0.70


def test_embedding_provider_properties():
    provider = EmbeddingProvider.get_instance()
    vectors = provider.encode_passages(["Great noise cancellation", "The hinge snapped after two weeks"])

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384

    # Verify unit L2 norm: ||v|| ~ 1.0
    norm0 = np.linalg.norm(vectors[0])
    norm1 = np.linalg.norm(vectors[1])
    assert pytest.approx(norm0, abs=1e-3) == 1.0
    assert pytest.approx(norm1, abs=1e-3) == 1.0
