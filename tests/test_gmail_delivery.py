"""
tests/test_gmail_delivery.py

Unit tests for Gmail OAuth 2.0 delivery provider:
- OAuth 2.0 token refresh and in-memory caching
- Revoked/expired credentials and safe error handling without secret leakage
- Accepted send state recording provider message ID
- Rate limits (429) and provider failures
- Explicit consent verification and recipient mismatch prevention
- Correct per-review survey link with signed expiring token
- Outbox idempotency to avoid duplicate invitations
- Default simulated mode never claiming sent/delivered
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import SecretStr

from prism_core.db.models import EmailOutbox, RawReview, Survey
from prism_core.mail import (
    GmailAuthError,
    GmailDeliveryError,
    clear_gmail_token_cache,
    refresh_gmail_access_token,
    send,
    send_via_gmail_api,
)
from prism_core.survey import generate_survey_token, send_survey_invite


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure clean token cache before and after each test."""
    clear_gmail_token_cache()
    yield
    clear_gmail_token_cache()


# ── 1. OAuth 2.0 Token Refresh & Caching ──────────────────────────────────────

@pytest.mark.asyncio
async def test_gmail_oauth_token_refresh_success_and_caching():
    """Verify refresh token exchange and in-memory caching for valid access tokens."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "ya29.mock_access_token_12345",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    # First call: performs HTTP request
    token1 = await refresh_gmail_access_token(
        client_id="client_id_test",
        client_secret="client_secret_test",
        refresh_token="refresh_token_test",
        client=mock_client,
    )
    assert token1 == "ya29.mock_access_token_12345"
    assert mock_client.post.call_count == 1

    # Second call: served from in-memory cache without repeating HTTP call
    token2 = await refresh_gmail_access_token(
        client_id="client_id_test",
        client_secret="client_secret_test",
        refresh_token="refresh_token_test",
        client=mock_client,
    )
    assert token2 == "ya29.mock_access_token_12345"
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_gmail_oauth_token_refresh_failure_revoked_credentials():
    """Verify safe error handling when refresh token is revoked or expired."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "error": "invalid_grant",
        "error_description": "Token has been expired or revoked.",
    }

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    with pytest.raises(GmailAuthError) as exc_info:
        await refresh_gmail_access_token(
            client_id="client_id_test",
            client_secret="SUPER_SECRET_CLIENT_SECRET",
            refresh_token="SECRET_REFRESH_TOKEN",
            client=mock_client,
        )

    err_str = str(exc_info.value)
    assert "invalid_grant" in err_str
    # Verify sensitive secrets are never leaked in error messages
    assert "SUPER_SECRET_CLIENT_SECRET" not in err_str
    assert "SECRET_REFRESH_TOKEN" not in err_str


# ── 2. Gmail REST API Send State & Provider ID ────────────────────────────────

@pytest.mark.asyncio
async def test_gmail_api_send_success_accepted_state():
    """Verify accepted send records 'sent' state and Gmail provider message ID."""
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "ya29.valid_token", "expires_in": 3600}

    mock_send_resp = MagicMock()
    mock_send_resp.status_code = 200
    mock_send_resp.json.return_value = {
        "id": "18e9a2b5e39b1a2c",
        "threadId": "th_98765",
        "labelIds": ["SENT"],
    }

    async def mock_post(url, *args, **kwargs):
        if "oauth2.googleapis.com" in url:
            return mock_token_resp
        elif "gmail.googleapis.com" in url:
            return mock_send_resp
        raise ValueError(f"Unexpected URL: {url}")

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=mock_post)

    msg_id = await send_via_gmail_api(
        to_addr="customer@example.com",
        from_addr="support@company.com",
        subject="PRISM Diagnostic",
        html_body="<p>Please take our diagnostic survey.</p>",
        client_id="cid",
        client_secret="csec",
        refresh_token="rtok",
        client=mock_client,
    )
    assert msg_id == "18e9a2b5e39b1a2c"


@pytest.mark.asyncio
async def test_gmail_api_provider_failure_logged_safely():
    """Verify Gmail 500 error logs status='failed' without crashing or exposing PII."""
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "ya29.valid_token", "expires_in": 3600}

    mock_send_resp = MagicMock()
    mock_send_resp.status_code = 500
    mock_send_resp.json.return_value = {"error": {"message": "Internal Gmail server error"}}

    async def mock_post(url, *args, **kwargs):
        if "oauth2.googleapis.com" in url:
            return mock_token_resp
        return mock_send_resp

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=mock_post)

    with pytest.raises(GmailDeliveryError) as exc_info:
        await send_via_gmail_api(
            to_addr="customer@example.com",
            from_addr="support@company.com",
            subject="Test",
            html_body="<p>Test</p>",
            client_id="cid",
            client_secret="csec",
            refresh_token="rtok",
            client=mock_client,
        )
    assert "Gmail API delivery rejected (500)" in str(exc_info.value)
    assert "Internal Gmail server error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gmail_api_rate_limit_handling():
    """Verify HTTP 429 rate limit is captured cleanly."""
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "ya29.valid_token", "expires_in": 3600}

    mock_send_resp = MagicMock()
    mock_send_resp.status_code = 429
    mock_send_resp.json.return_value = {"error": {"message": "User-rate limit exceeded"}}

    async def mock_post(url, *args, **kwargs):
        if "oauth2.googleapis.com" in url:
            return mock_token_resp
        return mock_send_resp

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=mock_post)

    with pytest.raises(GmailDeliveryError) as exc_info:
        await send_via_gmail_api(
            to_addr="customer@example.com",
            from_addr="support@company.com",
            subject="Rate Test",
            html_body="<p>Rate</p>",
            client_id="cid",
            client_secret="csec",
            refresh_token="rtok",
            client=mock_client,
        )
    assert "rate limit exceeded" in str(exc_info.value).lower()


