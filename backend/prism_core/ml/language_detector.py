"""
prism_core/ml/language_detector.py

Script and language detector supporting:
- 11 Indian languages:
  1. Hindi (hi)
  2. Marathi (mr)
  3. Bengali (bn)
  4. Assamese (as)
  5. Gujarati (gu)
  6. Punjabi (pa)
  7. Odia (or)
  8. Tamil (ta)
  9. Telugu (te)
  10. Kannada (kn)
  11. Malayalam (ml)
  Plus Romanized Hinglish (hi-Latn)
- 5 International languages:
  12. English (en)
  13. French (fr)
  14. German (de)
  15. Japanese (ja)
  16. Spanish (es)
"""
from __future__ import annotations

import re
from typing import Literal

SCRIPT_RANGES = [
    ("Japanese_Hiragana", 0x3040, 0x309F, "ja"),
    ("Japanese_Katakana", 0x30A0, 0x30FF, "ja"),
    ("Kannada", 0x0C80, 0x0CFF, "kn"),
    ("Telugu", 0x0C00, 0x0C7F, "te"),
    ("Tamil", 0x0B80, 0x0BFF, "ta"),
    ("Malayalam", 0x0D00, 0x0D7F, "ml"),
    ("Oriya", 0x0B00, 0x0B7F, "or"),
    ("Gurmukhi", 0x0A00, 0x0A7F, "pa"),
    ("Gujarati", 0x0A80, 0x0AFF, "gu"),
    ("Bengali", 0x0980, 0x09FF, "bn"),
    ("Devanagari", 0x0900, 0x097F, "hi"),
    ("CJK", 0x4E00, 0x9FFF, "ja"),
]

# Distinctive markers for shared scripts
# 1. Devanagari (Hindi vs Marathi)
MARATHI_MARKERS = {
    "आहे", "नाही", "छान", "वाईट", "खूप", "झाला", "झाली", "झाले",
    "केला", "केली", "केले", "उत्कृष्ट", "भारी", "पण", "आहेत",
    "होता", "होती", "होते", "नाहीत", "कसा", "कशी", "कसे", "दर्जा",
    "लगेच", "तुटले", "काम", "बॅटरी", "मोबाईल"
}
HINDI_MARKERS = {
    "है", "हैं", "नहीं", "नही", "था", "थी", "थे", "अच्छा", "अच्छी", "अच्छे",
    "बुरा", "बुरी", "बहुत", "लेकिन", "मगर", "और", "किया", "गया", "गई", "गए",
    "धोखेबाजी", "घटिया", "बकवास", "शानदार", "बेहतरीन", "का", "की", "के",
    "में", "से", "पर", "को", "करता", "करती", "करते", "बिल्कुल", "सही"
}

# 2. Eastern Nagari (Bengali vs Assamese)
ASSAMESE_MARKERS = {
    "ভাল", "বেয়া", "নহয়", "আছে", "সুন্দৰ", "বঢ়িয়া", "কিয়",
    "হ'ল", "গ'ল", "এদিনতে", "ভাঙা", "বহুত", "আৰু", "প্ৰডাক্ট",
    "কোৱালিটি", "এইটো", "নাক"
}
BENGALI_MARKERS = {
    "খুব", "ভালো", "বাজে", "নিকৃষ্ট", "টাকা", "অপচয়", "চমৎকার",
    "দুর্দান্ত", "লাগল", "লাগলো", "নয়", "নেই", "হলো", "গেলো",
    "জন্য", "একটি", "করুন", "এবং", "কোয়ালিটি", "ভাঙলো", "জিনিস", "জিনিসটা"
}

FRENCH_TOKENS = {"est", "très", "avec", "pour", "bon", "bonne", "mauvais", "mauvaise", "pas", "ce", "merci", "parfait", "déçu", "mais"}
GERMAN_TOKENS = {"ist", "nicht", "sehr", "gut", "schlecht", "mit", "und", "das", "der", "die", "aber", "kaputt", "toll", "perfekt"}
SPANISH_TOKENS = {"es", "muy", "bueno", "buena", "malo", "mala", "pero", "con", "por", "para", "excelente", "pésimo", "gracias", "roto"}

