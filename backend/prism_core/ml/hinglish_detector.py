"""
prism_core/ml/hinglish_detector.py

Detector for Hinglish (Hindi written in Roman/Latin script).
Identifies Indic function words, auxiliary verbs, and vernacular markers.
"""
from __future__ import annotations

import re

HINGLISH_FUNCTION_WORDS = {
    "hai", "hain", "kya", "nahi", "nahin", "na", "bhi", "toh", "to", "tha", "thi", "the",
    "hoga", "hogi", "bahut", "bohot", "wala", "wali", "wale", "lekin", "aur", "mat",
    "ye", "yeh", "wo", "woh", "acha", "achha", "kharab", "karo", "karna", "liya", "diya",
    "hota", "hoti", "raha", "rahi", "rahe", "apna", "apni", "mera", "meri", "kaise",
    "kyun", "kyu", "sabse", "ekdum", "bilkul", "sirf", "bhai", "yaar", "maal", "paisa",
    "paise", "kaam", "chal", "dekh", "samajh", "aaya", "aayi", "gaya", "gayi",
}


class HinglishDetector:
    """Classifies Latin-script text as Hinglish (hi-Latn) if Indic markers are prevalent."""

    def __init__(self, threshold: float = 0.12, min_distinct_words: int = 2):
        self.threshold = threshold
        self.min_distinct_words = min_distinct_words

    def is_hinglish(self, text: str) -> bool:
        if not text:
            return False

        # Tokenize lowercase words
        words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
        if not words:
            return False

        indic_matches = [w for w in words if w in HINGLISH_FUNCTION_WORDS]
        distinct_indic = set(indic_matches)

        ratio = len(indic_matches) / len(words)
        return ratio >= self.threshold and len(distinct_indic) >= self.min_distinct_words
