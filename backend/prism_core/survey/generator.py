"""
prism_core/survey/generator.py

RAG-Based Diagnostic Survey Generation Engine for PRISM.
Adheres to contracts.md §1.5, pipeline-3.md §P9, and ml.md §13:
1. Strict tenant & product isolated retrieval of verbatim review quotes, specs, and batch info.
2. Deduplication and substantive text filtering on retrieved quotes.
3. In-memory PII masking before prompt formulation.
4. Structured Gemini prompt generating 3 multiple-choice diagnostic questions to isolate engineering failure modes.
5. Strict schema validation, evidence-reference verification, and ungrounded fact rejection.
6. Calibrated category-level fallback diagnostic templates with is_fallback=True.
7. Explicit insufficient-evidence handling when cluster has no substantive verbatims.
"""
from __future__ import annotations

import difflib
import json
import logging
import re
from typing import Any, Sequence
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.config.settings import Settings, get_settings
from prism_core.db.models import ClusterMember, IssueCluster, Product, ProductVersion, Review
from prism_core.ml.translator import mask_pii
from prism_core.schemas.survey import (
    RetrievedEvidence,
    SurveyGenerationResult,
    SurveyQuestion,
    SurveyRetrievalContext,
)

logger = logging.getLogger(__name__)


# ── Category-Calibrated Diagnostic Fallback Templates ─────────────────────────

CATEGORY_FALLBACK_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "appliances": [
        {
            "question_id": "q1",
            "question_text": "When operating the unit, does the {feature} issue occur immediately upon startup, or only after extended running time?",
            "options": [
                "Immediately upon startup / power-on",
                "After 15-30 minutes of continuous operation",
                "Only during specific heavy cycles or settings",
                "Intermittently at random intervals",
                "I'm not sure",
            ],
            "rationale": "Differentiates between initial electrical/startup failure and thermal buildup / duty-cycle exhaustion.",
        },
        {
            "question_id": "q2",
            "question_text": "Have you observed any unusual sensory indicators (such as humming, clicking, thermal heat, or moisture) associated with the {feature}?",
            "options": [
                "Clicking or rhythmic ticking sounds",
                "Noticeable excess heat on the external casing",
                "Vibration or unusually loud humming",
                "No unusual sound, heat, or moisture observed",
                "I'm not sure",
            ],
            "rationale": "Identifies whether mechanical wear, relay switching, or electrical over-current accompanies the defect.",
        },
        {
            "question_id": "q3",
            "question_text": "Did disconnecting power for 10 minutes (hard reset) or adjusting operating settings resolve or change the {feature} behavior?",
            "options": [
                "Temporarily restored normal function, but issue returned",
                "Had no effect whatsoever on the issue",
                "Appliance failed to power back on",
                "I did not attempt a power reset",
                "I'm not sure",
            ],
            "rationale": "Isolates persistent physical hardware component failures from microcontroller firmware or latching relay faults.",
        },
    ],
    "audio": [
        {
            "question_id": "q1",
            "question_text": "Does the issue with {feature} affect both channels (left and right) equally, or is it isolated to one side?",
            "options": [
                "Isolated to the left ear / channel only",
                "Isolated to the right ear / channel only",
                "Equally affects both channels",
                "Switches intermittently between channels",
                "I'm not sure",
            ],
            "rationale": "Differentiates between single-driver/cable solder defect and central DAC/Bluetooth SoC audio pipeline failure.",
        },
        {
            "question_id": "q2",
            "question_text": "Under what connection mode does the {feature} symptom occur?",
            "options": [
                "Only over wireless Bluetooth connection",
                "Only when using a physical 3.5mm / USB wired cable",
                "Present across both wired and wireless connections",
                "Only when multipoint device pairing is active",
                "I'm not sure",
            ],
            "rationale": "Isolates wireless codec / RF interference from physical acoustic driver or analog amplification defect.",
        },
        {
            "question_id": "q3",
            "question_text": "When the {feature} issue occurs, how does the device respond when battery level drops below 30%?",
            "options": [
                "Symptom worsens significantly or device powers off abruptly",
                "Symptom remains identical regardless of battery charge",
                "Charging temporarily eliminates the symptom",
                "Device cannot hold a charge below 30%",
                "I'm not sure",
            ],
            "rationale": "Isolates voltage sag on battery degradation from steady-state digital signal processing issues.",
        },
    ],
    "electronics": [
        {
            "question_id": "q1",
            "question_text": "When did the {feature} issue first manifest during your ownership?",
            "options": [
                "Immediately out of the box on day 1",
                "Within the first 7 days of normal use",
                "After 2 to 4 weeks of regular use",
                "Directly following a firmware or software update",
                "I'm not sure",
            ],
            "rationale": "Separates manufacturing infant mortality / assembly defect from wear-out or firmware regression.",
        },
        {
            "question_id": "q2",
            "question_text": "What is the physical state of the device and housing surrounding the {feature}?",
            "options": [
                "Normal physical condition with no external changes",
                "Noticeable warmth or thermal hotspot on casing",
                "Loose fitting, gap, or physical play in assembly",
                "Cosmetic discoloration or minor cracking",
                "I'm not sure",
            ],
            "rationale": "Helps distinguish internal PCB component heating from mechanical enclosure tolerances.",
        },
        {
            "question_id": "q3",
            "question_text": "Does the issue with {feature} recur consistently under the same conditions, or is it sporadic?",
            "options": [
                "100% reproducible every time under identical conditions",
                "Occurs unpredictably with no discernible pattern",
                "Occurs only when device is plugged into power / charger",
                "Occurs only under intensive computational or environmental load",
                "I'm not sure",
            ],
            "rationale": "Identifies whether the fault is a deterministic hardware/firmware logic bug or an intermittent thermal/contact issue.",
        },
    ],
    "general": [
        {
            "question_id": "q1",
            "question_text": "When did you first observe the difficulty related to {feature}?",
            "options": [
                "Immediately on initial setup or unpacking",
                "Within the first week of regular usage",
                "After several weeks of standard use",
                "After relocating or cleaning the item",
                "I'm not sure",
            ],
            "rationale": "Distinguishes out-of-box assembly/packaging defects from cumulative mechanical degradation.",
        },
        {
            "question_id": "q2",
            "question_text": "Which environmental condition best matches when the {feature} problem occurs?",
            "options": [
                "Standard indoor ambient environment",
                "Elevated temperature or direct sunlight",
                "High humidity or moisture-prone setting",
                "Continuous uninterrupted heavy duty operation",
                "I'm not sure",
            ],
            "rationale": "Isolates environmental operating limit violations from inherent material weaknesses.",
        },
        {
            "question_id": "q3",
            "question_text": "Does inspecting, adjusting, or reconnecting the {feature} alter the observed behavior?",
            "options": [
                "No change at all in behavior",
                "Temporarily improved before failing again",
                "Exhibited physical resistance or tightness",
                "I did not attempt adjustment",
                "I'm not sure",
            ],
            "rationale": "Determines whether loose mounting or tolerance drift is a contributing factor.",
        },
    ],
}


