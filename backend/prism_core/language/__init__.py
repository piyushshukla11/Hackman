"""
prism_core/language/__init__.py

L2 Clean — Language Normalisation.
Exposes:
def normalise(raw: RawReview) -> NormalisedReview
"""
from __future__ import annotations

import re
from typing import Sequence
from prism_core.ml.hinglish_detector import HinglishDetector
from prism_core.ml.language_detector import LanguageDetector
from prism_core.ml.translator import Translator
from prism_core.schemas.clean import NormalisedReview
from prism_core.schemas.raw_review import RawReview

EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)

_lang_detector = LanguageDetector()
_hinglish_detector = HinglishDetector()
_translator = Translator()


def extract_emojis(text: str) -> list[str]:
    """Find all emojis in text."""
    if not text:
        return []
    return EMOJI_REGEX.findall(text)


async def normalise(raw: RawReview) -> NormalisedReview:
    """
    Public entrypoint for L2 Language Normalisation.
    1. Extracts emojis
    2. Detects script and language
    3. Flags Hinglish if Romanized Hindi
    4. Translates to English
    """
    text = (raw.text or raw.title or "").strip()
    emojis = extract_emojis(text)

    # 1. Script & Base Language Detection
    lang_code, script, tier = _lang_detector.detect(text)

    # 2. Check for Hinglish in Latin script
    if script == "Latin" and _hinglish_detector.is_hinglish(text):
        lang_code = "hi-Latn"
        tier = 1

    # 3. Translation to English
    text_en, tier_penalty = await _translator.translate_to_en(text, lang_code)

    return NormalisedReview(
        lang=lang_code,
        script=script,
        text_original=text,
        text_en=text_en,
        emojis=emojis,
        lang_tier=tier,
        lang_tier_penalty=tier_penalty,
    )
