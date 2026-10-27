"""
workflows/tasks/survey_loop.py

Render Workflows Task: survey_loop(survey_id: str)
Long-running, resume-safe task:
Monitors customer diagnostic survey responses up to 7 days.
Dispatches a gentle reminder at Day 3 if still unanswered, and expires token at Day 7.
Emits real-time SSE events so judges and dashboard users can observe the loop live.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.base import get_sessionmaker
from prism_core.db.models import IssueCluster, Product, RawReview, Survey
from prism_core.events import emit
from prism_core.mail import send as send_mail


async def execute_survey_loop(survey_id: str, session: AsyncSession | None = None) -> dict[str, str]:
    """
    Executes the survey monitoring step:
    - Checks whether survey has expired (> 7 days).
    - Checks whether Day 3 reminder should be sent.
    - Emits SSE events for real-time observability.
    """
    async def _run(sess: AsyncSession) -> dict[str, str]:
        survey = await sess.get(Survey, survey_id)
        if not survey:
            return {"status": "not_found", "survey_id": survey_id}

        now = datetime.now(timezone.utc)
        expires_at = survey.expires_at.replace(tzinfo=timezone.utc) if survey.expires_at.tzinfo is None else survey.expires_at
        created_at = survey.created_at.replace(tzinfo=timezone.utc) if survey.created_at.tzinfo is None else survey.created_at

        # 1. Check expiration (Day 7)
        if survey.status in ("sent", "opened") and now > expires_at:
            survey.status = "expired"
            await sess.flush()
            await emit(
                "survey.loop",
                "done",
                f"survey_{survey_id[:8]}",
                tenant_id=survey.tenant_id,
                session=sess,
                detail={"action": "expired", "survey_id": survey.id, "issue_id": survey.issue_id},
            )
            return {"status": "expired", "survey_id": survey_id}

        # 2. Check 3-day reminder for unanswered surveys
        if survey.status == "sent":
            metadata = survey.questions[0].get("metadata", {}) if (survey.questions and isinstance(survey.questions[0], dict)) else {}
            reminder_sent = metadata.get("reminder_sent", False)

            if not reminder_sent and (now - created_at) >= timedelta(days=3):
                # Retrieve product name and customer email with explicit consent
                cluster = await sess.get(IssueCluster, survey.issue_id)
                prod = await sess.get(Product, cluster.product_id) if cluster else None
                prod_name = prod.name if prod else "Device"
                feature_name = cluster.feature if cluster else "reported issue"

                # Lookup customer contact from review payload
                raw_rev = await sess.get(RawReview, survey.review_id)
                if not raw_rev:
                    rev = await sess.get(Review, survey.review_id)
                    if rev and rev.raw_id:
                        raw_rev = await sess.get(RawReview, rev.raw_id)

                has_consent = False
                consented_email: str | None = None
                cust_name = "Valued Customer"

                if raw_rev and isinstance(raw_rev.payload, dict):
                    contact = raw_rev.payload.get("contact") or {}
                    has_consent = bool(contact.get("consent_followup", False))
                    consented_email = contact.get("email")
                    author = raw_rev.payload.get("author") or {}
                    if not consented_email:
                        consented_email = author.get("email")
                    cust_name = author.get("display_name") or "Valued Customer"

                # Enforce explicit consent gate
                if not has_consent or not consented_email:
                    if survey.questions and isinstance(survey.questions[0], dict):
                        if "metadata" not in survey.questions[0]:
                            survey.questions[0]["metadata"] = {}
                        survey.questions[0]["metadata"]["reminder_skip_reason"] = "consent_missing"
                    return {"status": "skipped", "reason": "consent_missing", "survey_id": survey_id}

                target_email = consented_email.strip().lower()

                # Dispatch gentle reminder
                await send_mail(
                    template_name="reminder",
                    to_email=target_email,
                    ctx={
                        "survey_id": survey.id,
                        "customer_name": cust_name,
                        "product_name": prod_name,
                        "feature_name": feature_name,
                        "survey_url": f"/v1/survey/{survey.token_hash[:16]}",
                        "unsubscribe_url": f"/v1/survey/{survey.token_hash[:16]}/unsubscribe",
                    },
                    tenant_id=survey.tenant_id,
                    session=sess,
                )

                # Flag reminder as sent in metadata
                if survey.questions and isinstance(survey.questions[0], dict):
                    if "metadata" not in survey.questions[0]:
                        survey.questions[0]["metadata"] = {}
                    survey.questions[0]["metadata"]["reminder_sent"] = True
                    survey.questions[0]["metadata"]["reminder_at"] = now.isoformat()

                await sess.flush()
                import hashlib
                to_hash = hashlib.sha256(target_email.encode()).hexdigest()[:10]
                await emit(
                    "survey.loop",
                    "done",
                    f"survey_{survey_id[:8]}",
                    tenant_id=survey.tenant_id,
                    session=sess,
                    detail={"action": "reminder_sent", "survey_id": survey.id, "recipient_scope": to_hash},
                )
                return {"status": "reminder_sent", "survey_id": survey_id}

        return {"status": survey.status, "survey_id": survey_id}

    if session is not None:
        return await _run(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            res = await _run(sess)
            await sess.commit()
            return res
