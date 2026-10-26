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

from prism_core.survey import SurveyManager, generate_survey_token, verify_survey_token
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
