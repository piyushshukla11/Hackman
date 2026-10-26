"""
ml/translator.py

Translation service with in-memory PII masking.
Uses Sarvam Translate API for Indic languages with Gemini fallback.
PII never leaves the local process — masked before API call and restored in-memory.
"""
from __future__ import annotations

import os
import re
from typing import Tuple
import httpx

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
    email_idx = 0
    phone_idx = 0
    order_idx = 0

    def _replace_email(match):
        nonlocal email_idx
        token = f"[EMAIL_{email_idx}]"
        mapping[token] = match.group(0)
        email_idx += 1
        return token

    def _replace_phone(match):
        nonlocal phone_idx
        token = f"[PHONE_{phone_idx}]"
        mapping[token] = match.group(0)
        phone_idx += 1
        return token

    def _replace_order(match):
        nonlocal order_idx
        token = f"[ORDER_{order_idx}]"
        mapping[token] = match.group(0)
        order_idx += 1
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

    def __init__(
        self,
        sarvam_key: str | None = None,
        gemini_key: str | None = None,
        enable_sarvam: bool | None = None,
        llm_fallback_enabled: bool | None = None,
    ):
        self.sarvam_key = sarvam_key or os.environ.get("SARVAM_KEY")
        self.gemini_key = gemini_key or os.environ.get("GEMINI_KEY")
        self.enable_sarvam = enable_sarvam if enable_sarvam is not None else os.environ.get("ENABLE_SARVAM", "false").lower() in ("true", "1")
        self.llm_fallback_enabled = llm_fallback_enabled if llm_fallback_enabled is not None else os.environ.get("LLM_FALLBACK_ENABLED", "false").lower() in ("true", "1")

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
        if self.enable_sarvam and self.sarvam_key:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        "https://api.sarvam.ai/translate",
                        headers={"api-subscription-key": self.sarvam_key, "Content-Type": "application/json"},
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
        if self.llm_fallback_enabled and self.gemini_key:
            try:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}",
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
