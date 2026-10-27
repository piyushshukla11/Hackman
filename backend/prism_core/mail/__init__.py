"""
prism_core/mail/__init__.py

L5 Act — Email Delivery Service.
Sends transactional emails:
- survey: customer diagnostic survey link with signed expiring token & unsubscribe footer
- reminder: gentle 3-day reminder for pending customer diagnostic surveys
- serious_alert: urgent notification to engineering/QA leads regarding critical safety/thermal/injury risks
- digest: weekly role-tailored report digests (qa, ops, support, marketing, leadership)

Supports 4 delivery backends:
1. Resend REST API (when mail_provider == "resend" and mail_provider_key is set)
2. Postmark REST API (when mail_provider == "postmark" and mail_provider_key is set)
3. Standard SMTP (Gmail App Password, Brevo, SendGrid, Amazon SES via smtp_host/smtp_user/smtp_password)
4. Simulated Outbox (dev/offline fallback that guarantees full preview in demo UI)

All emails are recorded in the `email_outbox` table with status, provider ID, and rendered HTML preview.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional
import httpx
from jinja2 import Template
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.config.settings import Settings, get_settings
from prism_core.db.base import get_sessionmaker
from prism_core.db.models import EmailOutbox
from prism_core.mail.gmail import (
    GmailAuthError,
    GmailDeliveryError,
    clear_gmail_token_cache,
    refresh_gmail_access_token,
    send_via_gmail_api,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. HTML Email Templates
# ─────────────────────────────────────────────────────────────────────────────

SURVEY_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Product Diagnostic Feedback</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
    <div style="background: #0f172a; padding: 24px; text-align: center;">
      <h2 style="color: #38bdf8; margin: 0; font-size: 20px; font-weight: 700;">PRISM Engineering Diagnostic</h2>
      <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 13px;">Customer Quality Investigation</p>
    </div>
    <div style="padding: 28px;">
      <p style="margin-top: 0; font-size: 15px;">Hi <strong>{{ customer_name }}</strong>,</p>
      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        Thank you for your recent review regarding your <strong>{{ product_name }}</strong>.
      </p>
      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        Our quality engineering team has flagged an isolated concern regarding <strong>{{ feature_name }}</strong>. We have generated 3 targeted root-cause questions to help our firmware and hardware teams resolve this for all users.
      </p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{{ survey_url }}" style="background: #0284c7; color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 15px; display: inline-block; box-shadow: 0 2px 4px rgba(2, 132, 199, 0.3);">
          Answer 3 Diagnostic Questions &rarr;
        </a>
      </div>
      <p style="font-size: 12px; color: #64748b; text-align: center;">
        Takes under 60 seconds. This secure link is valid for 7 days.
      </p>
      <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 28px 0;" />
      <p style="font-size: 12px; color: #94a3b8; text-align: center; line-height: 1.5; margin-bottom: 0;">
        You received this message because you opted into product support follow-ups.<br />
        <a href="{{ unsubscribe_url }}" style="color: #64748b; text-decoration: underline;">Unsubscribe from diagnostic follow-ups</a>
      </p>
    </div>
  </div>
</body>
</html>
"""

SURVEY_REMINDER_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reminder: Product Diagnostic Feedback</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
    <div style="background: #0369a1; padding: 20px; text-align: center;">
      <h2 style="color: #ffffff; margin: 0; font-size: 18px; font-weight: 700;">Reminder: Help Us Improve {{ product_name }}</h2>
    </div>
    <div style="padding: 28px;">
      <p style="margin-top: 0; font-size: 15px;">Hi <strong>{{ customer_name }}</strong>,</p>
      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        This is a quick, gentle reminder regarding the 3-question diagnostic survey for your <strong>{{ product_name }}</strong>.
      </p>
      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        Your feedback on <strong>{{ feature_name }}</strong> directly informs our engineering investigations. This link will expire in 4 days.
      </p>
      <div style="text-align: center; margin: 28px 0;">
        <a href="{{ survey_url }}" style="background: #0284c7; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">
          Complete Quick Diagnostic &rarr;
        </a>
      </div>
      <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0;" />
      <p style="font-size: 11px; color: #94a3b8; text-align: center;">
        <a href="{{ unsubscribe_url }}" style="color: #64748b;">Opt out of diagnostic reminders</a>
      </p>
    </div>
  </div>
