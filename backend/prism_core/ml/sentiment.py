"""
prism_core/ml/sentiment.py

High-performance Clause-Level Multilingual Sentiment Engine.
- Derives sentiment strictly from text without allowing star ratings to contaminate or override text polarity.
- Reports rating/text alignment separately as 'aligned', 'conflict', or 'unknown'.
- Classifies review text into: 'positive', 'negative', 'mixed', 'neutral', or 'unclear'.
- Supports 16 languages (11 Indian + 5 International).
- Handles multi-token negation scope (preceding for SVO languages, succeeding for SOV Indic/Japanese).
- Handles litotes ('not bad', 'kharab nahi', 'nicht schlecht') -> mild positive/neutral (+0.10).
- Clause-level splitting via punctuation and multilingual contrastive conjunctions.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple
import yaml

from prism_core.config.settings import get_settings

NEGATION_TOKENS = {
    # English
    "not", "never", "no", "hardly", "barely", "scarcely", "without",
    # Hindi / Hinglish / Urdu
    "nahi", "nahin", "nhi", "mat", "na", "nako",
    # Marathi
    "नाही", "नको", "नाहीत",
    # Hindi Devanagari
    "नहीं", "नही",
    # Bengali / Assamese
    "না", "নয়", "নেই", "নহে", "নহয়", "নাই",
    # Gujarati
    "નથી", "ના", "નહિ",
    # Punjabi
    "ਨਹੀਂ", "ਨਾ",
    # Odia
    "ନାହିଁ", "ନୁହେଁ",
    # Tamil
    "இல்லை", "வேண்டாம்", "அல்ல",
    # Telugu
    "లేదు", "కాదు",
    # Kannada
    "ಇಲ್ಲ", "ಅಲ್ಲ", "ಬೇಡ", "illa", "ille",
    # Malayalam
    "ഇല്ല", "അല്ല", "അരുത്",
    # French
    "pas", "ne", "jamais", "aucun", "aucune", "rien",
    # German
    "nicht", "kein", "keine", "keinen", "nie", "niemals",
    # Spanish
    "no", "nunca", "jamás", "nada", "tampoco",
    # Japanese
    "ない", "なかった", "ません", "じゃない",
}

CONTRAST_CONJUNCTIONS = {
    # English
    "but", "however", "although", "though", "yet", "except",
    # Hindi / Urdu / Hinglish
    "lekin", "magar", "parantu", "kintu", "लेकिन", "मगर", "परंतु", "किंतु",
    # Marathi
    "पण", "मात्र",
    # Bengali / Assamese
    "কিন্তু", "তবে", "অথচ", "তথাপি",
    # Gujarati
    "પરંતુ", "પણ", "છતાં",
    # Punjabi
    "ਪਰ",
    # Odia
    "କିନ୍ତୁ", "ତଥାପି",
    # Tamil
    "ஆனால்", "எனினும்",
    # Telugu
    "కానీ", "అయితే",
    # Kannada
    "ಆದರೆ", "ಆದರೂ", "aadre", "aadare",
    # Malayalam
    "പക്ഷെ", "എങ്കിലും",
    # French
    "mais", "cependant", "pourtant", "néanmoins",
    # German
    "aber", "jedoch", "allerdings", "doch",
    # Spanish
    "pero", "sin embargo", "aunque",
    # Japanese
    "しかし", "でも", "けれども", "だが",
}

# Standard English seed dictionary (scaled -1.0 to 1.0)
CORE_WORDS: dict[str, float] = {
    "good": 0.5, "great": 0.8, "excellent": 0.9, "awesome": 0.9, "superb": 0.85,
    "love": 0.8, "loved": 0.8, "best": 0.9, "perfect": 0.9, "amazing": 0.85,
    "happy": 0.7, "satisfied": 0.7, "worth": 0.6, "nice": 0.5, "clean": 0.4,
    "fast": 0.4, "quiet": 0.5, "durable": 0.6, "premium": 0.7, "reliable": 0.7,
    "bad": -0.6, "worst": -0.9, "terrible": -0.9, "horrible": -0.9, "poor": -0.6,
    "broken": -0.8, "broke": -0.8, "break": -0.7, "cheap": -0.5, "useless": -0.8, "disappointed": -0.7,
    "noisy": -0.5, "slow": -0.5, "leaking": -0.6, "waste": -0.8, "defect": -0.7, "defective": -0.8,
    "flaw": -0.6, "fails": -0.7, "failed": -0.7, "stopped": -0.6, "hate": -0.8, "damaged": -0.8,
    "cracked": -0.7, "crack": -0.7, "burned": -0.8, "burn": -0.8,
}


class SentimentModel:
    """Clause-level multilingual sentiment model with pure text derivation and separate rating alignment."""

    _instance: SentimentModel | None = None

    def __init__(self, lexicon_path: Optional[Path] = None):
        settings = get_settings()
        self.lexicon_path = lexicon_path or (settings.config_dir / "lexicons" / "sentiment_lexicon.yaml")
        self.multilingual_path = settings.config_dir / "lexicons" / "multilingual_sentiment.yaml"
        self.lexicon: dict[str, float] = dict(CORE_WORDS)
        self._load_lexicons()

    @classmethod
    def get_instance(cls) -> SentimentModel:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_lexicons(self) -> None:
        # 1. Load VADER 7,500-word dictionary
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            vader_dict = SentimentIntensityAnalyzer().lexicon
            for k, v in vader_dict.items():
                self.lexicon[k.lower()] = max(-1.0, min(1.0, float(v) / 4.0))
        except Exception:
            pass

        # 2. Overlay Indian e-commerce & Hinglish YAML dictionary
        if self.lexicon_path.exists():
            try:
                with open(self.lexicon_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                raw_lex = data.get("lexicon", {})
                for k, v in raw_lex.items():
                    self.lexicon[k.lower()] = max(-1.0, min(1.0, float(v) / 4.0))
            except Exception:
                pass

        # 3. Overlay 16-language Multilingual Lexicon
        if self.multilingual_path.exists():
            try:
                with open(self.multilingual_path, "r", encoding="utf-8") as f:
                    multi_data = yaml.safe_load(f) or {}
                all_langs = multi_data.get("lexicons", {})
                for lang_code, lang_dict in all_langs.items():
                    for word, score in lang_dict.get("pos", {}).items():
                        self.lexicon[word.lower()] = float(score)
                    for word, score in lang_dict.get("neg", {}).items():
                        self.lexicon[word.lower()] = float(score)
            except Exception:
                pass

    def split_clauses(self, text: str) -> list[str]:
        """Split text by punctuation and contrast conjunctions into semantic clauses."""
        if not text:
            return []
        conjunctions_pattern = "|".join(re.escape(c) for c in sorted(CONTRAST_CONJUNCTIONS, key=len, reverse=True))
        # Support Western (.,!?;), Japanese (。、), and Indic (।) punctuation, plus whitespace/boundary conjunctions
        pattern = rf"[.!?,;\n\r\u3002\u3001\u0964]+|\s+(?:{conjunctions_pattern})\s+|\b(?:{conjunctions_pattern})\b"
        raw_splits = re.split(pattern, text, flags=re.IGNORECASE)
        clauses = [s.strip() for s in raw_splits if s and len(s.strip()) > 1]
        return clauses if clauses else [text.strip()]

    def analyze_clause(self, clause: str, rating: Optional[float] = None) -> Tuple[str, float]:
        """
        Analyze a single clause strictly from text.
        (Rating argument is maintained for backwards compatibility but is NOT blended into text polarity).
        Returns:
            polarity: 'pos' | 'neg' | 'neutral'
            score: float in [-1.0, 1.0]
        """
        clean_text = clause.lower().strip()
        if not clean_text:
            return "neutral", 0.0

        # Tokenize (extract words for spaces/alphanumeric, plus Indic scripts and CJK)
        # Match words or sequences of non-ASCII characters (e.g. Japanese, Hindi, Tamil)
        words = re.findall(r'[a-zàâçéèêëîïôûùüÿñæœäößáíóú]+|[\u0900-\u0D7F]+|[\u3040-\u30FF\u4E00-\u9FFF]+|[A-Za-z0-9]+', clean_text)
        if not words:
            # Fallback for scripts without spaces (e.g. Japanese)
            words = [clean_text]

        scores: list[float] = []
        is_litotes = False

        # Check multi-word phrases directly present in text
        for phrase, p_score in self.lexicon.items():
            if " " in phrase and phrase in clean_text:
                scores.append(p_score)

        for i, w in enumerate(words):
            if w in self.lexicon:
                base_score = self.lexicon[w]
            else:
                # Substring match for agglutinative/compound words and CJK / Indic characters
                matched_sub = None
                for lex_w, s in self.lexicon.items():
                    min_len = 1 if ord(lex_w[0]) > 0x0900 else 3
                    if len(lex_w) >= min_len and lex_w in w:
                        matched_sub = s
                        break
                if matched_sub is not None:
                    base_score = matched_sub
                else:
                    continue

            # Check 3-token negation window preceding (English, French, German, Spanish SVO)
            window_start = max(0, i - 3)
            preceding = words[window_start:i]
            # Check 2-token negation window succeeding (Indic SOV, Japanese SOV)
            succeeding = words[i + 1:min(len(words), i + 3)]

            negated = any(nw in NEGATION_TOKENS for nw in preceding) or any(nw in NEGATION_TOKENS for nw in succeeding)

            if negated:
                if base_score < -0.2:
                    # Litotes: "not bad", "kharab nahi", "nicht schlecht" -> mild positive/neutral +0.10
                    is_litotes = True
                    scores.append(0.10)
                else:
                    # Negated praise: "not good", "achha nahi" -> negative
                    scores.append(-base_score * 0.8)
            else:
                scores.append(base_score)

        if not scores:
            raw_polarity = 0.0
        else:
            raw_polarity = sum(scores) / len(scores)

        if is_litotes and raw_polarity <= 0:
            raw_polarity = 0.10

        combined = round(float(max(-1.0, min(1.0, raw_polarity))), 3)

        if combined > 0.15:
            polarity_label = "pos"
        elif combined < -0.15:
            polarity_label = "neg"
        else:
            polarity_label = "neutral"

        return polarity_label, combined

    def analyze_text(self, text: str, rating: Optional[float] = None) -> dict[str, Any]:
        """
        Analyzes complete review text.
        Returns:
            sentiment: 'positive' | 'negative' | 'mixed' | 'neutral' | 'unclear'
            score: float in [-1.0, 1.0]
            clauses: list of clause dictionaries
            rating_alignment: 'aligned' | 'conflict' | 'unknown'
        """
        if not text or len(text.strip()) == 0:
            return {
                "sentiment": "unclear",
                "score": 0.0,
                "clauses": [],
                "rating_alignment": "unknown",
            }

        clauses = self.split_clauses(text)
        clause_results = []
        pos_count = 0
        neg_count = 0
        clause_scores = []

        for c in clauses:
            pol, sc = self.analyze_clause(c)
            clause_results.append({"text": c, "polarity": pol, "score": sc})
            clause_scores.append(sc)
            if pol == "pos":
                pos_count += 1
            elif pol == "neg":
                neg_count += 1

        avg_score = sum(clause_scores) / len(clause_scores) if clause_scores else 0.0

        # Classify overall text sentiment
        if pos_count > 0 and neg_count > 0:
            overall_sentiment = "mixed"
        elif pos_count > 0 and neg_count == 0:
            overall_sentiment = "positive"
        elif neg_count > 0 and pos_count == 0:
            overall_sentiment = "negative"
        elif avg_score > 0.15:
            overall_sentiment = "positive"
        elif avg_score < -0.15:
            overall_sentiment = "negative"
        elif ((len(text.strip().split()) <= 1 if ord(text.strip()[0]) < 0x2000 else len(text.strip()) < 2)) and avg_score == 0.0:
            overall_sentiment = "unclear"
        else:
            overall_sentiment = "neutral"

        # Report rating/text alignment separately without altering text sentiment
        rating_alignment = "unknown"
        if rating is not None:
            if overall_sentiment == "positive":
                if rating >= 4.0:
                    rating_alignment = "aligned"
                elif rating <= 2.0:
                    rating_alignment = "conflict"
                else:
                    rating_alignment = "aligned"
            elif overall_sentiment == "negative":
                if rating <= 2.0:
                    rating_alignment = "aligned"
                elif rating >= 4.0:
                    rating_alignment = "conflict"
                else:
                    rating_alignment = "aligned"
            elif overall_sentiment == "neutral":
                if rating == 3.0:
                    rating_alignment = "aligned"
                else:
                    rating_alignment = "aligned"
            else:
                rating_alignment = "unknown"

        return {
            "sentiment": overall_sentiment,
            "score": round(avg_score, 3),
            "clauses": clause_results,
            "rating_alignment": rating_alignment,
        }

    def score_sentence(self, sentence: str, user_rating: float = 3.0) -> Tuple[str, float]:
        """
        Scores a single sentence, returning (polarity, score).
        polarity: 'pos' | 'neg' | 'neutral'
        score: float in [-1.0, 1.0]
        """
        return self.analyze_clause(sentence)