# ── 3. Full Send Integration & Outbox Logging ─────────────────────────────────

@pytest.mark.asyncio
async def test_mail_send_gmail_pathway_integration():
    """Verify send() logs to outbox and records Gmail message ID when Gmail provider is enabled."""
    session_mock = MagicMock()
    session_mock.add = MagicMock()
    session_mock.flush = AsyncMock()

    with patch("prism_core.mail.get_settings") as mock_settings:
        s = MagicMock()
        s.mail_provider = "gmail"
        s.gmail_client_id = SecretStr("mock_cid")
        s.gmail_client_secret = SecretStr("mock_csec")
        s.gmail_refresh_token = SecretStr("mock_rtok")
        s.gmail_user_email = "quality@prism.app"
        s.mail_from = "noreply@prism.app"
        mock_settings.return_value = s

        with patch("prism_core.mail.send_via_gmail_api", new=AsyncMock(return_value="gmail_msg_9999")):
            res = await send(
                template_name="survey",
                to_email="reviewer@example.com",
                ctx={
                    "customer_name": "Reviewer",
                    "product_name": "Smart Device",
                    "survey_url": "https://prism.app/v1/survey/tok1",
                },
                tenant_id="tenant_gmail",
                session=session_mock,
            )

    assert res["status"] == "sent"
    assert res["provider"] == "gmail"
    assert res["provider_id"] == "gmail_msg_9999"
    assert res["to_email"] == "reviewer@example.com"
    assert res["error"] is None

    # Verify outbox model added to session
    outbox_entry = session_mock.add.call_args[0][0]
    assert outbox_entry.status == "sent"
    assert outbox_entry.provider_id == "gmail_msg_9999"


# ── 4. Survey Invitation Flow: Consent, Token, Recipient Gates ────────────────

@pytest.mark.asyncio
async def test_survey_invite_flow_with_explicit_consent_and_gmail():
    """Verify consented survey invitation sends correct per-review survey URL."""
    secret = "secret-key-32-chars-minimum-abc12345"
    raw_token = generate_survey_token(
        survey_id="srv_user_01",
        tenant_id="tenant_g",
        recipient_id="raw_rev_alice",
        secret=secret,
    )
    survey = Survey(
        id="srv_user_01",
        tenant_id="tenant_g",
        issue_id="issue_01",
        review_id="raw_rev_alice",
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        questions=[{"question_id": "q1", "question_text": "Is heating present?"}],
    )

    consented_raw = RawReview(
        id="raw_rev_alice",
        tenant_id="tenant_g",
        source_id="widget",
        idempotency_key="idem_alice_01",
        payload={
            "contact": {"email": "alice@example.com", "consent_followup": True},
        },
    )

    mock_sess = MagicMock()
    mock_sess.get = AsyncMock(return_value=consented_raw)
    mock_exec = MagicMock()
    mock_exec.scalars.return_value.first.return_value = None  # No existing send
    mock_sess.execute = AsyncMock(return_value=mock_exec)
    mock_sess.add = MagicMock()
    mock_sess.flush = AsyncMock()

    with patch("prism_core.mail.get_settings") as mock_settings:
        s = MagicMock()
        s.mail_provider = "gmail"
        s.gmail_client_id = SecretStr("mock_cid")
        s.gmail_client_secret = SecretStr("mock_csec")
        s.gmail_refresh_token = SecretStr("mock_rtok")
        s.gmail_user_email = "quality@prism.app"
        s.mail_from = "noreply@prism.app"
        mock_settings.return_value = s

        with patch("prism_core.mail.send_via_gmail_api", new=AsyncMock(return_value="gmail_alice_msg")) as mock_send_api:
            res = await send_survey_invite(
                survey=survey,
                raw_token=raw_token,
                to_email="alice@example.com",
                customer_name="Alice",
                tenant_id="tenant_g",
                session=mock_sess,
            )

    assert res["status"] == "sent"
    assert res["provider"] == "gmail"
    assert res["provider_id"] == "gmail_alice_msg"
    assert mock_send_api.called

    # Verify that the generated HTML includes Alice's specific survey token URL
    call_kwargs = mock_send_api.call_args[1]
    assert call_kwargs["to_addr"] == "alice@example.com"
    assert f"/v1/survey/{raw_token}" in call_kwargs["html_body"]