</body>
</html>
"""

SERIOUS_ALERT_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>CRITICAL ALERT: Serious Product Safety Risk</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 2px solid #ef4444; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
    <div style="background: #dc2626; padding: 20px; text-align: center;">
      <span style="background: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase;">Action Required</span>
      <h2 style="color: #ffffff; margin: 8px 0 0 0; font-size: 20px; font-weight: 700;">Critical Safety Alert: {{ category | upper }}</h2>
    </div>
    <div style="padding: 24px;">
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
        <tr>
          <td style="padding: 8px 0; color: #64748b; width: 35%;">Product:</td>
          <td style="padding: 8px 0; font-weight: 600; color: #0f172a;">{{ product_name }}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #64748b;">Batch / Version:</td>
          <td style="padding: 8px 0; font-weight: 600; color: #0f172a;">{{ batch_code or 'Unknown Batch' }} ({{ version_label or 'Current' }})</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #64748b;">Severity / Urgency:</td>
          <td style="padding: 8px 0;">
            <span style="background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{{ severity | upper }}</span>
            <span style="background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 6px;">{{ urgency | upper }}</span>
          </td>
        </tr>
      </table>

      <div style="background: #fff1f2; border-left: 4px solid #e11d48; padding: 16px; border-radius: 4px; margin: 16px 0;">
        <div style="font-size: 12px; font-weight: 700; color: #9f1239; margin-bottom: 6px; text-transform: uppercase;">Customer Verbatim</div>
        <p style="margin: 0; font-size: 14px; font-style: italic; color: #4c0519; line-height: 1.5;">
          "{{ verbatim_quote }}"
        </p>
      </div>

      <div style="text-align: center; margin: 28px 0 10px 0;">
        <a href="{{ investigation_url }}" style="background: #dc2626; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">
          Open Safety Incident Investigation &rarr;
        </a>
      </div>
    </div>
  </div>
</body>
</html>
"""

DIGEST_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>PRISM Weekly Quality Digest</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
    <div style="background: #0f172a; padding: 20px 24px; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h2 style="color: #38bdf8; margin: 0; font-size: 18px; font-weight: 700;">PRISM Weekly Intelligence Digest</h2>
        <p style="color: #94a3b8; margin: 2px 0 0 0; font-size: 12px;">Tailored for: <strong>{{ role | upper }}</strong> | {{ week_range }}</p>
      </div>
    </div>
    <div style="padding: 24px;">
      <h3 style="margin-top: 0; font-size: 16px; color: #0f172a;">Executive Quality Summary: {{ product_name }}</h3>
      
      <div style="display: flex; gap: 12px; margin: 20px 0;">
        <div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; text-align: center;">
          <div style="font-size: 24px; font-weight: 800; color: #0284c7;">{{ health_score }}<span style="font-size: 14px; font-weight: normal; color: #64748b;">/100</span></div>
          <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Health Score</div>
        </div>
        <div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; text-align: center;">
          <div style="font-size: 24px; font-weight: 800; color: #e11d48;">{{ active_issues }}</div>
          <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Active Clusters</div>
        </div>
        <div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; text-align: center;">
          <div style="font-size: 24px; font-weight: 800; color: #059669;">+{{ lead_time_days }}d</div>
          <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Lead-Time Adv.</div>
        </div>
      </div>

      <h4 style="font-size: 14px; color: #334155; margin-bottom: 8px;">Top Focus Areas This Week:</h4>
      <ul style="font-size: 13px; color: #475569; line-height: 1.6; padding-left: 20px; margin-top: 0;">
        {% for item in highlights %}
        <li><strong>{{ item.title }}:</strong> {{ item.description }}</li>
        {% endfor %}
      </ul>

      <div style="text-align: center; margin: 28px 0 8px 0;">
        <a href="{{ dashboard_url }}" style="background: #0284c7; color: #ffffff; padding: 10px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 13px; display: inline-block;">
          Open Full PRISM Analytics Dashboard &rarr;
        </a>
      </div>
    </div>
  </div>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# 2. Template Render Helpers
# ─────────────────────────────────────────────────────────────────────────────

def render_survey_invitation(
    customer_name: str,
    product_name: str,
    feature: str,
    survey_url: str,
    unsubscribe_url: str = "#",
) -> str:
    """Render survey invitation HTML using the Jinja template."""
    tmpl = Template(SURVEY_EMAIL_TEMPLATE)
    return tmpl.render(
        customer_name=customer_name,
        product_name=product_name,
        feature_name=feature,
        survey_url=survey_url,
        unsubscribe_url=unsubscribe_url,
    )


