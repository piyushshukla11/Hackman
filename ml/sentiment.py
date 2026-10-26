"""
ml/sentiment.py

Augmented Sentiment Model:
- Full 7,500-word VADER engine augmented with Indian e-commerce & Hinglish dictionary
- Negation handling and booster words
- Rating prior blend: r' = (rating - 3) / 2
- Microsecond execution speed per feature sentence
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
import yaml


class SentimentModel:
    """Fast sentiment analysis combining VADER + Indian e-commerce lexicon + rating prior."""

    _instance: SentimentModel | None = None

    def __init__(self, lexicon_path: Path | str | None = None):
        if lexicon_path is not None:
            self.lexicon_path = Path(lexicon_path)
        else:
            default_path = Path(__file__).parent / "lexicons" / "sentiment_lexicon.yaml"
            env_path = os.environ.get("LEXICON_PATH")
            self.lexicon_path = Path(env_path) if env_path else default_path

        self.analyzer = None
        self.custom_lexicon: dict[str, float] = {}
        self._init_analyzer()

    @classmethod
    def get_instance(cls) -> SentimentModel:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_analyzer(self) -> None:
        # Load curated Indian e-commerce / Hinglish dictionary
        if self.lexicon_path and self.lexicon_path.exists():
            try:
                with open(self.lexicon_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    self.custom_lexicon = data.get("lexicon", {})
            except Exception:
                self.custom_lexicon = {}

        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self.analyzer = SentimentIntensityAnalyzer()
            # Augment VADER dictionary with custom Indian e-commerce words
            self.analyzer.lexicon.update(self.custom_lexicon)
        except ImportError:
            # Standalone fallback if vaderSentiment package is not yet installed
            self.analyzer = None

    def score_sentence(self, sentence: str, user_rating: float = 3.0) -> tuple[Literal["pos", "neg", "neutral"], float]:
        """
        Calculates polarity for a sentence.
        Blends VADER compound score with rating prior:
        r' = (user_rating - 3.0) / 2.0  (in [-1.0, 1.0])
        blended = 0.65 * vader + 0.35 * r'
        """
        if not sentence or not sentence.strip():
            rating_prior = (user_rating - 3.0) / 2.0
            pol: Literal["pos", "neg", "neutral"] = "pos" if rating_prior > 0.1 else ("neg" if rating_prior < -0.1 else "neutral")
            return pol, rating_prior

        vader_compound = 0.0
        if self.analyzer is not None:
            scores = self.analyzer.polarity_scores(sentence)
            vader_compound = scores.get("compound", 0.0)
        else:
            # Fallback simple dictionary match if vader package not installed
            tokens = sentence.lower().split()
            matched = [self.custom_lexicon.get(t, 0.0) for t in tokens if t in self.custom_lexicon]
            if matched:
                vader_compound = max(-1.0, min(1.0, sum(matched) / (len(matched) * 4.0)))

        # Rating prior r' in [-1.0, 1.0]
        rating_prior = (user_rating - 3.0) / 2.0
        blended = (0.65 * vader_compound) + (0.35 * rating_prior)
        blended = max(-1.0, min(1.0, round(blended, 3)))

        if blended > 0.10:
            polarity: Literal["pos", "neg", "neutral"] = "pos"
        elif blended < -0.10:
            polarity = "neg"
        else:
            polarity = "neutral"

        return polarity, blended
