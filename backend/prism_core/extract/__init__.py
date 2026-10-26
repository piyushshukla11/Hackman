"""
prism_core/extract/__init__.py

L3 Understand — Clause-Level Feature Extraction & Review Analysis.
- Splits text into clauses
- Zero-shot semantic feature mapping using multilingual-e5-small dense embeddings
- Polarity per feature with negation, litotes, and Bayesian rating prior
- Intra-review feature deduplication (collapses duplicate mentions per review)
- Other/unknown fallback for unmatched evaluative clauses
- Ambiguity and sarcasm detection
- Serious safety hazard assessment
"""
from __future__ import annotations

import re
from typing import Optional, Sequence
import numpy as np

from prism_core.ml.ambiguity import AmbiguityScorer
from prism_core.ml.embeddings import EmbeddingProvider
from prism_core.ml.language_detector import LanguageDetector
from prism_core.ml.sentiment import SentimentModel
from prism_core.schemas.raw_review import RawReview
from prism_core.schemas.understand import FeatureMention, ReviewAnalysis
from prism_core.serious import assess as assess_serious

DEFAULT_CATEGORY_FEATURES = [
    "build_quality", "cooling_performance", "battery_life", "sound_quality",
    "display", "software", "connectivity", "price_value", "customer_support",
    "packaging", "installation", "noise_level", "durability", "usability", "safety"
]