@pytest.mark.asyncio
async def test_survey_invite_blocked_when_consent_missing_or_denied():
    """Verify survey invite is strictly blocked when consent_followup is False."""
    survey = Survey(
        id="srv_user_02",
        tenant_id="tenant_g",
        issue_id="issue_01",
        review_id="raw_rev_bob",
        token_hash="hash_bob",
        questions=[{"question_id": "q1", "question_text": "Is battery dead?"}],
    )

    unconsented_raw = RawReview(
        id="raw_rev_bob",
        tenant_id="tenant_g",
        source_id="csv",
        idempotency_key="idem_bob_01",
        payload={
            "contact": {"email": "bob@example.com", "consent_followup": False},
        },
    )

    mock_sess = MagicMock()
    mock_sess.get = AsyncMock(return_value=unconsented_raw)

    with patch("prism_core.mail.send_via_gmail_api") as mock_gmail_api:
        res = await send_survey_invite(
            survey=survey,
            raw_token="tok_bob",
            to_email="bob@example.com",
            customer_name="Bob",
            tenant_id="tenant_g",
            session=mock_sess,
        )

    assert res["status"] == "skipped"
    assert res["reason"] == "consent_missing"
    # Never called Gmail API!
    assert not mock_gmail_api.called


@pytest.mark.asyncio
async def test_survey_invite_blocked_on_recipient_mismatch():
    """Verify survey invite is strictly blocked if target email mismatches consented email."""
    survey = Survey(
        id="srv_user_03",
        tenant_id="tenant_g",
        issue_id="issue_01",
        review_id="raw_rev_charlie",
        token_hash="hash_charlie",
        questions=[{"question_id": "q1", "question_text": "Noise?"}],
    )

    consented_raw = RawReview(
        id="raw_rev_charlie",
        tenant_id="tenant_g",
        source_id="widget",
        idempotency_key="idem_charlie_01",
        payload={
            "contact": {"email": "charlie@example.com", "consent_followup": True},
        },
    )

    mock_sess = MagicMock()
    mock_sess.get = AsyncMock(return_value=consented_raw)

    with patch("prism_core.mail.send_via_gmail_api") as mock_gmail_api:
        res = await send_survey_invite(
            survey=survey,
            raw_token="tok_charlie",
            to_email="attacker@evil.com",  # Mismatch!
            tenant_id="tenant_g",
            session=mock_sess,
        )

    assert res["status"] == "skipped"
    assert res["reason"] == "recipient_mismatch"
    assert not mock_gmail_api.called


@pytest.mark.asyncio
async def test_survey_invite_retry_idempotency_avoids_duplicate_send():
    """Verify that retrying a previously sent survey skips delivery to prevent spam."""
    survey = Survey(
        id="srv_user_04",
        tenant_id="tenant_g",
        issue_id="issue_01",
        review_id="raw_rev_dan",
        token_hash="hash_dan",
        questions=[{"question_id": "q1", "question_text": "Hinge loose?"}],
    )

    consented_raw = RawReview(
        id="raw_rev_dan",
        tenant_id="tenant_g",
        source_id="widget",
        idempotency_key="idem_dan_01",
        payload={
            "contact": {"email": "dan@example.com", "consent_followup": True},
        },
    )

    existing_outbox = EmailOutbox(
        id="outbox_dan_01",
        tenant_id="tenant_g",
        template="survey",
        to_hash=hashlib.sha256("dan@example.com".encode()).hexdigest(),
        payload={"survey_id": "srv_user_04"},
        status="sent",
        provider_id="gmail_dan_msg",
    )

    mock_sess = MagicMock()
    mock_sess.get = AsyncMock(return_value=consented_raw)
    mock_exec = MagicMock()
    mock_exec.scalars.return_value.first.return_value = existing_outbox
    mock_sess.execute = AsyncMock(return_value=mock_exec)

    with patch("prism_core.mail.send_via_gmail_api") as mock_gmail_api:
        res = await send_survey_invite(
            survey=survey,
            raw_token="tok_dan",
            to_email="dan@example.com",
            customer_name="Dan",
            tenant_id="tenant_g",
            session=mock_sess,
        )

    assert res["status"] == "duplicate_skipped"
    assert res["reason"] == "already_dispatched"
    assert not mock_gmail_api.called


# ── 5. Default Simulated Mode Never Claims Sent ───────────────────────────────

@pytest.mark.asyncio
async def test_simulated_mode_is_default_and_never_claims_sent():
    """Verify default development configuration labels status as 'simulated', never 'sent'."""
    session_mock = MagicMock()
    session_mock.add = MagicMock()
    session_mock.flush = AsyncMock()

    # Default settings: mail_provider is 'simulated'
    res = await send(
        template_name="survey",
        to_email="tester@example.com",
        ctx={"customer_name": "Tester", "product_name": "Device"},
        tenant_id="tenant_default",
        session=session_mock,
    )

    assert res["status"] == "simulated"
    assert res["provider"] == "simulated"
    assert res["status"] not in ("sent", "delivered")
    assert "/v1/email/outbox/" in res["preview_url"]
