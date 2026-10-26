"""
prism_core/ml/language_detector.py

Script and language detector using Unicode script block analysis.
Supports all major Indic languages (Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, etc.)
and Latin script.
"""
from __future__ import annotations

import unicodedata
from typing import Literal

SCRIPT_RANGES = [
    ("Devanagari", 0x0900, 0x097F, "hi"),      # Hindi, Marathi, Sanskrit, Nepali
    ("Bengali", 0x0980, 0x09FF, "bn"),         # Bengali, Assamese
    ("Gurmukhi", 0x0A00, 0x0A7F, "pa"),        # Punjabi
    ("Gujarati", 0x0A80, 0x0AFF, "gu"),        # Gujarati
    ("Oriya", 0x0B00, 0x0B7F, "or"),           # Odia
    ("Tamil", 0x0B80, 0x0BFF, "ta"),           # Tamil
    ("Telugu", 0x0C00, 0x0C7F, "te"),          # Telugu
    ("Kannada", 0x0C80, 0x0CFF, "kn"),         # Kannada
    ("Malayalam", 0x0D00, 0x0D7F, "ml"),       # Malayalam
    ("Arabic", 0x0600, 0x06FF, "ur"),          # Urdu / Arabic
]

# Tiers per contracts.md
TIER_1_LANGS = {"en", "hi", "hi-Latn", "ta", "te", "bn", "mr", "gu", "kn", "ml"}
TIER_2_LANGS = {"pa", "or", "ur", "as"}


class LanguageDetector:
    """Lightweight rule-based script and language detector based on Unicode codepoints."""

    def detect(self, text: str) -> tuple[str, str, Literal[1, 2, 3]]:
        """
        Returns (bcp47_code, script_name, lang_tier).
        """
        if not text or not text.strip():
            return "en", "Latin", 1

        script_counts: dict[str, int] = {}
        lang_guesses: dict[str, str] = {}

        for char in text:
            cp = ord(char)
            matched = False
            for script_name, start, end, lang_code in SCRIPT_RANGES:
                if start <= cp <= end:
                    script_counts[script_name] = script_counts.get(script_name, 0) + 1
                    lang_guesses[script_name] = lang_code
                    matched = True
                    break
            if not matched and ('a' <= char.lower() <= 'z'):
                script_counts["Latin"] = script_counts.get("Latin", 0) + 1
                lang_guesses["Latin"] = "en"

        if not script_counts:
            return "en", "Latin", 1

        dominant_script = max(script_counts, key=script_counts.get)
        lang_code = lang_guesses.get(dominant_script, "en")

        if lang_code in TIER_1_LANGS:
            tier = 1
        elif lang_code in TIER_2_LANGS:
            tier = 2
        else:
            tier = 3

        return lang_code, dominant_script, tier
