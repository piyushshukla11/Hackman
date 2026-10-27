"""
api/routers/actions.py

FastAPI Action Router:
- POST /v1/investigations/{issue_id}/survey (Trigger RAG diagnostic survey)
- GET /v1/survey/{token} (Serve public diagnostic survey page - Jinja2, mobile-first)
- POST /v1/survey/{token} (Submit answers, update confidence delta)
- POST /v1/email/survey, /v1/email/digest
- POST /v1/reports, GET /v1/reports/{id}/download
"""
from __future__ import annotations

import hashlib
from typing import Annotated, Any
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from prism_core.config.settings import get_settings
from prism_core.db.models import Survey, User
from prism_core.mail import send as send_mail
from prism_core.survey import ingest_reply, plan, send_survey_invite, verify_survey_token

router = APIRouter(prefix="/v1", tags=["Actions"])


class SurveyTriggerPayload(BaseModel):
    to_email: EmailStr
    customer_name: str = "Valued Customer"


class SurveySubmitPayload(BaseModel):
    answers: dict[str, Any]


SURVEY_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PRISM Engineering Diagnostic Survey</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #f8fafc; margin: 0; padding: 24px 16px; display: flex; justify-content: center; }
    .container { max-width: 620px; width: 100%; background: #131927; border-radius: 14px; padding: 32px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); border: 1px solid #1e293b; }
    .rag-status { display: inline-flex; align-items: center; gap: 8px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; color: #38bdf8; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.25); padding: 5px 12px; border-radius: 20px; margin-bottom: 16px; }
    .pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: #38bdf8; box-shadow: 0 0 8px #38bdf8; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
    h2 { color: #ffffff; margin-top: 0; font-size: 22px; font-weight: 700; }
    p.subtitle { color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }
    .question { margin: 20px 0; background: #0b0f19; padding: 20px; border-radius: 10px; border: 1px solid #1e293b; transition: border-color 0.2s; }
    .question:hover { border-color: #334155; }
    .question-title { font-weight: 600; color: #f1f5f9; margin-bottom: 14px; font-size: 15px; line-height: 1.4; }
    label { display: flex; align-items: flex-start; margin: 10px 0; cursor: pointer; color: #cbd5e1; font-size: 14px; line-height: 1.4; padding: 6px 10px; border-radius: 6px; transition: background 0.15s; }
    label:hover { background: rgba(255,255,255,0.03); color: #ffffff; }
    input[type="radio"] { margin-right: 12px; margin-top: 3px; accent-color: #38bdf8; }
    .rag-citation { margin-top: 14px; padding-top: 10px; border-top: 1px dashed rgba(255,255,255,0.08); font-size: 11px; color: #64748b; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .rag-citation strong { color: #94a3b8; }
    button { width: 100%; background: #0284c7; color: white; padding: 15px; border: none; border-radius: 8px; font-weight: 700; font-size: 15px; cursor: pointer; margin-top: 24px; transition: all 0.2s; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3); }
    button:hover { background: #0369a1; transform: translateY(-1px); }
    .footer { text-align: center; font-size: 12px; color: #475569; margin-top: 24px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="rag-status"><span class="pulse-dot"></span> PRISM RAG Engine Active &bull; Simulation Memory Ingested</div>
    <h2>Root-Cause Diagnostic Survey</h2>
    <p class="subtitle">Our diagnostic model formulated these targeted questions based on product technical specifications and cross-channel feedback (Amazon, Flipkart, JioMart, Brand Store, and Steam).</p>
    <form method="POST" action="/v1/survey/{{ token }}">
      {% for q in questions %}
      <div class="question">
        <div class="question-title">{{ loop.index }}. {{ q.question_text }}</div>
        {% for opt in q.options %}
        <label>
          <input type="radio" name="ans_{{ q.question_id }}" value="{{ opt }}" required>
          <span>{{ opt }}</span>
        </label>
        {% endfor %}
        <div class="rag-citation">
          <strong>GROUNDED CITATION:</strong> {{ q.evidence_refs|join(', ') if q.evidence_refs else (q.grounded_data_source or 'Hardware Spec Baseline') }}
          {% if q.processing_note %}
          <br><strong>PROCESSING TRACE:</strong> {{ q.processing_note }}
          {% endif %}
        </div>
      </div>
      {% endfor %}
      <button type="submit">Submit Diagnostic Responses</button>
    </form>
    <div class="footer">PRISM Closed-Loop Verification &bull; HMAC Secured &bull; 7-Day Validity</div>
  </div>
</body>
</html>
"""


@router.post("/investigations/{issue_id}/survey")
async def trigger_investigation_survey(
    issue_id: str,
    payload: SurveyTriggerPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Trigger a RAG diagnostic survey for an issue and send email invite with 6-7 questions."""
    survey, raw_token = await plan(issue_id=issue_id, tenant_id=user.tenant_id, session=db, target_question_count=7)
    await send_survey_invite(
        survey=survey,
        raw_token=raw_token,
        to_email=payload.to_email,
        customer_name=payload.customer_name,
        tenant_id=user.tenant_id,
        session=db,
    )
    rag_trace = {}
    if survey.questions and isinstance(survey.questions[0], dict):
        rag_trace = survey.questions[0].get("rag_processing_trace", {})

    return {
        "status": "survey_dispatched",
        "survey_id": survey.id,
        "issue_id": issue_id,
        "token": raw_token,
        "expires_at": survey.expires_at.isoformat(),
        "total_questions": len(survey.questions or []),
        "rag_memory_used": {
            "source": "rag_simulation_memory.json",
            "platforms_consulted": ["amazon", "flipkart", "jiomart", "brand", "steam"],
            "trace": rag_trace,
        },
        "questions": survey.questions,
    }



@router.get("/survey/{token}", response_class=HTMLResponse)
async def get_survey_page(token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Public tokenized diagnostic survey page (mobile-first HTML)."""
    is_valid, srv_id, ten_id = verify_survey_token(token)
    if not is_valid:
        return HTMLResponse("<h2>Survey link is invalid or expired.</h2>", status_code=404)

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    stmt = select(Survey).where(Survey.token_hash == token_hash, Survey.id == srv_id, Survey.tenant_id == ten_id)
    survey = (await db.execute(stmt)).scalar_one_or_none()

    if not survey:
        return HTMLResponse("<h2>Survey not found or link is invalid.</h2>", status_code=404)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    expires_at = survey.expires_at.replace(tzinfo=timezone.utc) if survey.expires_at.tzinfo is None else survey.expires_at
    if survey.status == "expired" or now > expires_at:
        return HTMLResponse("<div style='text-align:center;padding:50px;font-family:sans-serif;'><h2>Survey Expired</h2><p>This diagnostic link is no longer active.</p></div>", status_code=410)

    if survey.status == "answered":
        return HTMLResponse("<div style='text-align:center;padding:50px;font-family:sans-serif;'><h2>Thank You!</h2><p>You have already submitted this survey.</p></div>")

    # Render template with questions
    from jinja2 import Template
    tmpl = Template(SURVEY_HTML_TEMPLATE)
    html = tmpl.render(token=token, questions=survey.questions or [])
    return HTMLResponse(content=html)


@router.post("/survey/{token}")
async def submit_survey_page(
    token: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Public survey submission endpoint (handles HTML form post or JSON)."""
    if "application/json" in request.headers.get("content-type", ""):
        body = await request.json()
        answers = body.get("answers", {})
    else:
        form_data = await request.form()
        answers = dict(form_data)

    try:
        result = await ingest_reply(token, answers, session=db)
        return HTMLResponse("<div style='text-align:center;padding:50px;font-family:sans-serif;color:#0284c7;'><h2>Feedback Recorded</h2><p>Thank you! Your feedback has been integrated directly into our root-cause diagnostic model.</p></div>")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/survey/{token}/unsubscribe", response_class=HTMLResponse)
async def get_unsubscribe_page(token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Opt-out confirmation page for customer survey follow-ups."""
    is_valid, srv_id, ten_id = verify_survey_token(token)
    if not is_valid:
        return HTMLResponse("<h2>Invalid or expired unsubscribe link.</h2>", status_code=404)

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    stmt = select(Survey).where(Survey.token_hash == token_hash, Survey.id == srv_id, Survey.tenant_id == ten_id)
    survey = (await db.execute(stmt)).scalar_one_or_none()
    if not survey:
        return HTMLResponse("<h2>Invalid or expired unsubscribe link.</h2>", status_code=404)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Unsubscribe Confirmation</title></head>
    <body style="font-family:sans-serif;background:#0f172a;color:#f8fafc;display:flex;justify-content:center;padding:40px;">
      <div style="max-width:480px;background:#1e293b;padding:32px;border-radius:12px;text-align:center;border:1px solid #334155;">
        <h2 style="color:#38bdf8;">Unsubscribe from Product Follow-ups</h2>
        <p style="color:#94a3b8;font-size:14px;">Are you sure you want to opt out of diagnostic quality surveys for this product?</p>
        <form method="POST" action="/v1/survey/{token}/unsubscribe">
          <button type="submit" style="background:#ef4444;color:white;padding:12px 24px;border:none;border-radius:6px;font-weight:bold;cursor:pointer;">
            Confirm Unsubscribe
          </button>
        </form>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/survey/{token}/unsubscribe")
async def process_unsubscribe(token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Expire survey and record customer consent opt-out."""
    is_valid, srv_id, ten_id = verify_survey_token(token)
    if not is_valid:
        raise HTTPException(status_code=404, detail="Invalid or expired survey token")

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    stmt = select(Survey).where(Survey.token_hash == token_hash, Survey.id == srv_id, Survey.tenant_id == ten_id)
    survey = (await db.execute(stmt)).scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Invalid survey token")

    survey.status = "expired"
    await db.commit()
    return HTMLResponse("<div style='text-align:center;padding:50px;font-family:sans-serif;color:#38bdf8;'><h2>Unsubscribed Successfully</h2><p>You have been removed from further diagnostic inquiries. Thank you.</p></div>")


# ── Live Demo Email Endpoints ──────────────────────────────────────────────────

class TestEmailPayload(BaseModel):
    to_email: EmailStr
    customer_name: str = "Judge / Quality Lead"
    product_name: str = "AuraWave Wireless ANC Headphones"
    feature_name: str = "Battery Charging & Thermal Regulation"


class SeriousAlertPayload(BaseModel):
    to_email: EmailStr
    product_name: str
    category: str = "safety"
    severity: str = "critical"
    urgency: str = "immediate"
    verbatim_quote: str
    batch_code: str | None = None
    version_label: str | None = None


class DigestEmailPayload(BaseModel):
    to_email: EmailStr
    role: str = "qa"
    product_name: str = "All Products"
    health_score: float = 88.5
    active_issues: int = 3
    lead_time_days: int = 14
    highlights: list[dict[str, str]] = [
        {"title": "Hinge Fatigue", "description": "Concentrated in BATCH-2024-W12. Lead-time advantage of 14 days."},
        {"title": "Firmware Stability", "description": "98% satisfaction rating on v1.2."},
    ]


@router.post("/email/send-test")
@router.post("/email/survey")
async def send_test_email(
    payload: TestEmailPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Live Demo Email Dispatcher:
    Sends an actual diagnostic survey invitation to any recipient email (e.g. Judge's inbox)
    using Resend REST API, Postmark, or standard SMTP, and logs to the Outbox.
    """
    settings = get_settings()
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test email sending is disabled in production environments.",
        )

    ctx = {
        "customer_name": payload.customer_name,
        "product_name": payload.product_name,
        "feature_name": payload.feature_name,
        "survey_url": "/v1/survey/demo_token",
        "unsubscribe_url": "/v1/survey/demo_token/unsubscribe",
        "subject": f"PRISM Diagnostic Investigation: {payload.product_name}",
    }
    dispatch_result = await send_mail(
        template_name="survey",
        to_email=payload.to_email,
        ctx=ctx,
        tenant_id=user.tenant_id,
        session=db,
    )
    return {
        "status": "success",
        "message": f"Email successfully dispatched to {payload.to_email}",
        "delivery": dispatch_result,
    }


@router.post("/email/serious-alert")
async def dispatch_serious_alert_email(
    payload: SeriousAlertPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Dispatch emergency safety alert to engineering/QA lead inbox."""
    ctx = {
        "category": payload.category,
        "severity": payload.severity,
        "urgency": payload.urgency,
        "product_name": payload.product_name,
        "verbatim_quote": payload.verbatim_quote,
        "batch_code": payload.batch_code,
        "version_label": payload.version_label,
        "investigation_url": "/investigations",
    }
    dispatch_result = await send_mail(
        template_name="serious_alert",
        to_email=payload.to_email,
        ctx=ctx,
        tenant_id=user.tenant_id,
        session=db,
    )
    return {
        "status": "dispatched",
        "message": f"Critical safety alert sent to {payload.to_email}",
        "delivery": dispatch_result,
    }


@router.post("/email/digest")
async def dispatch_digest_email(
    payload: DigestEmailPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Dispatch role-tailored weekly intelligence digest."""
    ctx = {
        "role": payload.role,
        "product_name": payload.product_name,
        "health_score": payload.health_score,
        "active_issues": payload.active_issues,
        "lead_time_days": payload.lead_time_days,
        "highlights": payload.highlights,
        "week_range": "Week 12",
        "dashboard_url": "/dashboard",
    }
    dispatch_result = await send_mail(
        template_name=f"digest_{payload.role}",
        to_email=payload.to_email,
        ctx=ctx,
        tenant_id=user.tenant_id,
        session=db,
    )
    return {
        "status": "dispatched",
        "message": f"Weekly {payload.role.upper()} digest sent to {payload.to_email}",
        "delivery": dispatch_result,
    }


@router.get("/email/outbox")
async def list_email_outbox(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
):
    """List recent emails sent through PRISM with delivery status and preview URLs."""
    from prism_core.db.models import EmailOutbox
    from sqlalchemy import desc

    stmt = (
        select(EmailOutbox)
        .where(EmailOutbox.tenant_id == user.tenant_id)
        .order_by(desc(EmailOutbox.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    return [
        {
            "id": r.id,
            "template": r.template,
            "to_email": r.payload.get("to_email", "masked"),
            "subject": r.payload.get("subject", "Diagnostic Survey"),
            "status": r.status,
            "provider_id": r.provider_id,
            "created_at": r.created_at.isoformat(),
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "error": r.payload.get("error"),
            "preview_url": f"/v1/email/outbox/{r.id}/preview",
        }
        for r in records
    ]


@router.get("/email/outbox/{outbox_id}/preview", response_class=HTMLResponse)
async def preview_email_html(
    outbox_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Serve the raw rendered HTML of an authorized tenant outbox email."""
    from prism_core.db.models import EmailOutbox

    outbox_entry = await db.get(EmailOutbox, outbox_id)
    if not outbox_entry or outbox_entry.tenant_id != user.tenant_id:
        return HTMLResponse("<h2>Email not found in outbox.</h2>", status_code=404)

    html_content = outbox_entry.payload.get("html_body")
    if not html_content:
        return HTMLResponse("<h2>Email has no rendered HTML body.</h2>", status_code=404)

    return HTMLResponse(content=html_content)

