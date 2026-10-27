"""
tests/test_mvp7_rag_survey_and_action.py

Unit tests for MVP 7:
- RAG-grounded diagnostic survey generation (token creation, HMAC verification)
- Confidence delta updating from diagnostic answers
- Serious safety triage (immediate alert triggering for thermal/smoke)
- Jinja email survey outbox rendering
"""
from __future__ import annotations

import pytest

from prism_core.survey import generate_survey_token, verify_survey_token
from prism_core.serious import assess_serious_complaint
from prism_core.mail import render_survey_invitation



def test_survey_token_hmac():
    secret = "test-secret-key-12345"
    token = generate_survey_token(survey_id="srv_001", tenant_id="tenant_x", secret=secret)

    # Valid token verification
    verified, srv_id, ten_id = verify_survey_token(token, secret=secret)
    assert verified is True
    assert srv_id == "srv_001"
    assert ten_id == "tenant_x"

    # Tampered token verification
    tampered = token[:-4] + "abcd"
    verified_tampered, _, _ = verify_survey_token(tampered, secret=secret)
    assert verified_tampered is False


def test_serious_safety_triage():
    # Smoke / blast must trigger critical triage immediately
    crit_text = "Phone started smoking and charger caught fire during overnight charging"
    is_serious, category, severity, urgency = assess_serious_complaint(crit_text)
    assert is_serious is True
    assert category == "thermal"
    assert severity == "critical"
    assert urgency == "immediate"

    # Non-serious feedback
    normal_text = "Good sound quality, battery could be a bit better"
    is_serious_norm, _, _, _ = assess_serious_complaint(normal_text)
    assert is_serious_norm is False


def test_mail_template_rendering():
    rendered = render_survey_invitation(
        customer_name="Aarav",
        product_name="AuraSound ANC Headphones",
        feature="anc",
        survey_url="https://prism.app/survey/tok_12345",
    )
    assert "Aarav" in rendered
    assert "AuraSound ANC Headphones" in rendered
    assert "https://prism.app/survey/tok_12345" in rendered


@pytest.mark.asyncio
async def test_mail_dispatch_and_preview():
    from unittest.mock import AsyncMock, MagicMock
    from prism_core.mail import send

    session_mock = MagicMock()
    session_mock.add = MagicMock()
    session_mock.flush = AsyncMock()

    ctx = {
        "customer_name": "Judge Smith",
        "product_name": "AuraWave ANC",
        "feature_name": "Battery Heat",
        "survey_url": "https://prism.app/v1/survey/demo123",
    }
    res = await send(
        template_name="survey",
        to_email="judge@example.com",
        ctx=ctx,
        tenant_id="tenant_test",
        session=session_mock,
    )
    assert res["status"] == "simulated"
    assert res["status"] not in ("sent", "delivered")
    assert res["to_email"] == "judge@example.com"
    assert "/v1/email/outbox/" in res["preview_url"]


@pytest.mark.asyncio
async def test_mail_provider_failure_handling():
    """Verify safe failure handling: provider errors are logged to outbox with status='failed'."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import smtplib
    from prism_core.mail import send
    from pydantic import SecretStr

    session_mock = MagicMock()
    session_mock.add = MagicMock()
    session_mock.flush = AsyncMock()

    ctx = {
        "customer_name": "Test User",
        "product_name": "Appliance",
        "feature_name": "Motor",
        "survey_url": "https://prism.app/v1/survey/fail123",
    }

    # Simulate SMTP failure
    with patch("prism_core.mail.get_settings") as mock_settings:
        mock_s = MagicMock()
        mock_s.mail_provider = "smtp"
        mock_s.smtp_host = "smtp.invalid.prism.internal"
        mock_s.smtp_port = 587
        mock_s.smtp_user = "user"
        mock_s.smtp_password = SecretStr("pass")
        mock_s.smtp_use_tls = True
        mock_s.mail_from = "noreply@prism.app"
        mock_settings.return_value = mock_s

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=smtplib.SMTPConnectError(421, "Connection refused"))):
            res = await send(
                template_name="survey",
                to_email="test@example.com",
                ctx=ctx,
                tenant_id="tenant_test",
                session=session_mock,
            )

    assert res["status"] == "failed"
    assert "Connection refused" in res["error"]
    assert res["provider"] == "smtp"


def test_legacy_token_migration():
    """Verify migration path: legacy 3-part format and base64 tokens remain verifiable."""
    import hmac
    import hashlib
    import base64

    secret = "migration-secret-key-12345"

    # Legacy format 1: {survey_id}.{tenant_id}.{sig}
    survey_id = "srv_legacy_01"
    tenant_id = "tenant_leg"
    sig = hmac.new(secret.encode(), f"{survey_id}.{tenant_id}".encode(), hashlib.sha256).hexdigest()[:16]
    legacy_3part = f"{survey_id}.{tenant_id}.{sig}"

    is_valid, s_id, t_id = verify_survey_token(legacy_3part, secret=secret)
    assert is_valid is True
    assert s_id == survey_id
    assert t_id == tenant_id

    # Legacy format 2: base64({survey_id}:{tenant_id}:{sig})
    full_sig = hmac.new(secret.encode(), f"{survey_id}:{tenant_id}".encode(), hashlib.sha256).hexdigest()
    raw_b64 = f"{survey_id}:{tenant_id}:{full_sig}"
    legacy_b64 = base64.urlsafe_b64encode(raw_b64.encode()).decode()

    is_valid_b64, s_id_b64, t_id_b64 = verify_survey_token(legacy_b64, secret=secret)
    assert is_valid_b64 is True
    assert s_id_b64 == survey_id
    assert t_id_b64 == tenant_id


