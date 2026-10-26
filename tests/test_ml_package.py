"""
tests/test_ml_package.py

Unit tests for standalone `ml` package:
- intfloat/multilingual-e5-small embeddings (passage/query prefixes, 384-d, L2 unit norm)
- Augmented VADER sentiment model with Hinglish lexicon & rating prior
- Hinglish detection
- Language and Unicode script detection
- In-memory PII masking and restoration
- Ambiguity and sarcasm scoring
- Temperature calibration and ECE
"""
from __future__ import annotations

import pytest
import numpy as np

from ml.embeddings import EmbeddingProvider
from ml.sentiment import SentimentModel
from ml.hinglish_detector import HinglishDetector
from ml.language_detector import LanguageDetector
from ml.translator import mask_pii, restore_pii
from ml.ambiguity import AmbiguityScorer
from ml.calibrate import TemperatureScaler
from ml.eval import compute_classification_metrics, compute_expected_calibration_error


def test_embedding_provider_prefixes_and_norm():
    provider = EmbeddingProvider.get_instance()
    passages = ["The battery lasts barely 2 hours.", "Screen is bright and responsive."]
    embeddings = provider.encode_passages(passages)

    assert len(embeddings) == 2
    for vec in embeddings:
        assert len(vec) == 384
        # Verify L2 unit normalization
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-3

    queries = ["battery backup life", "display brightness"]
    q_embeddings = provider.encode_queries(queries)
    assert len(q_embeddings) == 2
    for vec in q_embeddings:
        assert len(vec) == 384
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-3


def test_sentiment_model_hinglish_augmentation():
    model = SentimentModel.get_instance()

    # Severe vernacular negative
    pol_neg, score_neg = model.score_sentence("Ekdum bakwas ghatiya quality hai", user_rating=1.0)
    assert pol_neg == "neg"
    assert score_neg < -0.3

    # Severe vernacular positive
    pol_pos, score_pos = model.score_sentence("Paisa wasool zabardast mast product", user_rating=5.0)
    assert pol_pos == "pos"
    assert score_pos > 0.3


def test_hinglish_detector():
    detector = HinglishDetector()

    # Typical Hinglish e-commerce feedback
    hinglish_text = "Yeh phone bohot garam hota hai aur battery bhi jaldi khatam ho rahi hai"
    assert detector.is_hinglish(hinglish_text) is True

    # Standard English feedback
    english_text = "The phone heats up quickly and battery drains fast"
    assert detector.is_hinglish(english_text) is False


def test_language_detector_unicode():
    detector = LanguageDetector()

    # Hindi in Devanagari
    lang, script, tier = detector.detect("यह फोन बहुत गर्म हो रहा है")
    assert lang == "hi"
    assert script == "Devanagari"
    assert tier == 1

    # Tamil script
    lang_ta, script_ta, tier_ta = detector.detect("இந்த தொலைபேசி மிகவும் நன்றாக உள்ளது")
    assert lang_ta == "ta"
    assert script_ta == "Tamil"
    assert tier_ta == 1

    # Standard English
    lang_en, script_en, tier_en = detector.detect("Great sound clarity and build quality")
    assert lang_en == "en"
    assert script_en == "Latin"
    assert tier_en == 1


def test_pii_masking_and_restoration():
    raw_text = "Contact me at rajesh.kumar@example.com or +91-9876543210 regarding order ORD-9928173."
    masked, mapping = mask_pii(raw_text)

    # Check that sensitive values are removed from masked string
    assert "rajesh.kumar@example.com" not in masked
    assert "9876543210" not in masked
    assert "ORD-9928173" not in masked
    assert "[EMAIL_0]" in masked
    assert "[PHONE_0]" in masked
    assert "[ORDER_0]" in masked

    # Check complete lossless restoration
    restored = restore_pii(masked, mapping)
    assert restored == raw_text


def test_ambiguity_and_sarcasm():
    scorer = AmbiguityScorer()

    # Sarcasm signal
    sarcastic_text = "Superb packaging, product was already dead on arrival! Great job /s"
    cat_sarcasm, mult_sarcasm = scorer.score(sarcastic_text, user_rating=1.0, sentiment_polarity=-0.5)
    assert cat_sarcasm == "sarcasm"
    assert mult_sarcasm == 0.55

    # Mixed adversative signal
    mixed_text = "Battery is great but the camera is completely terrible"
    cat_mixed, mult_mixed = scorer.score(mixed_text, user_rating=3.0, sentiment_polarity=0.0)
    assert cat_mixed == "mixed"
    assert mult_mixed == 0.70

    # Clear sentence
    clear_text = "Outstanding build quality and crystal clear sound"
    cat_none, mult_none = scorer.score(clear_text, user_rating=5.0, sentiment_polarity=0.8)
    assert cat_none == "none"
    assert mult_none == 1.00


def test_temperature_scaling_and_calibration():
    scaler = TemperatureScaler(initial_temperature=1.0)
    confidences = [0.95, 0.90, 0.85, 0.60, 0.40, 0.20]
    labels = [True, True, True, False, False, False]

    fitted_t = scaler.fit(confidences, labels)
    assert fitted_t > 0.0

    calibrated_val = scaler.calibrate(0.85)
    assert 0.0 <= calibrated_val <= 1.0

    ece = compute_expected_calibration_error(confidences, labels, n_bins=5)
    assert 0.0 <= ece <= 1.0
