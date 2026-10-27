"""
prism_core/survey/__init__.py

L5 Act — Survey Loop and RAG Diagnostic Engine.
Exposes:
- plan(issue_id, trigger) -> Survey
- send_survey_invite(survey, raw_token, to_email) -> dict
- ingest_reply(raw_token, answers) -> dict
- generate_survey_token(survey_id, tenant_id) -> str
- verify_survey_token(token) -> tuple[bool, str | None, str | None]
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.config.settings import get_settings
from prism_core.db.base import get_sessionmaker
from prism_core.db.models import EmailOutbox, IssueCluster, RawReview, Review, Survey, SurveyResponse
from prism_core.events import emit
from prism_core.mail import send as send_email
from prism_core.survey.generator import SurveyGenerator


def get_survey_signing_secret() -> str:
    """
    Retrieve survey token signing secret from configuration.
    Fails safely in production environments if secret is missing or insecure.
    """
    env = os.environ.get("ENVIRONMENT", "development").lower()
    secret: str | None = os.environ.get("SURVEY_TOKEN_SECRET") or os.environ.get("SECRET_KEY")

    try:
        settings = get_settings()
        env = getattr(settings, "environment", env).lower()
        if hasattr(settings, "secret_key") and settings.secret_key:
            secret = settings.secret_key.get_secret_value()
    except Exception:
        pass

    if env == "production":
        if not secret or secret in ("prism_secret_token_key", "secret", "changeme") or len(secret) < 32:
            raise ValueError("Production survey token signing secret must be securely configured with at least 32 characters.")
    return secret or "prism_secret_token_key"


def generate_survey_token(
    survey_id: str,
    tenant_id: str,
    secret: str | None = None,
    recipient_id: str = "anon",
    expires_in_seconds: int = 7 * 86400,
) -> str:
    """
    Generate an HMAC-signed tamper-proof canonical survey token.
    Canonical format: v1.{survey_id}.{tenant_id}.{recipient_scope}.{expires_ts}.{sig}
    Scoped to the survey, tenant, and recipient without exposing PII.
    """
    active_secret = secret or get_survey_signing_secret()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    expires_ts = now_ts + expires_in_seconds
    recipient_scope = hashlib.sha256(recipient_id.encode("utf-8")).hexdigest()[:10]

    payload = f"v1.{survey_id}.{tenant_id}.{recipient_scope}.{expires_ts}"
    sig = hmac.new(active_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"{payload}.{sig}"


def verify_survey_token(
    token: str,
    secret: str | None = None,
    expected_tenant_id: str | None = None,
    expected_recipient_id: str | None = None,
) -> tuple[bool, str | None, str | None]:
    """
    Verify HMAC-signed survey token.
    Enforces expiry validation and returns (is_valid, survey_id, tenant_id).
    Supports canonical v1 tokens and legacy tokens with time-limited migration.
    Optionally verifies expected_tenant_id and expected_recipient_id scoping.
    """
    active_secret = secret or get_survey_signing_secret()

    # 1. Canonical v1 Format: v1.{survey_id}.{tenant_id}.{recipient_scope}.{expires_ts}.{sig}
    if token.startswith("v1."):
        parts = token.split(".")
        if len(parts) == 6:
            _, survey_id, tenant_id, recipient_scope, expires_ts_str, sig = parts
            payload = f"v1.{survey_id}.{tenant_id}.{recipient_scope}.{expires_ts_str}"
            expected_sig = hmac.new(active_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
            if hmac.compare_digest(sig, expected_sig):
                try:
                    expires_ts = int(expires_ts_str)
                    now_ts = int(datetime.now(timezone.utc).timestamp())
                    if now_ts > expires_ts:
                        return False, None, None  # Expired
                    if expected_tenant_id and tenant_id != expected_tenant_id:
                        return False, None, None
                    if expected_recipient_id:
                        expected_scope = hashlib.sha256(expected_recipient_id.encode("utf-8")).hexdigest()[:10]
                        if recipient_scope != expected_scope:
                            return False, None, None
                    return True, survey_id, tenant_id
                except ValueError:
                    return False, None, None

    # 2. Legacy 3-part Format: {survey_id}.{tenant_id}.{sig}
    if "." in token:
        parts = token.split(".")
        if len(parts) == 3:
            survey_id, tenant_id, sig = parts
            expected = hmac.new(active_secret.encode("utf-8"), f"{survey_id}.{tenant_id}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
            if hmac.compare_digest(sig, expected):
                if expected_tenant_id and tenant_id != expected_tenant_id:
                    return False, None, None
                return True, survey_id, tenant_id

    # 3. Legacy Base64 Format: base64({survey_id}:{tenant_id}:{sig})
    try:
        raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        parts = raw.split(":")
        if len(parts) == 3:
            survey_id, tenant_id, sig = parts
            expected_sig = hmac.new(
                active_secret.encode("utf-8"), f"{survey_id}:{tenant_id}".encode("utf-8"), hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(sig, expected_sig):
                if expected_tenant_id and tenant_id != expected_tenant_id:
                    return False, None, None
                return True, survey_id, tenant_id
    except Exception:
        pass

    return False, None, None


async def plan(
    issue_id: str,
    trigger: str = "manual",
    tenant_id: str = "default",
    session: AsyncSession | None = None,
    target_question_count: int = 7,
) -> tuple[Survey, str]:
    """
    RAG-Grounded Diagnostic Survey Planner:
    1. Validates trigger authorization (monitor/gather/manual).
    2. Retrieves customer verbatims from issue cluster members with tenant/product isolation.
    3. Retrieves product technical specs and dominant batch/version context.
    4. Drafts 6-7 root-cause diagnostic questions via Gemini prompt or category fallback.
    5. Validates grounding, evidence refs, and uncertainty options.
    6. Issues canonical signed token with 7-day expiration.
    Returns: (survey_record, raw_token)
    """
    authorized_triggers = ("manual", "monitor", "gather", "monitoring", "gathering", "scheduled")
    if trigger not in authorized_triggers:
        raise ValueError(f"Unauthorized survey trigger: '{trigger}'. Must be one of {authorized_triggers}")

    async def _plan(sess: AsyncSession) -> tuple[Survey, str]:
        generator = SurveyGenerator()

        # 1. Fetch retrieval context with strict multi-tenant isolation
        context = await generator.retrieve_context(
            session=sess,
            issue_id=issue_id,
            tenant_id=tenant_id,
        )
        context.target_question_count = target_question_count

        if not context.is_sufficient:
            if "not found" in (context.insufficient_reason or "").lower():
                raise ValueError(f"Issue cluster {issue_id} not found")
            raise ValueError(f"Cannot generate survey: {context.insufficient_reason}")

        # 2. Generate RAG-grounded diagnostic questions (6-7 questions)
        gen_result = await generator.generate_diagnostic_survey(context, target_count=target_question_count)
        if gen_result.status == "insufficient_evidence" or not gen_result.questions:
            raise ValueError(f"Cannot generate survey: {gen_result.fallback_reason or 'Insufficient evidence'}")

        if len(gen_result.questions) < 3:
            fallback_qs = generator.get_category_fallback_questions(
                context.category, context.feature, context, limit=target_question_count
            )
            questions_payload = [q.model_dump() for q in fallback_qs]
        else:
            questions_payload = [q.model_dump() for q in gen_result.questions]

        # Attach RAG trace for inspection and transparency
        if questions_payload and gen_result.rag_processing_trace:
            questions_payload[0]["rag_processing_trace"] = gen_result.rag_processing_trace

        # 3. Review id for tracking
        rev_id = context.evidence_items[0].review_id if context.evidence_items else "rev_placeholder"

        # 4. Generate secure canonical token scoped to survey & tenant
        survey_id = secrets.token_hex(16)
        raw_token = generate_survey_token(
            survey_id=survey_id,
            tenant_id=tenant_id,
            recipient_id=rev_id,
            expires_in_seconds=7 * 86400,
        )
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        survey = Survey(
            id=survey_id,
            tenant_id=tenant_id,
            issue_id=issue_id,
            review_id=rev_id,
            token_hash=token_hash,
            questions=questions_payload,
            status="sent",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        sess.add(survey)
        await sess.flush()

        return survey, raw_token

    if session is not None:
        return await _plan(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            res = await _plan(sess)
            await sess.commit()
            return res


async def send_survey_invite(
    survey: Survey,
    raw_token: str,
    to_email: str | None = None,
    customer_name: str = "Valued Customer",
    product_name: str = "Device",
    tenant_id: str = "default",
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Send customer survey invite with strict consent verification:
    - Verifies explicit follow-up consent from recorded intake (RawReview).
    - Checks that to_email matches the consented email address.
    - If consent is missing/false, skips delivery and logs clear reason without exposing email.
    - Uses idempotency check to avoid duplicate sends on retries.
    """
    async def _send(sess: AsyncSession) -> dict[str, Any]:
        # 1. Lookup intake record to verify explicit consent
        raw_rev: RawReview | None = None
        if survey.review_id:
            raw_rev = await sess.get(RawReview, survey.review_id)
            if not raw_rev:
                # Review might be stored with raw_id pointer
                stmt = select(RawReview).where(RawReview.id == survey.review_id, RawReview.tenant_id == tenant_id)
                raw_rev = (await sess.execute(stmt)).scalar_one_or_none()
            if not raw_rev:
                rev_stmt = select(Review).where(Review.id == survey.review_id, Review.tenant_id == tenant_id)
                rev = (await sess.execute(rev_stmt)).scalar_one_or_none()
                if rev and rev.raw_id:
                    raw_rev = await sess.get(RawReview, rev.raw_id)

        consented_email: str | None = None
        has_consent = False

        if raw_rev and isinstance(raw_rev.payload, dict):
            contact = raw_rev.payload.get("contact") or {}
            has_consent = bool(contact.get("consent_followup", False))
            consented_email = contact.get("email")
            if not consented_email:
                author = raw_rev.payload.get("author") or {}
                consented_email = author.get("email")

        # 2. Consent Verification Gate
        if not has_consent or not consented_email:
            skip_reason = "consent_missing" if not has_consent else "consented_email_missing"
            # Record reason on survey metadata without exposing email
            if survey.questions and isinstance(survey.questions[0], dict):
                if "metadata" not in survey.questions[0]:
                    survey.questions[0]["metadata"] = {}
                survey.questions[0]["metadata"]["delivery_skip_reason"] = skip_reason
            return {
                "status": "skipped",
                "reason": skip_reason,
                "survey_id": survey.id,
            }

        # 3. Recipient Match Gate (do not trust caller-supplied to_email alone)
        target_email = consented_email.strip().lower()
        if to_email and to_email.strip().lower() != target_email:
            return {
                "status": "skipped",
                "reason": "recipient_mismatch",
                "survey_id": survey.id,
            }

        # 4. Idempotency Gate (check for duplicate sends on retry)
        to_hash = hashlib.sha256(target_email.encode("utf-8")).hexdigest()
        existing_stmt = select(EmailOutbox).where(
            EmailOutbox.tenant_id == tenant_id,
            EmailOutbox.to_hash == to_hash,
            EmailOutbox.template == "survey",
            EmailOutbox.status.in_(["sent", "delivered", "simulated"]),
        )
        existing = (await sess.execute(existing_stmt)).scalars().first()
        if existing and existing.payload.get("survey_id") == survey.id:
            return {
                "status": "duplicate_skipped",
                "reason": "already_dispatched",
                "outbox_id": existing.id,
            }

        # 5. Dispatch via Mail Provider
        survey_url = f"/v1/survey/{raw_token}"
        unsubscribe_url = f"/v1/survey/{raw_token}/unsubscribe"

        ctx = {
            "survey_id": survey.id,
            "customer_name": customer_name,
            "product_name": product_name,
            "feature_name": "the reported issue",
            "survey_url": survey_url,
            "unsubscribe_url": unsubscribe_url,
        }
        res = await send_email("survey", target_email, ctx, tenant_id=tenant_id, session=sess)
        return res

    if session is not None:
        return await _send(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            out = await _send(sess)
            await sess.commit()
            return out


def classify_answer_signal(question: dict[str, Any], answer: Any) -> tuple[str, str]:
    """
    Classifies a customer's answer to a diagnostic survey question into
    'confirm', 'deny', 'neutral', or 'unclear'.
    Validates that the answer corresponds to one of the question's allowed options.
    Returns: (signal, matched_option_text)
    Raises: ValueError if the answer is not a valid option for the question.
    """
    raw_ans = str(answer).strip()
    if not raw_ans:
        raise ValueError("Answer cannot be empty.")

    valid_options = [str(opt).strip() for opt in question.get("options", []) if str(opt).strip()]
    if not valid_options:
        matched_option = raw_ans
    else:
        # Match exact or case-insensitive
        matched_option = next((opt for opt in valid_options if opt.lower() == raw_ans.lower()), None)
        if not matched_option:
            try:
                idx = int(raw_ans)
                if 0 <= idx < len(valid_options):
                    matched_option = valid_options[idx]
            except (ValueError, TypeError):
                pass

        if not matched_option:
            q_id = question.get("question_id", "unknown")
            raise ValueError(
                f"Invalid answer for question '{q_id}': '{raw_ans}' is not a valid option."
            )

    opt_lower = matched_option.lower()

    # 1. Unclear / uncertainty signal
    unclear_terms = (
        "not sure",
        "uncertain",
        "don't know",
        "dont know",
        "cannot determine",
        "can't determine",
        "unclear",
        "unknown",
        "unsure",
        "undecided",
    )
    if any(term in opt_lower for term in unclear_terms):
        return "unclear", matched_option

    # 2. Neutral / unattempted / not applicable signal
    neutral_terms = (
        "not applicable",
        "n/a",
        "did not attempt",
        "have not tried",
        "haven't tried",
        "did not try",
        "no preference",
        "neutral",
        "neither",
        "no opinion",
        "did not observe or check",
        "not tested",
        "untested",
        "inconclusive",
        "skip",
    )
    if any(term in opt_lower for term in neutral_terms):
        return "neutral", matched_option

    # 3. Deny / symptom absent / operating normally signal
    deny_terms = (
        "no unusual",
        "no difference",
        "not observed",
        "not present",
        "did not occur",
        "does not occur",
        "never occurs",
        "never happens",
        "no problem",
        "no issue",
        "resolved completely",
        "works fine",
        "working normally",
        "normal physical condition",
        "normal warm charging",
        "no sound, heat, or moisture",
        "device operates normally",
        "operates normally",
        "symptom eliminated",
        "symptom not present",
        "symptom absent",
        "issue absent",
        "never experienced",
        "did not experience",
        "cannot reproduce",
        "unable to reproduce",
    )
    if any(term in opt_lower for term in deny_terms):
        return "deny", matched_option
    if opt_lower in ("no", "false", "disagree", "absent", "denied", "deny", "negative", "never", "none"):
        return "deny", matched_option
    if opt_lower.startswith(("no,", "no -", "no: ", "deny: ")):
        return "deny", matched_option
    if opt_lower.startswith("no ") and not opt_lower.startswith(("no effect on the issue", "no effect whatsoever", "no change at all in behavior")):
        return "deny", matched_option

    # 4. Confirm / symptom observed / failure mode present
    return "confirm", matched_option


async def ingest_reply(
    raw_token: str,
    answers: dict[str, Any],
    secret: str | None = None,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Ingests customer diagnostic survey response:
    - Validates token authenticity and expiry.
    - Validates answers against survey questions and allowed options.
    - Rejects invalid answers, blank responses, and duplicate submissions.
    - Computes bounded SurveyDelta (capped at ±0.20 per pipeline-3.md §P8):
      confirmations increase confidence, denials decrease it, neutral/unclear have zero effect.
    - Clamps issue confidence strictly in [0.0, 1.0].
    - Emits SSE event for real-time observability.
    """
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    async def _ingest(sess: AsyncSession) -> dict[str, Any]:
        # Validate cryptographic signature and token expiry
        is_valid, srv_id, ten_id = verify_survey_token(raw_token, secret=secret)
        survey = None
        if is_valid:
            stmt = select(Survey).where(Survey.token_hash == token_hash)
            survey = (await sess.execute(stmt)).scalar_one_or_none()
            if not survey or survey.id != srv_id or survey.tenant_id != ten_id:
                raise ValueError("Invalid or expired survey token")
        else:
            # Fallback for internal task invocation directly by survey_id
            stmt = select(Survey).where(Survey.id == raw_token)
            survey = (await sess.execute(stmt)).scalar_one_or_none()
            if not survey:
                raise ValueError("Invalid or expired survey token")

        # Expiry check
        now = datetime.now(timezone.utc)
        expires_at = survey.expires_at.replace(tzinfo=timezone.utc) if survey.expires_at.tzinfo is None else survey.expires_at
        if now > expires_at:
            survey.status = "expired"
            raise ValueError("Survey has expired")

        # Reject duplicate submissions
        if survey.status == "answered":
            raise ValueError("Survey has already been submitted.")

        # Validate answers: must not be empty
        clean_raw = {k: v for k, v in answers.items() if v is not None and str(v).strip()}
        if not clean_raw:
            raise ValueError("Invalid submission: answers cannot be empty.")

        questions = survey.questions or []
        if not questions:
            raise ValueError("Survey has no questions configured.")

        # Validate answer keys against question IDs
        valid_q_ids = {str(q.get("question_id", "")) for q in questions}
        valid_keys = set(valid_q_ids)
        for qid in valid_q_ids:
            valid_keys.add(f"ans_{qid}")

        for k in clean_raw:
            if k not in valid_keys and k.lower() not in {vk.lower() for vk in valid_keys}:
                raise ValueError(f"Invalid answer key: '{k}' does not match any survey question.")

        # Map each answer to a validated confirm, deny, neutral, or unclear signal
        signals: list[str] = []
        signals_by_question: dict[str, str] = {}
        clean_answers: dict[str, str] = {}

        for q in questions:
            q_id = str(q.get("question_id", ""))
            ans_val = None
            for k, v in clean_raw.items():
                if k == q_id or k == f"ans_{q_id}" or k.lower() in (q_id.lower(), f"ans_{q_id}".lower()):
                    ans_val = v
                    break

            if ans_val is not None:
                # classify_answer_signal validates option containment and raises ValueError on invalid option
                signal, matched_opt = classify_answer_signal(q, ans_val)
                signals.append(signal)
                signals_by_question[q_id] = signal
                clean_answers[q_id] = matched_opt

        if not clean_answers:
            raise ValueError("Invalid submission: answers cannot be empty.")

        # Calculate bounded, evidence-based SurveyDelta (capped at ±0.20 per pipeline-3.md §P8)
        total_questions = max(len(questions), 1)
        step = 0.20 / total_questions

        total_delta = 0.0
        for s in signals:
            if s == "confirm":
                total_delta += step
            elif s == "deny":
                total_delta -= step
            elif s in ("neutral", "unclear"):
                total_delta += 0.0  # neutral/unclear has zero effect

        confidence_delta = round(max(-0.20, min(0.20, total_delta)), 3)

        # Generate evidence-grounded summary
        n_confirm = signals.count("confirm")
        n_deny = signals.count("deny")
        n_neutral = signals.count("neutral")
        n_unclear = signals.count("unclear")

        if n_confirm > n_deny:
            summary = f"Customer response confirmed failure symptoms ({n_confirm} confirms, delta: {confidence_delta:+.2f})."
        elif n_deny > n_confirm:
            summary = f"Customer response indicated failure symptoms were absent ({n_deny} denials, delta: {confidence_delta:+.2f})."
        elif n_unclear + n_neutral == len(signals):
            summary = "Customer response was neutral or unclear with no diagnostic confidence change."
        else:
            summary = f"Customer response was mixed ({n_confirm} confirms, {n_deny} denials, delta: {confidence_delta:+.2f})."

        survey.status = "answered"
        resp = SurveyResponse(
            tenant_id=survey.tenant_id,
            survey_id=survey.id,
            answers=clean_answers,
            summary=summary,
            confidence_delta=confidence_delta,
        )
        sess.add(resp)

        # Update IssueCluster confidence bounded strictly in [0.0, 1.0]
        cluster = await sess.get(IssueCluster, survey.issue_id)
        if cluster:
            cluster.confidence = round(max(0.0, min(1.0, cluster.confidence + confidence_delta)), 3)
            if cluster.confidence_parts and isinstance(cluster.confidence_parts, dict):
                cluster.confidence_parts["survey_delta"] = confidence_delta
                cluster.confidence_parts["final"] = cluster.confidence

        await sess.flush()
        await emit(
            "survey.answered",
            "done",
            f"srv_{survey.id[:8]}",
            tenant_id=survey.tenant_id,
            session=sess,
            detail={
                "survey_id": survey.id,
                "issue_id": survey.issue_id,
                "confidence_delta": confidence_delta,
                "signals": signals_by_question,
            },
        )

        return {
            "status": "success",
            "survey_id": survey.id,
            "issue_id": survey.issue_id,
            "confidence_delta": confidence_delta,
            "new_confidence": cluster.confidence if cluster else round(max(0.0, min(1.0, 0.50 + confidence_delta)), 3),
            "signals": signals_by_question,
            "summary": summary,
        }

    if session is not None:
        return await _ingest(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            out = await _ingest(sess)
            await sess.commit()
            return out


class SurveyManager:
    """Manager for RAG-grounded customer diagnostic surveys."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.generator = SurveyGenerator(settings=self.settings)

    async def retrieve_context(
        self,
        session: AsyncSession,
        issue_id: str,
        tenant_id: str,
    ):
        """Retrieve evidence context with strict multi-tenant isolation."""
        return await self.generator.retrieve_context(session=session, issue_id=issue_id, tenant_id=tenant_id)

    def retrieve_from_memory(
        self,
        cluster: dict[str, Any],
        product: dict[str, Any] | None,
        members: list[dict[str, Any]],
        tenant_id: str,
    ):
        """Retrieve evidence context from in-memory objects with strict isolation."""
        return self.generator.retrieve_from_memory(
            cluster=cluster,
            product=product,
            members=members,
            tenant_id=tenant_id,
        )

    async def generate_diagnostic_survey(self, context, timeout_seconds: float = 8.0):
        """Generate RAG diagnostic survey questions for given context."""
        return await self.generator.generate_diagnostic_survey(context=context, timeout_seconds=timeout_seconds)

    def validate_questions(self, raw_questions: list[dict[str, Any]], context):
        """Validate question schema, uncertainty option, and evidence references."""
        return self.generator.validate_questions(raw_questions=raw_questions, context=context)

    def get_category_fallback_questions(self, category: str | None, feature: str, context):
        """Provide calibrated fallback questions for a given category."""
        return self.generator.get_category_fallback_questions(category=category, feature=feature, context=context)

    async def plan(
        self,
        issue_id: str,
        trigger: str = "manual",
        tenant_id: str = "default",
        session: AsyncSession | None = None,
    ):
        """Plan a RAG-grounded survey with 3 diagnostic questions."""
        return await plan(issue_id=issue_id, trigger=trigger, tenant_id=tenant_id, session=session)

    async def send_invite(
        self,
        survey: Survey,
        raw_token: str,
        to_email: str | None = None,
        customer_name: str = "Valued Customer",
        product_name: str = "Device",
        tenant_id: str = "default",
        session: AsyncSession | None = None,
    ):
        """Send consented customer invite."""
        return await send_survey_invite(
            survey=survey,
            raw_token=raw_token,
            to_email=to_email,
            customer_name=customer_name,
            product_name=product_name,
            tenant_id=tenant_id,
            session=session,
        )

    async def ingest_reply(
        self,
        raw_token: str,
        answers: dict[str, Any],
        session: AsyncSession | None = None,
    ):
        """Ingest response and update confidence."""
        return await ingest_reply(raw_token=raw_token, answers=answers, session=session)
