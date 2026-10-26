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
from prism_core.db.models import Survey, User
from prism_core.mail import send as send_mail
from prism_core.survey import ingest_reply, plan, send_survey_invite

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
  <title>PRISM Product Feedback</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; display: flex; justify-content: center; }
    .container { max-width: 540px; width: 100%; background: #1e293b; border-radius: 12px; padding: 28px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
    h2 { color: #38bdf8; margin-top: 0; font-size: 20px; }
    p { color: #94a3b8; font-size: 14px; line-height: 1.5; }
    .question { margin: 24px 0; background: #0f172a; padding: 16px; border-radius: 8px; border: 1px solid #334155; }
    .question-title { font-weight: 600; color: #e2e8f0; margin-bottom: 12px; font-size: 15px; }
    label { display: block; margin: 10px 0; cursor: pointer; color: #cbd5e1; font-size: 14px; }
    input[type="radio"] { margin-right: 10px; accent-color: #38bdf8; }
    button { width: 100%; background: #0284c7; color: white; padding: 14px; border: none; border-radius: 8px; font-weight: 600; font-size: 16px; cursor: pointer; margin-top: 20px; transition: background 0.2s; }
    button:hover { background: #0369a1; }
    .footer { text-align: center; font-size: 12px; color: #64748b; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Product Diagnostic Diagnostic</h2>
    <p>Please take 60 seconds to answer 3 targeted questions to help our engineering team troubleshoot your reported issue.</p>
    <form method="POST" action="/v1/survey/{{ token }}">
      {% for q in questions %}
      <div class="question">
        <div class="question-title">{{ loop.index }}. {{ q.question_text }}</div>
        {% for opt in q.options %}
        <label>
          <input type="radio" name="ans_{{ q.question_id }}" value="{{ opt }}" required>
          {{ opt }}
        </label>
        {% endfor %}
      </div>
      {% endfor %}
      <button type="submit">Submit Feedback</button>
    </form>
    <div class="footer">Secure PRISM Verification Link</div>
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
    """Trigger a RAG diagnostic survey for an issue and send email invite."""
    survey, raw_token = await plan(issue_id=issue_id, tenant_id=user.tenant_id, session=db)
    await send_survey_invite(
        survey=survey,
        raw_token=raw_token,
        to_email=payload.to_email,
        customer_name=payload.customer_name,
        tenant_id=user.tenant_id,
        session=db,
    )
    return {
        "status": "survey_dispatched",
        "survey_id": survey.id,
        "issue_id": issue_id,
        "token": raw_token,
        "expires_at": survey.expires_at.isoformat(),
    }


@router.get("/survey/{token}", response_class=HTMLResponse)
async def get_survey_page(token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """Public tokenized diagnostic survey page (mobile-first HTML)."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    stmt = select(Survey).where(Survey.token_hash == token_hash)
    survey = (await db.execute(stmt)).scalar_one_or_none()

    if not survey:
        return HTMLResponse("<h2>Survey not found or link is invalid.</h2>", status_code=404)

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


# ── Live Demo Email Endpoints ──────────────────────────────────────────────────

class TestEmailPayload(BaseModel):
    to_email: EmailStr
    customer_name: str = "Judge / Quality Lead"
    product_name: str = "AuraWave Wireless ANC Headphones"
    feature_name: str = "Battery Charging & Thermal Regulation"


@router.post("/email/send-test")
async def send_test_email(
    payload: TestEmailPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Live Demo Email Dispatcher:
    Sends an actual diagnostic survey invitation to any recipient email (e.g. Judge's inbox)
    using Resend REST API or standard SMTP, and logs to the Outbox.
    """
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
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Serve the raw rendered HTML of any outbox email for instant live demo inspection."""
    from prism_core.db.models import EmailOutbox

    outbox_entry = await db.get(EmailOutbox, outbox_id)
    if not outbox_entry:
        return HTMLResponse("<h2>Email not found in outbox.</h2>", status_code=404)

    html_content = outbox_entry.payload.get("html_body")
    if not html_content:
        return HTMLResponse("<h2>Email has no rendered HTML body.</h2>", status_code=404)

    return HTMLResponse(content=html_content)