HINGLISH_FUNCTION_WORDS = {
    "hai", "hain", "tha", "thi", "the", "nahi", "nhi", "na", "mat", "bahut", "bohot",
    "badiya", "badhiya", "bekar", "bakwas", "khatam", "ekdum", "karna", "padta", "paisa",
    "vasool", "chahiye", "chal", "lekin", "magar", "aur", "ya", "bhi", "toh", "kharab",
    "mast", "thik", "theek", "yaar", "bhai", "samajh", "aaya", "dekh", "karo", "accha", "achha"
}

TIER_1_LANGS = {"en", "hi", "hi-Latn", "ta", "te", "bn", "mr", "gu", "kn", "ml", "ja", "fr", "de", "es"}
TIER_2_LANGS = {"pa", "or", "as"}


class LanguageDetectionResult:
    """
    Rich detection result supporting:
    - 3-tuple unpacking: `lang, script, tier = detector.detect(text)`
    - Structured attribute access: `.lang`, `.script`, `.tier`, `.candidate_langs`, `.request_review`
    """

    def __init__(
        self,
        lang: str,
        script: str,
        tier: Literal[1, 2, 3],
        candidate_langs: list[str] | None = None,
        request_review: bool = False,
    ):
        self.lang = lang
        self.script = script
        self.tier = tier
        self.candidate_langs = candidate_langs or ([lang] if lang != "unclear" else [])
        self.request_review = request_review

    def __iter__(self):
        yield self.lang
        yield self.script
        yield self.tier

    def __getitem__(self, idx: int):
        return [self.lang, self.script, self.tier, self.candidate_langs, self.request_review][idx]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, tuple):
            return (self.lang, self.script, self.tier) == other
        if isinstance(other, LanguageDetectionResult):
            return (
                self.lang == other.lang and
                self.script == other.script and
                self.tier == other.tier and
                self.candidate_langs == other.candidate_langs and
                self.request_review == other.request_review
            )
        return False

    def __repr__(self) -> str:
        return (
            f"LanguageDetectionResult(lang={self.lang!r}, script={self.script!r}, "
            f"tier={self.tier}, candidates={self.candidate_langs!r}, request_review={self.request_review})"
        )


