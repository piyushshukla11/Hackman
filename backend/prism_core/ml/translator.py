"""
prism_core/ml/translator.py

Translation service with in-memory PII masking.
Uses Sarvam Translate API for Indic languages with Gemini fallback.
PII never leaves the local process — masked before API call and restored in-memory.
"""
from __future__ import annotations

import re
import httpx
from typing import Tuple

from prism_core.config.settings import Settings, get_settings

# PII Patterns
PHONE_REGEX = re.compile(r"(\+?91[\-\s]?)?[6-9]\d{9}\b|\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
ORDER_REGEX = re.compile(r"\b(ORD|OD|INV)[-_]?[A-Za-z0-9]{6,}\b", re.IGNORECASE)


def mask_pii(text: str) -> tuple[str, dict[str, str]]:
    """
    Mask sensitive PII with tokens.
    Returns (masked_text, mapping_to_restore).
    """
    mapping: dict[str, str] = {}
    email_c = 0
    phone_c = 0
    order_c = 0

    def _replace_email(match):
        nonlocal email_c
        token = f"[EMAIL_{email_c}]"
        mapping[token] = match.group(0)
        email_c += 1
        return token

    def _replace_phone(match):
        nonlocal phone_c
        token = f"[PHONE_{phone_c}]"
        mapping[token] = match.group(0)
        phone_c += 1
        return token

    def _replace_order(match):
        nonlocal order_c
        token = f"[ORDER_{order_c}]"
        mapping[token] = match.group(0)
        order_c += 1
        return token

    text = EMAIL_REGEX.sub(_replace_email, text)
    text = PHONE_REGEX.sub(_replace_phone, text)
    text = ORDER_REGEX.sub(_replace_order, text)

    return text, mapping



def restore_pii(text: str, mapping: dict[str, str]) -> str:
    """Restore original PII from in-memory mapping."""
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text


class Translator:
    """
    Translates non-English and vernacular Indic reviews into English.
    Integrates Sarvam API for Indic languages, Gemini fallback, and in-memory PII masking.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def translate_to_en(self, text: str, source_lang: str) -> tuple[str, bool]:
        """
        Translates text to English.
        Returns (text_en, lang_tier_penalty).
        """
        if not text or not text.strip():
            return text, False

        # If already standard English, no translation needed
        if source_lang == "en":
            return text, False

        # Step 1: Mask PII in memory
        masked_text, pii_map = mask_pii(text)

        # Step 2: Try Sarvam API if configured
        sarvam_key = (
            self.settings.sarvam_key.get_secret_value()
            if self.settings.sarvam_key and hasattr(self.settings.sarvam_key, "get_secret_value")
            else None
        )

        if self.settings.enable_sarvam and sarvam_key:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        "https://api.sarvam.ai/translate",
                        headers={"api-subscription-key": sarvam_key, "Content-Type": "application/json"},
                        json={
                            "input": masked_text,
                            "source_language_code": source_lang if source_lang != "hi-Latn" else "hi-IN",
                            "target_language_code": "en-IN",
                            "speaker_gender": "Female",
                            "mode": "formal",
                        },
                    )
                    if resp.status_code == 200:
                        translated = resp.json().get("translated_text", masked_text)
                        return restore_pii(translated, pii_map), False
            except Exception:
                pass  # Fall through to Gemini or original

        # Step 3: Try Gemini fallback if configured
        gemini_key = (
            self.settings.gemini_key.get_secret_value()
            if self.settings.gemini_key and hasattr(self.settings.gemini_key, "get_secret_value")
            else None
        )

        if self.settings.llm_fallback_enabled and gemini_key:
            try:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}",
                        headers={"Content-Type": "application/json"},
                        json={
                            "contents": [{
                                "parts": [{
                                    "text": f"Translate the following customer feedback into clear English. Preserve tone, product terms, and any bracketed tokens like [EMAIL_0] or [PHONE_0] exactly.\n\nText: {masked_text}"
                                }]
                            }]
                        },
                    )
                    if resp.status_code == 200:
                        candidates = resp.json().get("candidates", [])
                        if candidates:
                            translated = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                            if translated:
                                return restore_pii(translated, pii_map), False
            except Exception:
                pass

        # Fallback: keep original text and flag lang_tier_penalty
        return restore_pii(masked_text, pii_map), True
