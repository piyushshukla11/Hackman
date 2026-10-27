"""
tests/test_ml_core_intelligence.py

Comprehensive test suite verifying all PRISM ML core intelligence modules in Hackman backend:
1. Language Normalization & Hinglish Detection
2. G1-G6 Trust Cascade with Decoupled Rating Status & Bounded Scores
3. Clause-Level Sentiment with Hinglish Lexicon, Negation Scope & Litotes
4. Sarcasm vs Sincere vs Rating Mismatch Disentanglement
5. Serious Safety Hazard Detection with Ordinary Defect Exclusion & Slang Immunity
6. 5-Rung Batch Inference Ladder (B0-B4)
7. Clause-Level Feature Extraction & Intra-Review Deduplication
8. Issue Graph Connected Components & Defect Concentration
9. 5-Lens Comparison Engine with Small Sample & Zero-Denominator Guards
10. 5-Factor Confidence Waterfall Breakdown
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from prism_core.batch import infer as infer_batch
from prism_core.compare import run as run_comparison
from prism_core.confidence import score as score_confidence
from prism_core.extract import analyse as extract_features
from prism_core.graph import rebuild as rebuild_graph
from prism_core.language import normalise as normalise_language
from prism_core.ml.ambiguity import AmbiguityScorer
from prism_core.ml.language_detector import LanguageDetector
from prism_core.ml.sentiment import SentimentModel
from prism_core.schemas.clean import NormalisedReview
from prism_core.schemas.diagnose import Cluster
from prism_core.schemas.raw_review import ProductRef, RatingPayload, RawReview
from prism_core.serious import assess as assess_serious
from prism_core.trust import score as score_trust


def test_language_normalization_and_hinglish():
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    raw = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-PHONE-01"),
        rating=RatingPayload(value=3.0),
        text="The sound is nice, lekin battery bilkul bekaar hai yaar 🙃",
        reviewed_at=now,
    )
    norm = asyncio.run(normalise_language(raw))
    assert norm.lang == "hi-Latn"
    assert "🙃" in norm.emojis
    assert len(norm.text_en) > 0


def test_trust_cascade_decoupled_status_and_verified_bonus():
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    # 1. Short clean review: text dropped from NLP (rejected_short), but rating preserved (counted)
    raw_short = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-01"),
        rating=RatingPayload(value=5.0),
        author={"verified_buyer": True},
        text="Good",
        reviewed_at=now,
    )
    norm_short = NormalisedReview(
        lang="en", script="Latin", text_original="Good", text_en="Good"
    )
    verdict_short = score_trust(raw_short, norm_short)
    assert verdict_short.text_status == "rejected_short"
    assert verdict_short.rating_status == "counted"

    # 2. Duplicate review: rejected and rating excluded
    import hashlib
    existing = {hashlib.sha256(b"this is duplicate").hexdigest()}
    raw_dup = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-01"),
        rating=RatingPayload(value=1.0),
        author={"verified_buyer": True},
        text="This is duplicate",
        reviewed_at=now,
    )
    norm_dup = NormalisedReview(
        lang="en", script="Latin", text_original="This is duplicate", text_en="This is duplicate"
    )
    verdict_dup = score_trust(raw_dup, norm_dup, existing_hashes=existing)
    assert verdict_dup.text_status == "rejected_dup"
    assert verdict_dup.rating_status == "excluded"
    assert verdict_dup.trust_score <= 0.25

    # 3. Promo spam link
    raw_spam = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-01"),
        rating=RatingPayload(value=5.0),
        text="Get 100% genuine cashback at https://bit.ly/deal call 9876543210",
        reviewed_at=now,
    )
    norm_spam = NormalisedReview(
        lang="en", script="Latin", text_original=raw_spam.text, text_en=raw_spam.text
    )
    verdict_spam = score_trust(raw_spam, norm_spam)
    assert verdict_spam.text_status == "rejected_spam"
    assert verdict_spam.rating_status == "excluded"


def test_mixed_sentiment_disentanglement():
    """Verifies that reviews with contrasting positive and negative aspects are tagged mixed."""
    sentiment = SentimentModel.get_instance()
    scorer = AmbiguityScorer()

    # Split clause test
    clauses = sentiment.split_clauses("The display is beautiful and sharp, but the battery life is terrible.")
    assert len(clauses) >= 2
    pol_display, score_disp = sentiment.analyze_clause(clauses[0])
    pol_battery, score_batt = sentiment.analyze_clause(clauses[1])
    assert pol_display == "pos"
    assert pol_battery == "neg"

    # Ambiguity scorer evaluates mixed polarity
    res = scorer.evaluate(
        text="The display is beautiful and sharp, but the battery life is terrible.",
        clause_polarities=[(pol_display, score_disp), (pol_battery, score_batt)],
        rating=3.0,
    )
    assert res["ambiguity"] == "mixed"
    assert res["ambiguity_mult"] == 0.70
    assert "MIXED_POLARITY" in res["signals"]


def test_vague_text_detection():
    """
    Verifies that factual neutral statements are classified as neutral with ambiguity='none',
    while 'vague' is reserved strictly for genuinely underspecified or vacuous reviews.
    """
    sentiment = SentimentModel.get_instance()
    scorer = AmbiguityScorer()

    # 1. Factual neutral statement: informative, non-evaluative -> ambiguity='none'
    factual_text = "The product arrived in a brown box on Wednesday."
    pol, score = sentiment.analyze_clause(factual_text)
    assert pol == "neutral"

    res_factual = scorer.evaluate(
        text=factual_text,
        clause_polarities=[(pol, score)],
        rating=3.0,
    )
    assert res_factual["ambiguity"] == "none"
    assert res_factual["ambiguity_mult"] == 1.00
    assert "VAGUE_TEXT" not in res_factual["signals"]

    # 2. Genuinely vague / underspecified text: vacuous remark -> ambiguity='vague'
    vague_text = "Average product, neither good nor bad."
    pol_v, score_v = sentiment.analyze_clause(vague_text)
    assert pol_v == "neutral"

    res_vague = scorer.evaluate(
        text=vague_text,
        clause_polarities=[(pol_v, score_v)],
        rating=3.0,
    )
    assert res_vague["ambiguity"] == "vague"
    assert res_vague["ambiguity_mult"] == 0.85
    assert "VAGUE_TEXT" in res_vague["signals"]




def test_rating_disagreement_and_mismatch():
    """Verifies mismatch between star rating and expressed sentiment is caught without changing text sentiment or calling it sarcasm."""
    scorer = AmbiguityScorer()
    sentiment = SentimentModel.get_instance()

    # 1. 5-star review with severe defect text
    text_defect = "The motor burned out immediately and plastic housing broke into pieces."
    res_high_star_defect = scorer.evaluate(
        text=text_defect,
        clause_polarities=[("neg", -0.85)],
        rating=5.0,
    )
    assert "RATING_TEXT_CONFLICT" in res_high_star_defect["signals"]
    assert res_high_star_defect["ambiguity"] == "rating_conflict"
    assert res_high_star_defect["ambiguity_mult"] == 0.75
    assert res_high_star_defect["request_review"] is True

    # Pure text sentiment remains negative, rating alignment reported as conflict
    text_res = sentiment.analyze_text(text_defect, rating=5.0)
    assert text_res["sentiment"] == "negative"
    assert text_res["rating_alignment"] == "conflict"

    # 2. 1-star review with pure praise text
    text_praise = "Excellent build quality, loved the sound, perfect device."
    res_low_star_praise = scorer.evaluate(
        text=text_praise,
        clause_polarities=[("pos", 0.90)],
        rating=1.0,
    )
    assert "RATING_TEXT_CONFLICT" in res_low_star_praise["signals"]
    assert res_low_star_praise["ambiguity"] == "rating_conflict"
    assert res_low_star_praise["ambiguity_mult"] == 0.75
    assert res_low_star_praise["request_review"] is True

    # Pure text sentiment remains positive, rating alignment reported as conflict
    praise_res = sentiment.analyze_text(text_praise, rating=1.0)
    assert praise_res["sentiment"] == "positive"
    assert praise_res["rating_alignment"] == "conflict"


def test_rhetorical_sarcasm_and_ironic_emojis():
    """Verifies sarcasm detection across rhetorical irony, sarcastic emojis, and rhetorical questions."""
    scorer = AmbiguityScorer()

    # 1. Rhetorical irony pattern: praise + failure
    res_irony = scorer.evaluate(
        text="Great job amazon, broke on the very first day!",
        clause_polarities=[("pos", 0.7), ("neg", -0.8)],
        rating=1.0,
    )
    assert "RHETORICAL_IRONY" in res_irony["signals"]
    assert res_irony["ambiguity"] == "sarcasm"
    assert res_irony["ambiguity_mult"] == 0.55

    # 2. Expensive paperweight pattern
    res_paperweight = scorer.evaluate(
        text="Makes an expensive paperweight after 2 weeks.",
        clause_polarities=[("neg", -0.6)],
        rating=1.0,
    )
    assert "RHETORICAL_IRONY" in res_paperweight["signals"]
    assert res_paperweight["ambiguity"] == "sarcasm"

    # 3. Sarcastic emoji with negative review
    res_emoji = scorer.evaluate(
        text="Love when my brand new oven stops heating on day two 🙃",
        clause_polarities=[("neg", -0.7)],
        rating=1.0,
        emojis=["🙃"],
    )
    assert "SARCASTIC_EMOJI" in res_emoji["signals"]
    assert res_emoji["ambiguity"] == "sarcasm"

    # 4. Rhetorical question
    res_question = scorer.evaluate(
        text="Who designed this disaster? Is this a joke?",
        clause_polarities=[("neg", -0.7)],
        rating=1.0,
    )
    assert "RHETORICAL_QUESTION" in res_question["signals"]


def test_multi_token_negation_and_litotes():
    """Verifies 3-token negation window, vernacular negation, and litotes."""
    sentiment = SentimentModel.get_instance()

    # 1. Multi-token window negation ("not at all good")
    pol1, score1 = sentiment.analyze_clause("The audio is not at all good")
    assert pol1 == "neg"
    assert score1 < 0.0

    # 2. Direct negation ("sound is not good")
    pol2, score2 = sentiment.analyze_clause("Sound is not good")
    assert pol2 == "neg"
    assert score2 < 0.0

    # 3. Vernacular Hindi negation ("achha nahi hai")
    pol3, score3 = sentiment.analyze_clause("Camera achha nahi hai")
    assert pol3 == "neg"
    assert score3 < 0.0

    # 4. Litotes (negated negative): "not bad at all" -> mild positive/neutral +0.10
    pol_litotes, score_litotes = sentiment.analyze_clause("The battery life is not bad at all")
    assert score_litotes >= 0.05
    assert pol_litotes in ("pos", "neutral")

    # 5. Vernacular litotes: "kharab nahi hai"
    pol_v_litotes, score_v_litotes = sentiment.analyze_clause("Display bilkul kharab nahi hai")
    assert score_v_litotes >= 0.05
    assert pol_v_litotes in ("pos", "neutral")


def test_multilingual_reviews_indic_and_vernacular():
    """Verifies language identification for Indic scripts and vernacular lexicon scoring."""
    detector = LanguageDetector()
    sentiment = SentimentModel.get_instance()

    # 1. Devanagari Hindi
    lang_hi, script_hi, tier_hi = detector.detect("यह फ्रिज बहुत जल्दी ठंडा करता है")
    assert script_hi == "Devanagari"
    assert lang_hi == "hi"
    assert tier_hi == 1

    # 2. Kannada
    lang_kn, script_kn, tier_kn = detector.detect("ಈ ಫ್ರಿಡ್ಜ್ ತುಂಬಾ ಚೆನ್ನಾಗಿದೆ")
    assert script_kn == "Kannada"
    assert lang_kn == "kn"
    assert tier_kn == 1

    # 3. Romanized Hinglish praise with vernacular e-commerce lexicon ("ekdum badiya", "mast")
    pol_praise, score_praise = sentiment.analyze_clause("Product ekdum badiya hai, cooling ekdum mast")
    assert pol_praise == "pos"
    assert score_praise > 0.4

    # 4. Romanized Hinglish complaint with vernacular lexicon ("paisa barbad", "bakwas")
    pol_comp, score_comp = sentiment.analyze_clause("Paisa barbad, bilkul bakwas product")
    assert pol_comp == "neg"
    assert score_comp < -0.4


def test_serious_safety_hazard_detection_and_defect_exclusion():
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Genuine Hazard: caught fire
    raw_fire = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-OVEN-01"),
        rating=RatingPayload(value=1.0),
        text="The heating element caught fire internally and started billowing smoke!",
        reviewed_at=now,
    )
    hazard = assess_serious(raw_fire)
    assert hazard is not None
    assert hazard.category == "fire_explosion"
    assert hazard.severity == "high"

    # 2. Ordinary Defect Exclusion: water leak from faucet / hose
    raw_leak = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-WASHER-01"),
        rating=RatingPayload(value=2.0),
        text="The hose had a small water leak and dripping under the sink.",
        reviewed_at=now,
    )
    assert assess_serious(raw_leak) is None

    # 3. Slang Praise Immunity: "This new color is fire 🔥"
    raw_slang = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-SHIRT-01"),
        rating=RatingPayload(value=5.0),
        text="This new color is fire! Had a blast wearing it.",
        reviewed_at=now,
    )
    assert assess_serious(raw_slang) is None

    # 4. Negated Hazard: "No electric shock occurred"
    raw_neg = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-TOASTER-01"),
        rating=RatingPayload(value=4.0),
        text="Worked safely, no electric shock or sparks.",
        reviewed_at=now,
    )
    assert assess_serious(raw_neg) is None


def test_batch_inference_ladder():
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)

    # Rung B0: Explicit code
    raw_b0 = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-FRIDGE-01"),
        rating=RatingPayload(value=2.0),
        text="My unit from batch B-0716 had a broken shelf.",
        reviewed_at=now,
    )
    inf_b0 = infer_batch(raw_b0)
    assert inf_b0.batch_method == "B0"
    assert inf_b0.batch_conf == 1.00
    assert inf_b0.batch_id == "B-0716"

    # Rung B3: Purchase cohort
    raw_b3 = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="amazon",
        product=ProductRef(sku="SKU-FRIDGE-01"),
        rating=RatingPayload(value=1.0),
        text="Stopped cooling after 2 weeks.",
        order={"purchase_date": date(2026, 7, 10)},
        reviewed_at=now,
    )
    inf_b3 = infer_batch(raw_b3)
    assert inf_b3.batch_method == "B3"
    assert inf_b3.batch_conf == 0.50
    assert "COHORT_AMAZON_2026_07_FN1" in (inf_b3.batch_id or "")


def test_feature_extraction_and_deduplication():
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    raw = RawReview(
        tenant_id="tenant_1",
        source_id="SITE_A",
        channel="web",
        product=ProductRef(sku="SKU-REF-01"),
        rating=RatingPayload(value=2.0),
        text="Cooling performance is poor. The cooling fails to keep milk cold. However the design is nice.",
        reviewed_at=now,
    )
    analysis = extract_features(raw, product_id="prod_ref_01", custom_features=["cooling_performance", "build_quality"])
    feats = [f.feature for f in analysis.features]
    # Check deduplication: cooling_performance appears only once
    assert feats.count("cooling_performance") == 1
    assert len(analysis.embedding) == 384


def test_issue_graph_rebuild_and_batch_classification():
    today = date(2026, 10, 27)
    # 6 negative mentions on cooling_performance concentrated in batch B-101 within 10 days
    mentions = [
        {"id": f"m_{i}", "feature": "cooling_performance", "polarity": "neg", "batch_id": "B-101",
         "channel": "amazon", "created_at": today - date.resolution * i, "trust_score": 0.9}
        for i in range(6)
    ]
    clusters = rebuild_graph("prod_1", mentions)
    assert len(clusters) == 1
    c = clusters[0]
    assert c.feature == "cooling_performance"
    assert c.issue_type == "batch"
    assert c.defect_concentration == 1.0
    assert c.p_value <= 0.05


def test_comparison_engine_small_sample_guard():
    # Small sample N = 5 vs 5 -> must safely return insufficient_data without crashing
    a_small = [4.0, 5.0, 4.0, 3.0, 5.0]
    b_small = [2.0, 1.0, 2.0, 3.0, 1.0]
    res_small = run_comparison("product", "prod_a", "prod_b", a_small, b_small)
    assert res_small.verdict == "insufficient_data"

    # Sufficient sample N = 25 vs 25 -> valid statistical test
    a_large = [4.5] * 25
    b_large = [2.0] * 25
    res_large = run_comparison("product", "prod_a", "prod_b", a_large, b_large)
    assert res_large.verdict == "better"
    assert res_large.p_value < 0.05


def test_confidence_waterfall_breakdown():
    c = Cluster(
        id="c1",
        product_id="p1",
        feature="battery_life",
        polarity="neg",
        issue_type="batch",
        severity="high",
        first_seen=date(2026, 10, 1),
        last_seen=date(2026, 10, 10),
        size=15,
        defect_concentration=0.85,
        p_value=0.001,
    )
    conf = score_confidence(c, user_trust_avg=0.90)
    assert 0.0 <= conf.final <= 1.0
    assert conf.level in ("act", "monitor", "gather")
    assert conf.frequency > 0
    assert conf.density > 0
    assert conf.consistency > 0