def render_survey_reminder(
    customer_name: str,
    product_name: str,
    feature: str,
    survey_url: str,
    unsubscribe_url: str = "#",
) -> str:
    """Render 3-day survey reminder HTML."""
    tmpl = Template(SURVEY_REMINDER_EMAIL_TEMPLATE)
    return tmpl.render(
        customer_name=customer_name,
        product_name=product_name,
        feature_name=feature,
        survey_url=survey_url,
        unsubscribe_url=unsubscribe_url,
    )


def render_serious_alert(
    category: str,
    severity: str,
    urgency: str,
    product_name: str,
    verbatim_quote: str,
    batch_code: str | None = None,
    version_label: str | None = None,
    investigation_url: str = "/investigations",
) -> str:
    """Render urgent engineering serious safety alert HTML."""
    tmpl = Template(SERIOUS_ALERT_EMAIL_TEMPLATE)
    return tmpl.render(
        category=category,
        severity=severity,
        urgency=urgency,
        product_name=product_name,
        verbatim_quote=verbatim_quote,
        batch_code=batch_code,
        version_label=version_label,
        investigation_url=investigation_url,
    )


def render_digest_email(
    role: str,
    product_name: str,
    health_score: float | int,
    active_issues: int,
    lead_time_days: int,
    highlights: list[dict[str, str]],
    week_range: str = "This Week",
    dashboard_url: str = "/dashboard",
) -> str:
    """Render role-tailored weekly digest HTML."""
    tmpl = Template(DIGEST_EMAIL_TEMPLATE)
    return tmpl.render(
        role=role,
        product_name=product_name,
        health_score=health_score,
        active_issues=active_issues,
        lead_time_days=lead_time_days,
        highlights=highlights,
        week_range=week_range,
        dashboard_url=dashboard_url,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. SMTP Sync Worker
# ─────────────────────────────────────────────────────────────────────────────

def _send_smtp_sync(
    host: str,
    port: int,
    user: str | None,
    password: str | None,
    use_tls: bool,
    from_addr: str,
    to_addr: str,
    subject: str,
    html_body: str,
) -> str:
    """Synchronous SMTP worker running inside an async worker thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    plain_text = f"{subject}\n\nPlease view this email in an HTML-compatible client."
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    server = smtplib.SMTP(host, port, timeout=10)
    try:
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
        return f"smtp_{hashlib.sha256(to_addr.encode()).hexdigest()[:8]}"
    finally:
        try:
            server.quit()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# 4. Main Send Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

async def send(
    template_name: str,
    to_email: str,
    ctx: dict[str, Any],
    tenant_id: str = "default",
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Public entrypoint for L5 Mail Delivery.
    Renders template, logs to email_outbox, and sends via Resend, Postmark, SMTP, or Simulated Outbox.
    Returns dictionary with outbox_id, status, provider, and preview URL.
    """
    settings = get_settings()
    to_clean = to_email.strip().lower()
    to_hash = hashlib.sha256(to_clean.encode("utf-8")).hexdigest()

    # Route template to appropriate renderer
    if template_name in ("serious_alert", "safety_alert"):
        html_body = render_serious_alert(
            category=ctx.get("category", "safety"),
            severity=ctx.get("severity", "critical"),
            urgency=ctx.get("urgency", "immediate"),
            product_name=ctx.get("product_name", "Device"),
            verbatim_quote=ctx.get("verbatim_quote", "Unspecified hazard reported"),
            batch_code=ctx.get("batch_code"),
            version_label=ctx.get("version_label"),
            investigation_url=ctx.get("investigation_url", "/investigations"),
        )
        subject = ctx.get("subject", f"CRITICAL QUALITY ALERT: {ctx.get('product_name', 'Device')} {ctx.get('category', 'Safety')}")
    elif template_name in ("reminder", "survey_reminder"):
        html_body = render_survey_reminder(
            customer_name=ctx.get("customer_name", "Valued Customer"),
            product_name=ctx.get("product_name", "Device"),
            feature=ctx.get("feature_name", "the reported issue"),
            survey_url=ctx.get("survey_url", "/v1/survey/demo_token"),
            unsubscribe_url=ctx.get("unsubscribe_url", "/v1/survey/demo_token/unsubscribe"),
        )
        subject = ctx.get("subject", f"Reminder: Quick diagnostic on your {ctx.get('product_name', 'Device')}")
    elif template_name.startswith("digest"):
        role_name = template_name.replace("digest_", "") if "_" in template_name else ctx.get("role", "quality")
        html_body = render_digest_email(
            role=role_name,
            product_name=ctx.get("product_name", "All Products"),
            health_score=ctx.get("health_score", 92),
            active_issues=ctx.get("active_issues", 2),
            lead_time_days=ctx.get("lead_time_days", 14),
            highlights=ctx.get("highlights", [
                {"title": "Hinge Fatigue", "description": "Concentrated in BATCH-2024-W12. Lead-time advantage of 14 days."},
                {"title": "Firmware Stability", "description": "98% satisfaction rating on v1.2."},
            ]),
            week_range=ctx.get("week_range", "Week 12"),
            dashboard_url=ctx.get("dashboard_url", "/dashboard"),
        )
        subject = ctx.get("subject", f"PRISM Weekly Quality Digest: {ctx.get('product_name', 'Overview')}")
    else:
        # Default: survey invitation
        html_body = render_survey_invitation(
            customer_name=ctx.get("customer_name", "Valued Customer"),
            product_name=ctx.get("product_name", "Device"),
            feature=ctx.get("feature_name", "the reported issue"),
            survey_url=ctx.get("survey_url", "/v1/survey/demo_token"),
            unsubscribe_url=ctx.get("unsubscribe_url", "/v1/survey/demo_token/unsubscribe"),
        )
        subject = ctx.get("subject", f"Product Diagnostic: {ctx.get('product_name', 'Feedback')}")

    async def _dispatch(sess: AsyncSession) -> dict[str, Any]:
        import uuid
        outbox_id = str(uuid.uuid4())
        outbox_entry = EmailOutbox(
            id=outbox_id,
            tenant_id=tenant_id,
            template=template_name,
            to_hash=to_hash,
            payload={
                "to_email": to_clean,
                "subject": subject,
                "customer_name": ctx.get("customer_name"),
                "product_name": ctx.get("product_name"),
                "survey_url": ctx.get("survey_url"),
                "survey_id": ctx.get("survey_id"),
                "html_body": html_body,
            },
            status="queued",
        )
        sess.add(outbox_entry)
        await sess.flush()

        provider_name = "simulated"
        provider_id = None
        error_msg = None

        # ── Provider Resolution ─────────────────────────────────────────────────
        provider_mode = str(getattr(settings, "mail_provider", "simulated")).lower()
        gmail_cid = getattr(settings, "gmail_client_id", None)
        gmail_csec = getattr(settings, "gmail_client_secret", None)
        gmail_rtok = getattr(settings, "gmail_refresh_token", None)

        has_gmail_oauth = False
        if provider_mode == "gmail":
            has_gmail_oauth = True
        elif gmail_cid and gmail_csec and gmail_rtok:
            if hasattr(gmail_cid, "get_secret_value") and hasattr(gmail_csec, "get_secret_value") and hasattr(gmail_rtok, "get_secret_value"):
                has_gmail_oauth = bool(gmail_cid.get_secret_value() and gmail_csec.get_secret_value() and gmail_rtok.get_secret_value())
            elif isinstance(gmail_cid, str) and isinstance(gmail_csec, str) and isinstance(gmail_rtok, str):
                has_gmail_oauth = bool(gmail_cid and gmail_csec and gmail_rtok)

        # ── Pathway 1: Google Gmail OAuth 2.0 REST API ──────────────────────────
        if provider_mode == "gmail" or (
            has_gmail_oauth
            and provider_mode not in ("smtp", "postmark", "resend", "simulated")
            and not getattr(settings, "smtp_host", None)
        ):
            provider_name = "gmail"
            client_id = settings.gmail_client_id.get_secret_value() if settings.gmail_client_id else ""
            client_secret = settings.gmail_client_secret.get_secret_value() if settings.gmail_client_secret else ""
            refresh_token = settings.gmail_refresh_token.get_secret_value() if settings.gmail_refresh_token else ""
            from_addr = settings.gmail_user_email or settings.mail_from

            if not (client_id and client_secret and refresh_token):
                outbox_entry.status = "failed"
                error_msg = "Gmail OAuth credentials incomplete (missing client_id, client_secret, or refresh_token)"
            else:
                try:
                    provider_id = await send_via_gmail_api(
                        to_addr=to_clean,
                        from_addr=from_addr,
                        subject=subject,
                        html_body=html_body,
                        client_id=client_id,
                        client_secret=client_secret,
                        refresh_token=refresh_token,
                    )
                    outbox_entry.status = "sent"
                    outbox_entry.provider_id = provider_id
                    outbox_entry.sent_at = datetime.now(timezone.utc)
                except Exception as e:
                    outbox_entry.status = "failed"
                    error_msg = str(e)

        # ── Pathway 2: Explicit SMTP Alternative (Gmail App Password, Brevo, SendGrid) ─
        elif provider_mode == "smtp" or (getattr(settings, "smtp_host", None) and provider_mode not in ("gmail", "postmark", "resend", "simulated")):
            provider_name = "smtp"
            smtp_pwd = settings.smtp_password.get_secret_value() if settings.smtp_password else None
            try:
                provider_id = await asyncio.to_thread(
                    _send_smtp_sync,
                    host=settings.smtp_host,
                    port=settings.smtp_port,
                    user=settings.smtp_user,
                    password=smtp_pwd,
                    use_tls=settings.smtp_use_tls,
                    from_addr=settings.mail_from,
                    to_addr=to_clean,
                    subject=subject,
                    html_body=html_body,
                )
                outbox_entry.status = "sent"
                outbox_entry.provider_id = provider_id
                outbox_entry.sent_at = datetime.now(timezone.utc)
            except Exception as e:
                outbox_entry.status = "failed"
                error_msg = str(e)

        # ── Pathway 3: Postmark REST API ────────────────────────────────────────
        elif settings.mail_provider == "postmark" and settings.mail_provider_key:
            provider_name = "postmark"
            api_key = settings.mail_provider_key.get_secret_value()
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        "https://api.postmarkapp.com/email",
                        headers={
                            "X-Postmark-Server-Token": api_key,
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        json={
                            "From": settings.mail_from,
                            "To": to_clean,
                            "Subject": subject,
                            "HtmlBody": html_body,
                        },
                    )
                    if resp.status_code == 200:
                        outbox_entry.status = "sent"
                        provider_id = resp.json().get("MessageID")
                        outbox_entry.provider_id = provider_id
                        outbox_entry.sent_at = datetime.now(timezone.utc)
                    else:
                        outbox_entry.status = "failed"
                        error_msg = f"Postmark HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                outbox_entry.status = "failed"
                error_msg = str(e)

        # ── Pathway 4: Resend REST API ──────────────────────────────────────────
        elif settings.mail_provider == "resend" and settings.mail_provider_key:
            provider_name = "resend"
            api_key = settings.mail_provider_key.get_secret_value()
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={
                            "from": settings.mail_from,
                            "to": [to_clean],
                            "subject": subject,
                            "html": html_body,
                        },
                    )
                    if resp.status_code in (200, 201):
                        outbox_entry.status = "sent"
                        provider_id = resp.json().get("id")
                        outbox_entry.provider_id = provider_id
                        outbox_entry.sent_at = datetime.now(timezone.utc)
                    else:
                        outbox_entry.status = "failed"
                        error_msg = f"Resend HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                outbox_entry.status = "failed"
                error_msg = str(e)

        # ── Pathway 5: Live Simulated Outbox (Demo & Test Safe) ─────────────────
        else:
            provider_name = "simulated"
            outbox_entry.status = "simulated"
            _oid = outbox_entry.id or outbox_id
            provider_id = f"sim_{_oid[:10]}"
            outbox_entry.provider_id = provider_id
            outbox_entry.sent_at = datetime.now(timezone.utc)

        if error_msg:
            outbox_entry.payload["error"] = error_msg

        _oid = outbox_entry.id or outbox_id
        return {
            "outbox_id": _oid,
            "status": outbox_entry.status,
            "provider": provider_name,
            "provider_id": provider_id,
            "to_email": to_clean,
            "subject": subject,
            "error": error_msg,
            "preview_url": f"/v1/email/outbox/{_oid}/preview",
        }

    if session is not None:
        return await _dispatch(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            res = await _dispatch(sess)
            await sess.commit()
            return res


__all__ = [
    "send",
    "render_survey_invitation",
    "render_survey_reminder",
    "render_serious_alert",
    "render_digest_email",
    "send_via_gmail_api",
    "refresh_gmail_access_token",
    "clear_gmail_token_cache",
    "GmailAuthError",
    "GmailDeliveryError",
]