def cosine_sim(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:

    """Calculates cosine similarity between two dense embedding vectors."""
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def split_sentences(text: str) -> list[str]:
    """Split text on sentence terminators: periods, exclamation marks, question marks, newlines, and Indic danda (।)."""
    if not text:
        return []
    raw_sentences = re.split(r"[.!?\n\u0964]+", text)
    return [s.strip() for s in raw_sentences if s.strip()]


class FeatureExtractor:
    """Clause-level feature extractor with dense embeddings and deduplication."""


    def __init__(self):
        self.sentiment_model = SentimentModel.get_instance()
        self.ambiguity_scorer = AmbiguityScorer()
        self.embedder = EmbeddingProvider.get_instance()
        self.lang_detector = LanguageDetector()

    def analyse(
        self,
        raw: Any,
        product_id: Optional[str] = None,
        custom_features: Optional[Any] = None,
        user_rating: Optional[float] = None,
    ) -> ReviewAnalysis:
        if isinstance(raw, str):
            text = raw.strip()
            rating = user_rating
        elif hasattr(raw, "text_original") or hasattr(raw, "text_en"):
            text = (getattr(raw, "text_original", None) or getattr(raw, "text_en", None) or "").strip()
            rating = user_rating
        elif hasattr(raw, "text") or hasattr(raw, "title"):
            text = (getattr(raw, "text", None) or getattr(raw, "title", None) or "").strip()
            rating = user_rating if user_rating is not None else (raw.rating.value if getattr(raw, "rating", None) else None)
        else:
            text = str(raw).strip()
            rating = user_rating

        if not text:
            return ReviewAnalysis(features=[], embedding=[], serious=None)

        clauses = self.sentiment_model.split_clauses(text)
        if not clauses:
            clauses = [text]

        # Features candidate list (custom features max 15, fallback to standard anchors)
        cleaned_custom: list[str] = []
        if custom_features:
            for item in custom_features:
                if isinstance(item, dict):
                    cleaned_custom.append(item.get("name", ""))
                elif isinstance(item, str):
                    cleaned_custom.append(item)
        cleaned_custom = [c for c in cleaned_custom if c]
        features_pool = cleaned_custom[:15] if cleaned_custom else list(DEFAULT_CATEGORY_FEATURES)
        if "battery_life" in features_pool and "battery" not in features_pool:
            features_pool.append("battery")
        if "other" not in features_pool:
            features_pool.append("other")

        # Encode queries for feature anchors
        feature_embeddings = self.embedder.encode_queries(features_pool)
        feature_mat = np.asarray(feature_embeddings, dtype=np.float32)  # shape: (n_features, 384)

        # Encode passage clauses
        clause_embeddings = self.embedder.encode_passages(clauses)
        clause_mat = np.asarray(clause_embeddings, dtype=np.float32)  # shape: (n_clauses, 384)

        # Full review embedding (mean pooled)
        rev_emb = np.mean(clause_mat, axis=0)
        norm_rev = np.linalg.norm(rev_emb)
        if norm_rev > 0:
            rev_emb /= norm_rev
        review_vector = rev_emb.tolist()

        raw_feature_mentions: list[FeatureMention] = []
        clause_polarities: list[tuple[str, float]] = []

        for s_idx, clause in enumerate(clauses):
            c_vec = clause_mat[s_idx]
            pol_label, pol_score = self.sentiment_model.analyze_clause(clause, rating=rating)
            clause_polarities.append((pol_label, pol_score))

            # Check keyword match first (robust to offline mock vector mode)
            clause_lower = clause.lower()
            keyword_match = None
            for fp in features_pool:
                base_term = fp.replace("_", " ").split()[0]
                if re.search(r"\b" + re.escape(base_term) + r"\b", clause_lower):
                    keyword_match = fp
                    break

            # Compute cosine similarities to feature pool
            sims = np.dot(feature_mat, c_vec)
            best_feat_idx = int(np.argmax(sims))
            best_sim = float(sims[best_feat_idx])

            if keyword_match:
                matched_feature = keyword_match
                best_sim = max(best_sim, 0.85)
            elif best_sim >= 0.38:
                matched_feature = features_pool[best_feat_idx]
            elif pol_label != "neutral":
                matched_feature = "other/unknown"
                best_sim = 0.50
            else:
                continue

            raw_feature_mentions.append(
                FeatureMention(
                    feature=matched_feature,
                    polarity=pol_label,
                    score=pol_score,
                    sentence_idx=s_idx,
                    anchor_sim=round(best_sim, 4),
                )
            )

        # Language ambiguity check
        lang_res = self.lang_detector.detect(text)
        is_lang_uncertain = (lang_res.lang == "unclear") or lang_res.request_review

        # Ambiguity evaluation
        amb_result = self.ambiguity_scorer.evaluate(
            text=text,
            clause_polarities=clause_polarities,
            rating=rating,
            emojis=[],
            language_uncertainty=is_lang_uncertain,
        )


        # Intra-review feature deduplication
        consolidated: dict[str, FeatureMention] = {}
        for fm in raw_feature_mentions:
            fm.ambiguity = amb_result["ambiguity"]
            fm.ambiguity_mult = amb_result["ambiguity_mult"]
            feat = fm.feature
            if feat not in consolidated:
                consolidated[feat] = fm
            else:
                # Merge: keep strongest polarity and highest anchor similarity
                existing = consolidated[feat]
                if abs(fm.score) > abs(existing.score):
                    consolidated[feat] = fm

        final_features = list(consolidated.values())

        # Text-level sentiment and rating alignment
        text_sentiment = self.sentiment_model.analyze_text(text, rating=rating)

        # Serious safety hazard scan
        serious_assessment = assess_serious(raw, text)

        return ReviewAnalysis(
            features=final_features,
            embedding=review_vector,
            serious=serious_assessment,
            sentiment=text_sentiment["sentiment"],
            sentiment_score=text_sentiment["score"],
            rating_alignment=text_sentiment["rating_alignment"],
            ambiguity=amb_result["ambiguity"],
            ambiguity_mult=amb_result["ambiguity_mult"],
            request_review=amb_result["request_review"],
            sentiment_engine="vader_augmented",
        )


_feature_extractor = FeatureExtractor()


def analyse(
    raw: Any,
    product_id: Optional[str] = None,
    custom_features: Optional[Any] = None,
    user_rating: Optional[float] = None,
) -> ReviewAnalysis:
    """Public functional entrypoint for feature extraction."""
    return _feature_extractor.analyse(raw, product_id, custom_features, user_rating=user_rating)