class LanguageDetector:
    """Multi-script and multi-language detector with shared-script disambiguation."""

    def detect(self, text: str) -> LanguageDetectionResult:
        """
        Detects script and language.
        For shared scripts (Devanagari, Eastern Nagari):
        - Disambiguates based on distinctive characters and grammatical markers.
        - Never silently defaults ambiguous text (e.g., does not label ambiguous Assamese as Bengali,
          or ambiguous Marathi as Hindi).
        - Returns lang='unclear' with explicit candidate set and request_review=True when evidence is weak.
        """
        if not text or not text.strip():
            return LanguageDetectionResult("en", "Latin", 1, candidate_langs=["en"], request_review=False)

        script_counts: dict[str, int] = {}
        lang_guesses: dict[str, str] = {}

        for char in text:
            cp = ord(char)
            matched = False
            for script_name, start, end, lang_code in SCRIPT_RANGES:
                if start <= cp <= end:
                    base_script = "Japanese" if "Japanese" in script_name or script_name == "CJK" else script_name
                    script_counts[base_script] = script_counts.get(base_script, 0) + 1
                    lang_guesses[base_script] = lang_code
                    matched = True
                    break
            if not matched and ('a' <= char.lower() <= 'z' or cp in (0xE0, 0xE2, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xEE, 0xEF, 0xF4, 0xF9, 0xFB, 0xFC, 0xDF, 0xE4, 0xF6, 0xFC, 0xF1, 0xE1, 0xED, 0xF3, 0xFA)):
                script_counts["Latin"] = script_counts.get("Latin", 0) + 1
                lang_guesses["Latin"] = "en"

        if not script_counts:
            return LanguageDetectionResult("en", "Latin", 1, candidate_langs=["en"], request_review=False)

        dominant_script = max(script_counts, key=script_counts.get)
        lang_code = lang_guesses.get(dominant_script, "en")
        candidate_langs: list[str] = [lang_code]
        request_review = False

        # Disambiguate shared scripts
        if dominant_script == "Devanagari":
            words_dev = set(re.findall(r'[\u0900-\u097F]+', text))
            # Marathi unique character: U+0933 (ळ)
            has_marathi_lla = "ळ" in text
            mr_hits = sum(1 for w in words_dev if w in MARATHI_MARKERS) + (3 if has_marathi_lla else 0)
            hi_hits = sum(1 for w in words_dev if w in HINDI_MARKERS)

            if mr_hits > 0 and hi_hits == 0:
                lang_code = "mr"
                candidate_langs = ["mr"]
                request_review = False
            elif hi_hits > 0 and mr_hits == 0:
                lang_code = "hi"
                candidate_langs = ["hi"]
                request_review = False
            elif mr_hits > 0 and hi_hits > 0:
                if mr_hits >= hi_hits + 2:
                    lang_code = "mr"
                    candidate_langs = ["mr", "hi"]
                    request_review = False
                elif hi_hits >= mr_hits + 2:
                    lang_code = "hi"
                    candidate_langs = ["hi", "mr"]
                    request_review = False
                else:
                    lang_code = "unclear"
                    candidate_langs = ["hi", "mr"]
                    request_review = True
            else:
                # Neither Hindi nor Marathi distinctive markers found: do NOT silently label as Hindi!
                lang_code = "unclear"
                candidate_langs = ["hi", "mr"]
                request_review = True

        elif dominant_script == "Bengali":
            words_ben = set(re.findall(r'[\u0980-\u09FF]+', text))
            # Unique characters:
            # Assamese: U+09F0 (ৰ - Assamese Ra), U+09F1 (ৱ - Assamese Wa)
            # Note: U+09B0 (র) alone in loanwords or numbers without grammatical markers is ambiguous
            has_as_chars = any(c in text for c in ("ৰ", "ৱ"))
            has_bn_ra = "র" in text

            as_hits = sum(1 for w in words_ben if w in ASSAMESE_MARKERS) + (3 if has_as_chars else 0)
            # Require distinctive Bengali markers or multiple strong Bengali markers
            bn_hits = sum(1 for w in words_ben if w in BENGALI_MARKERS)
            if has_bn_ra and bn_hits > 0:
                bn_hits += 1

            if as_hits > 0 and bn_hits == 0:
                lang_code = "as"
                candidate_langs = ["as"]
                request_review = False
            elif bn_hits > 0 and as_hits == 0:
                lang_code = "bn"
                candidate_langs = ["bn"]
                request_review = False
            elif as_hits > 0 and bn_hits > 0:
                if as_hits >= bn_hits + 2:
                    lang_code = "as"
                    candidate_langs = ["as", "bn"]
                    request_review = False
                elif bn_hits >= as_hits + 2:
                    lang_code = "bn"
                    candidate_langs = ["bn", "as"]
                    request_review = False
                else:
                    lang_code = "unclear"
                    candidate_langs = ["as", "bn"]
                    request_review = True
            else:
                # Neither Assamese nor Bengali distinctive markers found: do NOT silently label as Bengali!
                lang_code = "unclear"
                candidate_langs = ["as", "bn"]
                request_review = True


        elif dominant_script == "Latin":
            text_lower = text.lower()
            words_lat = set(re.findall(r'\b[a-zàâçéèêëîïôûùüÿñæœäößáíóú]+\b', text_lower))

            # 1. Check Hinglish / Romanized Indic
            indic_hits = sum(1 for w in words_lat if w in HINGLISH_FUNCTION_WORDS)
            if indic_hits >= 2 or (indic_hits == 1 and len(words_lat) <= 5):
                lang_code = "hi-Latn"
                candidate_langs = ["hi-Latn"]
            else:
                es_score = len(words_lat.intersection(SPANISH_TOKENS)) * 2 + sum(1 for c in text_lower if c in ("ñ", "¿", "¡")) * 3 + sum(1 for c in text_lower if c in ("á", "í", "ó", "ú"))
                fr_score = len(words_lat.intersection(FRENCH_TOKENS)) * 2 + sum(1 for c in text_lower if c in ("ç", "œ", "à", "ù", "ê", "è")) * 2
                de_score = len(words_lat.intersection(GERMAN_TOKENS)) * 2 + sum(1 for c in text_lower if c in ("ä", "ö", "ü", "ß")) * 3

                scores = [("es", es_score), ("fr", fr_score), ("de", de_score)]
                best_lang, best_score = max(scores, key=lambda x: x[1])
                if best_score >= 2:
                    lang_code = best_lang
                    candidate_langs = [best_lang]
                else:
                    lang_code = "en"
                    candidate_langs = ["en"]

        tier: Literal[1, 2, 3] = 1 if lang_code in TIER_1_LANGS else (2 if lang_code in TIER_2_LANGS else 3)
        return LanguageDetectionResult(
            lang=lang_code,
            script=dominant_script,
            tier=tier,
            candidate_langs=candidate_langs,
            request_review=request_review,
        )

