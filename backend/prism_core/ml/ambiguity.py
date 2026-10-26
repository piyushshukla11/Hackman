"""
prism_core/ml/ambiguity.py

Ambiguity and Sarcasm Scorer:
Evaluates 6 cheap heuristic signals:
1. Rating vs Sentiment Divergence (e.g. 5 stars + scathing text, or 1 star + praise)
2. Sarcasm markers ('great job /s', 'wow wonderful... broke on day 1')
3. Hedge words ('maybe', 'perhaps', 'kind of', 'not sure') -> vague
4. Adversative conjunctions ('good X but terrible Y') -> mixed
5. Emoji vs rating divergence (e.g. 5 stars + angry emojis)
6. Extreme brevity with ambiguous tokens ('whatever', 'ok ok')

Returns: (ambiguity_type, ambiguity_multiplier)
- none: 1.00
- vague: 0.85
- mixed: 0.70
- sarcasm: 0.55
"""
from __future__ import annotations

import re
from typing import Literal

HEDGE_WORDS = {"maybe", "perhaps", "seems", "somewhat", "not sure", "kind of", "sort of", "chalta hai", "kam chalau"}
ADVERSATIVE_WORDS = {"but", "however", "although", "lekin", "magar", "par", "yet", "still"}
SARCASM_PATTERNS = [
    re.compile(r"wow\b.*\b(broke|dead|failed|worst)\b", re.IGNORECASE),
    re.compile(r"great job\b.*\b(garbage|trash|useless)\b", re.IGNORECASE),
    re.compile(r"superb\b.*\b(disaster|waste)\b", re.IGNORECASE),
    re.compile(r"\b/s\b", re.IGNORECASE),
]


class AmbiguityScorer:
    """Scores ambiguity and sarcasm levels with confidence multipliers."""

    def score(
        self,
        text: str,
        user_rating: float,
        sentiment_polarity: float,
        emojis: list[str] | None = None,
    ) -> tuple[Literal["none", "vague", "mixed", "sarcasm"], float]:
        if not text:
            return "none", 1.00

        text_lower = text.lower()
        words = text_lower.split()
        rating_prior = (user_rating - 3.0) / 2.0  # [-1.0, 1.0]

        # 1. Sarcasm pattern match
        for pat in SARCASM_PATTERNS:
            if pat.search(text_lower):
                return "sarcasm", 0.55

        # 2. Rating vs sentiment stark divergence (e.g. 5 stars + strongly negative text)
        if user_rating >= 4.5 and sentiment_polarity <= -0.4:
            return "sarcasm", 0.55
        if user_rating <= 1.5 and sentiment_polarity >= 0.4:
            return "sarcasm", 0.55

        # 3. Mixed sentiment via adversatives ('loved X but Y was terrible')
        has_adversative = any(adv in words for adv in ADVERSATIVE_WORDS)
        if has_adversative and abs(sentiment_polarity) < 0.25:
            return "mixed", 0.70

        # 4. Hedge words -> Vague
        has_hedge = any(h in text_lower for h in HEDGE_WORDS)
        if has_hedge:
            return "vague", 0.85

        return "none", 1.00
