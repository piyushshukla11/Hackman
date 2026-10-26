"""
ml/llm_client.py

Gemini LLM Client with structured output and rule-based fallback:
- Ambiguity & sarcasm resolution
- RAG-grounded diagnostic survey question drafting
- Image OCR for Batch Inference (B1)
"""
from __future__ import annotations

import json
import os
from typing import Any
import httpx


class LLMClient:
    """Client for Gemini structured JSON outputs with guaranteed graceful offline fallbacks."""

    def __init__(self, gemini_key: str | None = None, llm_fallback_enabled: bool | None = None):
        self.gemini_key = gemini_key or os.environ.get("GEMINI_KEY")
        self.llm_fallback_enabled = llm_fallback_enabled if llm_fallback_enabled is not None else os.environ.get("LLM_FALLBACK_ENABLED", "false").lower() in ("true", "1")

    async def generate_rag_survey_questions(
        self,
        feature: str,
        verbatims: list[str],
        specs: dict[str, Any],
        batch_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        RAG-grounded diagnostic question generator:
        Injects customer quotes, specs, and batch info into Gemini prompt to draft 3 targeted root-cause diagnostic questions.
        """
        if not self.gemini_key or not self.llm_fallback_enabled:
            return self._fallback_survey_questions(feature)

        prompt = (
            f"You are an expert product reliability engineering diagnostic assistant. "
            f"A cluster of customer defect complaints has emerged around the feature '{feature}'.\n"
            f"Batch Info: {batch_code or 'Unknown'}\n"
            f"Product Specs: {json.dumps(specs)}\n"
            f"Customer Verbatims:\n" + "\n".join(f"- {q}" for q in verbatims[:4]) + "\n\n"
            f"Draft exactly 3 multiple-choice diagnostic questions to isolate the mechanical/firmware root cause. "
            f"Respond with a valid JSON array of objects with keys 'question_id', 'question_text', 'options' (list of strings)."
        )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"response_mime_type": "application/json"},
                    },
                )
                if resp.status_code == 200:
                    candidates = resp.json().get("candidates", [])
                    if candidates:
                        text_resp = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(text_resp)
                        if isinstance(parsed, list) and len(parsed) >= 1:
                            return parsed[:3]
        except Exception:
            pass

        return self._fallback_survey_questions(feature)

    def _fallback_survey_questions(self, feature: str) -> list[dict[str, Any]]:
        """Calibrated fallback diagnostic questions if LLM unavailable."""
        return [
            {
                "question_id": "q1",
                "question_text": f"When did you first notice the issue with {feature}?",
                "options": [
                    "Immediately out of the box",
                    "Within first 7 days",
                    "After 2-4 weeks",
                    "After a software update",
                    "I'm not sure",
                ],
                "evidence_refs": [],
                "rationale": f"Determines failure onset latency for {feature} defects.",
                "is_fallback": True,
            },
            {
                "question_id": "q2",
                "question_text": f"What was the environmental condition when {feature} failed?",
                "options": [
                    "Normal indoor usage",
                    "During outdoor travel / heat",
                    "While charging",
                    "Under heavy load",
                    "I'm not sure",
                ],
                "evidence_refs": [],
                "rationale": f"Isolates ambient operating stress factors triggering {feature} failure.",
                "is_fallback": True,
            },
            {
                "question_id": "q3",
                "question_text": f"Did restarting or power cycling resolve the {feature} issue?",
                "options": [
                    "Yes, permanently",
                    "Yes, but issue recurred",
                    "No effect at all",
                    "Device became unresponsive",
                    "I'm not sure",
                ],
                "evidence_refs": [],
                "rationale": f"Differentiates persistent hardware defects from transient state/firmware latching in {feature}.",
                "is_fallback": True,
            },
        ]
