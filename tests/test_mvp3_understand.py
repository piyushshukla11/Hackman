"""
tests/test_mvp3_understand.py

Unit tests for MVP 3:
- Augmented VADER Sentiment analysis with Hinglish & Indian e-commerce lexicon
- Ambiguity & Sarcasm scoring
- Feature extraction with Company Custom Features (zero-shot e5-small matching)
- Serious complaint / Safety risk classification
- Batch inference ladder B0-B4
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from prism_core.batch import infer as infer_batch
from prism_core.extract import analyse as extract_analyse
from prism_core.ml.ambiguity import AmbiguityScorer
from prism_core.ml.llm_client import LLMClient
from prism_core.ml.sentiment import SentimentModel
from prism_core.schemas.clean import NormalisedReview
from prism_core.schemas.raw_review import OrderPayload, ProductRef, RatingPayload, RawReview
from prism_core.serious import assess as assess_serious


def test_sentiment_model_hinglish_augmentation():
    model = SentimentModel.get_instance()

    # Highly negative Hinglish word "bakwas" / "bekar"
    pol_neg, score_neg = model.score_sentence("ye product bilkul bakwas hai", user_rating=1.0)
    assert pol_neg == "neg"
    assert score_neg < -0.10

    # Highly positive Hinglish word "zabardast" / "badiya"
    pol_pos, score_pos = model.score_sentence("badiya product hai, zabardast sound", user_rating=5.0)
    assert pol_pos == "pos"
    assert score_pos > 0.10


def test_ambiguity_and_sarcasm_scorer():
    scorer = AmbiguityScorer()

    # Sarcasm via star rating divergence (5 stars with scathing negative sentiment)
    amb_type, mult = scorer.score("The product arrived dead on arrival, completely useless", user_rating=5.0, sentiment_polarity=-0.6)
    assert amb_type == "sarcasm"
    assert mult == 0.55

    # Hedge words -> vague
    amb_vague, mult_vague = scorer.score("It is maybe sort of okay, not sure", user_rating=3.0, sentiment_polarity=0.0)
    assert amb_vague == "vague"
    assert mult_vague == 0.85

    # Clean text -> none
    amb_clean, mult_clean = scorer.score("The battery lasts 20 hours easily", user_rating=5.0, sentiment_polarity=0.5)
    assert amb_clean == "none"
    assert mult_clean == 1.00


def test_serious_safety_assessment():
    # Electrical / thermal safety risk
    rev_hazard = NormalisedReview(
        lang="en", script="Latin",
        text_original="While charging, the battery caught fire and smoke filled the room!",
        text_en="While charging, the battery caught fire and smoke filled the room!"
    )
    assessment = assess_serious(rev_hazard)
    assert assessment is not None
    assert assessment.category == "safety_thermal_electrical"
    assert assessment.severity == "high"
    assert assessment.urgency == "high"

    # Benign review -> None
    rev_normal = NormalisedReview(
        lang="en", script="Latin",
        text_original="Comfortable fit and decent volume.",
        text_en="Comfortable fit and decent volume."
    )
    assert assess_serious(rev_normal) is None


def test_batch_inference_ladder():
    now = datetime.now(timezone.utc)

    # B0: Explicit batch code
    raw_b0 = RawReview(
        tenant_id="t1", source_id="s1", channel="web",
        product=ProductRef(sku="HEADPHONE-01"), rating=RatingPayload(value=4.0),
        reviewed_at=now, batch_code="BATCH-2024-W12-001"
    )
    b0 = infer_batch(NormalisedReview(lang="en", script="Latin", text_original="OK", text_en="OK"), raw_b0)
    assert b0.batch_method == "B0"
    assert b0.batch_conf == 1.00
    assert b0.batch_id == "BATCH-2024-W12-001"

    # B2: Warehouse + Dispatch date
    raw_b2 = RawReview(
        tenant_id="t1", source_id="s1", channel="web",
        product=ProductRef(sku="HEADPHONE-01"), rating=RatingPayload(value=4.0),
        reviewed_at=now,
        order=OrderPayload(warehouse="BLR-WH-02", dispatch_date=date(2024, 3, 15))
    )
    b2 = infer_batch(NormalisedReview(lang="en", script="Latin", text_original="OK", text_en="OK"), raw_b2)
    assert b2.batch_method == "B2"
    assert b2.batch_conf == 0.70
    assert "BLR-WH-02" in b2.batch_id

    # B3: Purchase date cohort
    raw_b3 = RawReview(
        tenant_id="t1", source_id="s1", channel="web",
        product=ProductRef(sku="HEADPHONE-01"), rating=RatingPayload(value=4.0),
        reviewed_at=now,
        order=OrderPayload(purchase_date=date(2024, 4, 10))
    )
    b3 = infer_batch(NormalisedReview(lang="en", script="Latin", text_original="OK", text_en="OK"), raw_b3)
    assert b3.batch_method == "B3"
    assert b3.batch_conf == 0.50


def test_feature_extraction_with_custom_features():
    rev = NormalisedReview(
        lang="en", script="Latin",
        text_original="The ear cushion comfort is luxurious, but the battery died after 2 hours.",
        text_en="The ear cushion comfort is luxurious, but the battery died after 2 hours."
    )
    # Define company custom feature "ear cushion comfort"
    custom_feats = [{"name": "ear cushion comfort", "description": "Ergonomics of ear cups"}]

    analysis = extract_analyse(rev, custom_features=custom_feats, user_rating=2.5)

    assert len(analysis.features) >= 1
    features_detected = [f.feature for f in analysis.features]
    assert "battery" in features_detected or "ear cushion comfort" in features_detected
    assert len(analysis.embedding) == 384