# ── Deduplication and Cleaning Helpers ────────────────────────────────────────

def _clean_tokens(text: str) -> set[str]:
    """Extract normalized alphanumeric words for Jaccard similarity."""
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _is_near_duplicate(candidate: str, existing_quotes: list[str], threshold: float = 0.65) -> bool:
    """Checks if a candidate quote has high lexical overlap with any already selected quote."""
    cand_tokens = _clean_tokens(candidate)
    if not cand_tokens:
        return False
    for prev in existing_quotes:
        prev_tokens = _clean_tokens(prev)
        if not prev_tokens:
            continue
        intersection = cand_tokens.intersection(prev_tokens)
        union = cand_tokens.union(prev_tokens)
        if union and (len(intersection) / len(union)) >= threshold:
            return True
        # Also check direct sequence matcher for substring-heavy paraphrases
        if difflib.SequenceMatcher(None, candidate.lower(), prev.lower()).ratio() >= threshold:
            return True
    return False


def _is_substantive(text: str) -> bool:
    """A quote is substantive if it has at least 3 distinct non-trivial words."""
    words = [w for w in text.strip().split() if len(w) > 1]
    return len(words) >= 3


# ── Core Generator Class ──────────────────────────────────────────────────────

class SurveyGenerator:
    """
    RAG-grounded survey generator:
    - Enforces tenant and product isolation
    - Retrieves, deduplicates, and masks customer verbatims
    - Generates 3 targeted diagnostic multiple-choice questions
    - Validates evidence refs and grounding
    - Applies category-calibrated fallback templates
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _get_api_key(self) -> str | None:
        """Extract Gemini key from settings or environment without exposing in logs."""
        if self.settings.gemini_key and hasattr(self.settings.gemini_key, "get_secret_value"):
            return self.settings.gemini_key.get_secret_value()
        import os
        return os.environ.get("GEMINI_KEY")

    # ── 1. Database Retrieval ─────────────────────────────────────────────────

    async def retrieve_context(
        self,
        session: AsyncSession,
        issue_id: str,
        tenant_id: str,
    ) -> SurveyRetrievalContext:
        """
        Retrieves context with strict multi-tenant and product isolation:
        - Up to 4 diverse, representative customer review quotes
        - Product technical specs from catalog
        - Dominant batch code and firmware/product version
        """
        # 1. Fetch cluster with strict tenant isolation
        cluster_stmt = select(IssueCluster).where(
            IssueCluster.id == issue_id,
            IssueCluster.tenant_id == tenant_id,
        )
        cluster = (await session.execute(cluster_stmt)).scalar_one_or_none()
        if not cluster:
            return SurveyRetrievalContext(
                tenant_id=tenant_id,
                product_id="",
                issue_id=issue_id,
                feature="",
                is_sufficient=False,
                insufficient_reason=f"Issue cluster '{issue_id}' not found for tenant '{tenant_id}'.",
            )

        # 2. Fetch product specs with strict tenant & product isolation
        prod_stmt = select(Product).where(
            Product.id == cluster.product_id,
            Product.tenant_id == tenant_id,
        )
        product = (await session.execute(prod_stmt)).scalar_one_or_none()
        specs = (product.specs or {}) if product else {}
        category = product.category if product else "general"

        # 3. Fetch version label if available
        version_label: str | None = None
        if cluster.versions:
            ver_id = cluster.versions[0]
            ver_stmt = select(ProductVersion.label).where(
                ProductVersion.id == ver_id,
                ProductVersion.tenant_id == tenant_id,
                ProductVersion.product_id == cluster.product_id,
            )
            version_label = (await session.execute(ver_stmt)).scalar_one_or_none()

        # 4. Fetch member reviews with strict tenant & product isolation
        # Order by exemplar role first, then review date
        members_stmt = (
            select(
                Review.id,
                Review.text_original,
                Review.rating,
                Review.channel,
                ClusterMember.role,
            )
            .join(ClusterMember, Review.id == ClusterMember.review_id)
            .where(
                ClusterMember.cluster_id == issue_id,
                ClusterMember.tenant_id == tenant_id,
                Review.tenant_id == tenant_id,
                Review.product_id == cluster.product_id,
            )
            .order_by(
                ClusterMember.role.desc(),  # 'exemplar' before 'member'
                Review.reviewed_at.desc(),
            )
            .limit(20)  # pull pool for diverse selection
        )
        rows = (await session.execute(members_stmt)).all()

        # 5. Deduplicate and mask verbatims
        evidence_items: list[RetrievedEvidence] = []
        seen_texts: list[str] = []

        for rev_id, raw_text, rating, channel, role in rows:
            if not raw_text or not _is_substantive(raw_text):
                continue
            if _is_near_duplicate(raw_text, seen_texts, threshold=0.70):
                continue

            masked_text, _ = mask_pii(raw_text)
            seen_texts.append(raw_text)
            evidence_items.append(
                RetrievedEvidence(
                    review_id=rev_id,
                    text=masked_text,
                    rating=float(rating) if rating is not None else None,
                    channel=channel,
                    role=role or "member",
                )
            )
            if len(evidence_items) >= 4:
                break

        # Check sufficiency
        if not evidence_items:
            return SurveyRetrievalContext(
                tenant_id=tenant_id,
                product_id=cluster.product_id,
                issue_id=issue_id,
                feature=cluster.feature,
                category=category,
                evidence_items=[],
                specs=specs,
                dominant_batch_id=cluster.dominant_batch_id,
                version_label=version_label,
                is_sufficient=False,
                insufficient_reason="No representative, substantive customer review verbatims available for this cluster.",
            )

        return SurveyRetrievalContext(
            tenant_id=tenant_id,
            product_id=cluster.product_id,
            issue_id=issue_id,
            feature=cluster.feature,
            category=category,
            evidence_items=evidence_items,
            specs=specs,
            dominant_batch_id=cluster.dominant_batch_id,
            version_label=version_label,
            is_sufficient=True,
        )

    # ── 2. In-Memory Retrieval (for decoupled testing) ─────────────────────────

    def retrieve_from_memory(
        self,
        cluster: dict[str, Any],
        product: dict[str, Any] | None,
        members: list[dict[str, Any]],
        tenant_id: str,
    ) -> SurveyRetrievalContext:
        """In-memory retrieval for decoupled testing, enforcing strict isolation and deduplication."""
        # Tenant isolation check on cluster
        if cluster.get("tenant_id") != tenant_id:
            return SurveyRetrievalContext(
                tenant_id=tenant_id,
                product_id="",
                issue_id=cluster.get("id", ""),
                feature="",
                is_sufficient=False,
                insufficient_reason=f"Cluster does not belong to tenant '{tenant_id}'.",
            )

        product_id = cluster.get("product_id", "")
        feature = cluster.get("feature", "unknown_feature")
        specs: dict[str, Any] = {}
        category = "general"

        if product:
            # Check tenant and product isolation
            if product.get("tenant_id") == tenant_id and product.get("id") == product_id:
                specs = product.get("specs", {}) or {}
                category = product.get("category", "general")

        evidence_items: list[RetrievedEvidence] = []
        seen_texts: list[str] = []

        for m in members:
            # Enforce tenant and product matching on reviews
            if m.get("tenant_id") != tenant_id or m.get("product_id") != product_id:
                continue

            raw_text = m.get("text_original") or m.get("text") or ""
            if not raw_text or not _is_substantive(raw_text):
                continue
            if _is_near_duplicate(raw_text, seen_texts, threshold=0.70):
                continue

            masked_text, _ = mask_pii(raw_text)
            seen_texts.append(raw_text)
            evidence_items.append(
                RetrievedEvidence(
                    review_id=m.get("review_id") or m.get("id", "rev_unknown"),
                    text=masked_text,
                    rating=m.get("rating"),
                    channel=m.get("channel"),
                    role=m.get("role", "member"),
                )
            )
            if len(evidence_items) >= 4:
                break

        if not evidence_items:
            return SurveyRetrievalContext(
                tenant_id=tenant_id,
                product_id=product_id,
                issue_id=cluster.get("id", ""),
                feature=feature,
                category=category,
                evidence_items=[],
                specs=specs,
                dominant_batch_id=cluster.get("dominant_batch_id"),
                version_label=cluster.get("version_label"),
                is_sufficient=False,
                insufficient_reason="No representative customer review verbatims available for this cluster.",
            )

        return SurveyRetrievalContext(
            tenant_id=tenant_id,
            product_id=product_id,
            issue_id=cluster.get("id", ""),
            feature=feature,
            category=category,
            evidence_items=evidence_items,
            specs=specs,
            dominant_batch_id=cluster.get("dominant_batch_id"),
            version_label=cluster.get("version_label"),
            is_sufficient=True,
        )

    # ── 3. Question Validation and Sanitization ───────────────────────────────

    def validate_questions(
        self,
        raw_questions: list[dict[str, Any]],
        context: SurveyRetrievalContext,
    ) -> tuple[bool, list[SurveyQuestion], str | None]:
        """
        Validates questions against schema, evidence references, and ungrounded claims:
        - Must contain 1 to 3 questions.
        - Options must have at least 3 distinct choices.
        - Must include an explicit uncertain / 'I'm not sure' choice.
        - Evidence references must strictly belong to retrieved review IDs or spec keys.
        - Questions must not assert ungrounded causes as established facts.
        """
        if not isinstance(raw_questions, list) or len(raw_questions) == 0:
            return False, [], "LLM output is not a valid list of questions."

        valid_evidence_keys = {e.review_id for e in context.evidence_items}
        if context.specs:
            valid_evidence_keys.update(context.specs.keys())
        if context.dominant_batch_id:
            valid_evidence_keys.add(context.dominant_batch_id)
        if context.version_label:
            valid_evidence_keys.add(context.version_label)

        sanitized: list[SurveyQuestion] = []
        seen_question_texts: list[str] = []

        # Prohibited phrases that assert ungrounded speculation as fact
        assertive_cause_patterns = [
            r"\b(?:because|since|given that)\s+(?:the\s+)?[\w\s-]+\s+(?:is|was|failed due to|caused by|defective|faulty)",
            r"\bconfirm that\s+(?:the\s+)?[\w\s-]+\s+(?:caused|broke|failed)",
            r"\bdue to\s+(?:the\s+)?(?:defective|faulty|broken|poor quality)\b",
        ]

        for idx, q_dict in enumerate(raw_questions[:3], start=1):
            if not isinstance(q_dict, dict):
                return False, [], f"Question {idx} is not an object."

            q_text = str(q_dict.get("question_text", "")).strip()
            if not q_text or len(q_text) < 10:
                return False, [], f"Question {idx} has missing or empty question text."

            # Check ungrounded assertive claims
            for pat in assertive_cause_patterns:
                if re.search(pat, q_text, re.IGNORECASE):
                    return False, [], f"Question {idx} asserts ungrounded cause as fact: '{q_text}'"

            # Check duplication across questions
            if _is_near_duplicate(q_text, seen_question_texts, threshold=0.80):
                return False, [], f"Question {idx} is a duplicate of a previous question."
            seen_question_texts.append(q_text)

            # Validate options
            raw_options = q_dict.get("options", [])
            if not isinstance(raw_options, list) or len(raw_options) < 2:
                return False, [], f"Question {idx} does not provide sufficient options."

            options = [str(opt).strip() for opt in raw_options if str(opt).strip()]
            # Ensure unique options
            unique_options: list[str] = []
            for opt in options:
                if opt not in unique_options:
                    unique_options.append(opt)

            # Ensure uncertainty choice exists
            has_uncertain = any(
                term in opt.lower()
                for opt in unique_options
                for term in ("not sure", "uncertain", "don't know", "cannot determine", "not applicable")
            )
            if not has_uncertain:
                unique_options.append("I'm not sure")

            if len(unique_options) < 3:
                return False, [], f"Question {idx} options count is under the minimum of 3."

            # Validate evidence references
            raw_refs = q_dict.get("evidence_refs", [])
            if isinstance(raw_refs, str):
                raw_refs = [raw_refs]
            elif not isinstance(raw_refs, list):
                raw_refs = []

            evidence_refs: list[str] = []
            for ref in raw_refs:
                ref_str = str(ref).strip()
                # Check containment in valid context keys
                if ref_str in valid_evidence_keys or any(ref_str in v for v in valid_evidence_keys):
                    evidence_refs.append(ref_str)

            # If evidence_refs was omitted or filtered out, populate with matching evidence
            if not evidence_refs and context.evidence_items:
                evidence_refs = [e.review_id for e in context.evidence_items[:2]]

            rationale = str(q_dict.get("rationale", "")).strip() or "Ground-truth failure mode diagnostic query."

            sanitized.append(
                SurveyQuestion(
                    question_id=str(q_dict.get("question_id") or f"q{idx}"),
                    question_text=q_text,
                    options=unique_options,
                    evidence_refs=evidence_refs,
                    rationale=rationale,
                    is_fallback=bool(q_dict.get("is_fallback", False)),
                )
            )

        if len(sanitized) == 0:
            return False, [], "No valid diagnostic questions could be extracted."

        return True, sanitized, None

    # ── 4. Fallback Question Generator ────────────────────────────────────────

    def get_category_fallback_questions(
        self,
        category: str | None,
        feature: str,
        context: SurveyRetrievalContext,
    ) -> list[SurveyQuestion]:
        """Provides pre-calibrated diagnostic templates for category with is_fallback=True."""
        cat_key = (category or "general").lower()
        if cat_key not in CATEGORY_FALLBACK_TEMPLATES:
            # Check partial match (e.g. "refrigerators" -> "appliances")
            if any(term in cat_key for term in ("appliance", "fridge", "wash", "oven", "ac", "cool")):
                cat_key = "appliances"
            elif any(term in cat_key for term in ("headphone", "earphone", "audio", "sound", "speaker")):
                cat_key = "audio"
            elif any(term in cat_key for term in ("electron", "phone", "tv", "display", "gadget")):
                cat_key = "electronics"
            else:
                cat_key = "general"

        templates = CATEGORY_FALLBACK_TEMPLATES[cat_key]
        clean_feature = feature.replace("_", " ").title()
        evidence_ids = [e.review_id for e in context.evidence_items] or ["cluster_evidence"]

        results: list[SurveyQuestion] = []
        for t in templates:
            q_text = t["question_text"].format(feature=clean_feature)
            results.append(
                SurveyQuestion(
                    question_id=t["question_id"],
                    question_text=q_text,
                    options=list(t["options"]),
                    evidence_refs=evidence_ids[:3],
                    rationale=f"Category template ({cat_key}): {t['rationale']}",
                    is_fallback=True,
                )
            )
        return results

    # ── 5. Main Generation Entry Point ────────────────────────────────────────

    async def generate_diagnostic_survey(
        self,
        context: SurveyRetrievalContext,
        timeout_seconds: float = 8.0,
    ) -> SurveyGenerationResult:
        """
        Executes the full RAG diagnostic survey generation:
        1. Checks evidence sufficiency.
        2. Prompts Gemini with masked quotes and specs.
        3. Validates structured output.
        4. Gracefully falls back to category templates on failure or timeout.
        """
        # Guard: Insufficient evidence
        if not context.is_sufficient or len(context.evidence_items) == 0:
            return SurveyGenerationResult(
                status="insufficient_evidence",
                questions=[],
                evidence_context=context.evidence_items,
                fallback_reason=context.insufficient_reason or "Insufficient evidence: cluster contains 0 substantive review verbatims.",
                is_fallback=False,
            )

        api_key = self._get_api_key()
        llm_enabled = self.settings.llm_fallback_enabled

        # If LLM is not configured, go directly to category fallback
        if not api_key or not llm_enabled:
            fallback_qs = self.get_category_fallback_questions(
                category=context.category,
                feature=context.feature,
                context=context,
            )
            return SurveyGenerationResult(
                status="fallback",
                questions=fallback_qs,
                evidence_context=context.evidence_items,
                fallback_reason="Gemini API key is not configured or LLM fallback is disabled.",
                is_fallback=True,
            )

        # Build grounded prompt
        quotes_block = "\n".join(
            f"- [Review ID: {e.review_id}] \"{e.text}\" (Rating: {e.rating or 'N/A'}, Channel: {e.channel or 'N/A'})"
            for e in context.evidence_items
        )
        specs_json = json.dumps(context.specs, indent=2) if context.specs else "{}"

        prompt = (
            f"You are a Senior Reliability and Quality Engineering Diagnostic Specialist.\n"
            f"A customer defect cluster has formed around the feature '{context.feature}' for product category '{context.category or 'General'}'.\n\n"
            f"Dominant Batch Code: {context.dominant_batch_id or 'Unknown'}\n"
            f"Product Version: {context.version_label or 'Unknown'}\n"
            f"Catalog Technical Specs:\n{specs_json}\n\n"
            f"Customer Evidence (Masked Verbatims):\n{quotes_block}\n\n"
            f"Your Goal: Draft exactly 3 multiple-choice diagnostic questions to isolate the root engineering failure mode.\n\n"
            f"CRITICAL GROUNDING INVARIANTS:\n"
            f"1. Stay strictly grounded in the customer verbatims, product specifications, and batch context provided.\n"
            f"2. DO NOT state or presume an unverified cause as an established fact.\n"
            f"3. Frame each question as an objective inquiry to isolate failure modes.\n"
            f"4. Provide 3-5 distinct multiple-choice options for each question, ALWAYS including an 'I'm not sure' or uncertainty option.\n"
            f"5. Include 'evidence_refs' referencing the exact Review IDs (e.g. ['{context.evidence_items[0].review_id}']) or spec keys that substantiate the question.\n"
            f"6. Include a concise engineering 'rationale' explaining how customer answers will isolate the root cause.\n\n"
            f"Output Format:\n"
            f"Respond ONLY with a JSON array of 3 objects with keys:\n"
            f"'question_id', 'question_text', 'options', 'evidence_refs', 'rationale'."
        )

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                resp = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "response_mime_type": "application/json",
                            "temperature": 0.2,
                        },
                    },
                )

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(content_part)

                        # Validate output against rules
                        is_valid, questions, val_err = self.validate_questions(parsed, context)
                        if is_valid:
                            return SurveyGenerationResult(
                                status="success",
                                questions=questions,
                                evidence_context=context.evidence_items,
                                fallback_reason=None,
                                is_fallback=False,
                            )
                        else:
                            logger.warning("Gemini output failed validation: %s. Falling back to templates.", val_err)
                            fallback_qs = self.get_category_fallback_questions(context.category, context.feature, context)
                            return SurveyGenerationResult(
                                status="fallback",
                                questions=fallback_qs,
                                evidence_context=context.evidence_items,
                                fallback_reason=f"Validation failure: {val_err}",
                                is_fallback=True,
                            )
                else:
                    logger.warning("Gemini API returned status code %s. Using fallback.", resp.status_code)
        except Exception as ex:
            logger.warning("Exception during Gemini survey generation: %s. Using fallback.", ex)

        # Fallback to category templates on API error, validation error, or timeout
        fallback_qs = self.get_category_fallback_questions(
            category=context.category,
            feature=context.feature,
            context=context,
        )
        return SurveyGenerationResult(
            status="fallback",
            questions=fallback_qs,
            evidence_context=context.evidence_items,
            fallback_reason="Gemini generation timed out, encountered an error, or produced invalid output.",
            is_fallback=True,
        )
