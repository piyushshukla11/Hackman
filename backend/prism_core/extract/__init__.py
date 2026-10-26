"""
prism_core/extract/__init__.py

L3 Understand — Feature Extraction and Ambiguity Analysis.
Exposes:
def analyse(review: NormalisedReview, product_id: str | None = None, ...) -> ReviewAnalysis

Matches review text against:
1. Company Custom Features (max 15 defined per product)
2. Category taxonomy anchor features
Assigns polarity via augmented VADER and evaluates ambiguity/sarcasm.
"""
from __future__ import annotations

import re
from typing import Any, Sequence
import numpy as np

from prism_core.ml.ambiguity import AmbiguityScorer
from prism_core.ml.embeddings import EmbeddingProvider
from prism_core.ml.sentiment import SentimentModel
from prism_core.schemas.clean import NormalisedReview
from prism_core.schemas.understand import FeatureMention, ReviewAnalysis
from prism_core.serious import assess as assess_serious

DEFAULT_CATEGORY_FEATURES = [
    "battery",
    "sound_quality",
    "comfort",
    "connectivity",
    "build_quality",
    "price_value",
    "microphone",
    "durability",
    "packaging",
    "customer_support",
]

_ambiguity_scorer = AmbiguityScorer()


def split_sentences(text: str) -> list[str]:
    """Split text on sentence terminators: periods, exclamation marks, question marks, newlines, and Indic danda (।)."""
    if not text:
        return []
    raw_sentences = re.split(r"[.!?\n।]+", text)
    return [s.strip() for s in raw_sentences if s.strip()]


def cosine_sim(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def analyse(
    review: NormalisedReview,
    product_id: str | None = None,
    custom_features: list[dict[str, Any]] | None = None,
    user_rating: float = 3.0,
) -> ReviewAnalysis:
    """
    Public entrypoint for L3 Extract.
    Returns ReviewAnalysis with identified feature mentions, 384-d vector, and serious assessment.
    """
    embedder = EmbeddingProvider.get_instance()
    sentiment_model = SentimentModel.get_instance()

    text_to_analyse = review.text_en or review.text_original or ""
    sentences = split_sentences(text_to_analyse)
    if not sentences and text_to_analyse:
        sentences = [text_to_analyse]

    # Full review 384-d embedding
    review_vectors = embedder.encode_passages([text_to_analyse]) if text_to_analyse else []
    review_embedding = review_vectors[0] if review_vectors else []

    # Compile candidate features: category defaults + company custom features (max 15)
    candidates: list[str] = list(DEFAULT_CATEGORY_FEATURES)
    if custom_features:
        for cf in custom_features[:15]:
            fname = cf.get("name") if isinstance(cf, dict) else str(cf)
            if fname and fname not in candidates:
                candidates.append(fname)

    # Encode feature anchor queries
    anchor_embeddings = embedder.encode_queries(candidates)
    feature_to_anchor = {candidates[i]: anchor_embeddings[i] for i in range(len(candidates))}

    feature_mentions: list[FeatureMention] = []

    # Process each sentence
    for s_idx, sentence in enumerate(sentences):
        sentence_vec = embedder.encode_passages([sentence])[0]
        sentence_lower = sentence.lower()

        # Score similarities to all candidates
        scored_candidates: list[tuple[str, float]] = []
        for feat, anchor_vec in feature_to_anchor.items():
            sim = cosine_sim(sentence_vec, anchor_vec)
            # Direct keyword boost if feature or keyword appears in sentence
            if feat.lower() in sentence_lower:
                sim = max(sim, 0.75)
            scored_candidates.append((feat, sim))

        # Sort candidates by similarity descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        if not scored_candidates:
            continue

        top_feat, top_sim = scored_candidates[0]
        floor_sim = 0.38
        relative_margin = 0.04

        # Select matches within relative margin of top score (max 4 per sentence)
        matched_sentence_features: list[tuple[str, float]] = []
        for feat, sim in scored_candidates:
            if sim >= floor_sim and (top_sim - sim) <= relative_margin:
                matched_sentence_features.append((feat, sim))
            if len(matched_sentence_features) >= 4:
                break

        # Polarity and ambiguity for the sentence
        polarity, score_val = sentiment_model.score_sentence(sentence, user_rating=user_rating)
        ambiguity_type, ambiguity_mult = _ambiguity_scorer.score(
            sentence,
            user_rating=user_rating,
            sentiment_polarity=score_val,
            emojis=review.emojis,
        )

        for feat, sim in matched_sentence_features:
            feature_mentions.append(FeatureMention(
                feature=feat,
                polarity=polarity,
                score=score_val,
                ambiguity=ambiguity_type,
                ambiguity_mult=ambiguity_mult,
                sentence_idx=s_idx,
                anchor_sim=round(sim, 3),
                llm_used=False,
                needs_second_opinion=ambiguity_type in ("sarcasm", "mixed"),
            ))

    # Evaluate safety / serious complaints
    serious_assessment = assess_serious(review)

    return ReviewAnalysis(
        features=feature_mentions,
        embedding=review_embedding,
        serious=serious_assessment,
        sentiment_engine="vader_augmented",
    )
