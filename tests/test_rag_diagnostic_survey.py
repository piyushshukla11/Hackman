"""
tests/test_rag_diagnostic_survey.py

Focused evaluation suite for PRISM's RAG-based diagnostic survey generation:
- Tenant and product isolation in evidence retrieval
- Relevant, representative quote selection, deduplication, and source ID preservation
- Grounded questions versus unsupported/hallucinated claims
- Empty clusters, missing specs, and insufficient evidence behavior
- Malformed Gemini JSON, timeouts, and category fallback templates
- PII exclusion before prompt formulation
- Consent gate and HMAC-signed expiring token verification
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import SecretStr

from prism_core.db.models import EmailOutbox, IssueCluster, RawReview, Survey
from prism_core.schemas.survey import (
    RetrievedEvidence,
    SurveyGenerationResult,
    SurveyQuestion,
    SurveyRetrievalContext,
)
from prism_core.survey import (
    generate_survey_token,
    get_survey_signing_secret,
    ingest_reply,
    send_survey_invite,
    verify_survey_token,
)
from prism_core.survey.generator import (
    CATEGORY_FALLBACK_TEMPLATES,
    SurveyGenerator,
    _clean_tokens,
    _is_near_duplicate,
    _is_substantive,
)


# ── 1. Tenant and Product Isolation in Retrieval ─────────────────────────────

def test_tenant_and_product_isolation_in_retrieval():
    """Verify that retrieval strictly isolates by tenant_id and product_id."""
    generator = SurveyGenerator()

    cluster = {
        "id": "clust_alpha_cool",
        "tenant_id": "tenant_alpha",
        "product_id": "prod_refrig_100",
        "feature": "cooling",
        "dominant_batch_id": "BATCH-2026-A",
        "version_label": "v1.2",
    }

    product_alpha = {
        "id": "prod_refrig_100",
        "tenant_id": "tenant_alpha",
        "name": "FrostFree Refrigerator",
        "category": "appliances",
        "specs": {"compressor": "inverter", "refrigerant": "R600a", "capacity": "320L"},
    }

    # Reviews: 1 valid for tenant_alpha, 1 from foreign tenant_beta, 1 from foreign product_headphone
    members = [
        {
            "id": "rev_valid_01",
            "review_id": "rev_valid_01",
            "tenant_id": "tenant_alpha",
            "product_id": "prod_refrig_100",
            "text": "The cooling compartment is barely cold and vegetables are spoiling rapidly.",
            "rating": 1.0,
            "channel": "amazon",
            "role": "exemplar",
        },
        {
            "id": "rev_foreign_tenant_02",
            "review_id": "rev_foreign_tenant_02",
            "tenant_id": "tenant_beta",  # CROSS-TENANT: MUST BE EXCLUDED
            "product_id": "prod_refrig_100",
            "text": "Tenant Beta confidential review: freezer cooling completely halted.",
            "rating": 1.0,
            "channel": "flipkart",
            "role": "member",
        },
        {
            "id": "rev_foreign_product_03",
            "review_id": "rev_foreign_product_03",
            "tenant_id": "tenant_alpha",
            "product_id": "prod_headphone_200",  # CROSS-PRODUCT: MUST BE EXCLUDED
            "text": "Headphone ear cushions are cracking after one week.",
            "rating": 2.0,
            "channel": "direct",
            "role": "member",
        },
    ]

    context = generator.retrieve_from_memory(
        cluster=cluster,
        product=product_alpha,
        members=members,
        tenant_id="tenant_alpha",
    )

    assert context.is_sufficient is True
    assert context.tenant_id == "tenant_alpha"
    assert context.product_id == "prod_refrig_100"
    assert context.specs["compressor"] == "inverter"

    # Only the matching review must be included
    evidence_ids = [e.review_id for e in context.evidence_items]
    assert evidence_ids == ["rev_valid_01"]
    assert "rev_foreign_tenant_02" not in evidence_ids
    assert "rev_foreign_product_03" not in evidence_ids

    # Cross-tenant query attempt on cluster must be rejected immediately
    foreign_query = generator.retrieve_from_memory(
        cluster=cluster,
        product=product_alpha,
        members=members,
        tenant_id="tenant_beta",
    )
    assert foreign_query.is_sufficient is False
    assert "does not belong to tenant" in (foreign_query.insufficient_reason or "")


# ── 2. Relevant, Representative Quotes and Source ID Preservation ────────────

def test_relevant_quote_deduplication_and_source_id_preservation():
    """Verify quote deduplication, substantive filtering, and source review_id preservation."""
    generator = SurveyGenerator()

    cluster = {
        "id": "clust_wash_motor",
        "tenant_id": "tenant_omega",
        "product_id": "prod_wash_300",
        "feature": "motor",
    }
    product = {
        "id": "prod_wash_300",
        "tenant_id": "tenant_omega",
        "name": "EcoWash Front Loader",
        "category": "appliances",
        "specs": {"motor_type": "direct_drive", "rpm": "1400"},
    }

    members = [
        {
            "review_id": "rev_substantive_01",
            "tenant_id": "tenant_omega",
            "product_id": "prod_wash_300",
            "text": "The direct drive motor emits a loud rhythmic grinding noise during the 1400 rpm spin cycle.",
            "rating": 1.5,
            "channel": "site_a",
            "role": "exemplar",
        },
        {
            "review_id": "rev_dupe_02",  # Near-duplicate of #1
            "tenant_id": "tenant_omega",
            "product_id": "prod_wash_300",
            "text": "The direct drive motor emits a loud rhythmic grinding noise during the spin cycle.",
            "rating": 1.0,
            "channel": "site_b",
            "role": "member",
        },
        {
            "review_id": "rev_too_short_03",  # Non-substantive (< 3 words)
            "tenant_id": "tenant_omega",
            "product_id": "prod_wash_300",
            "text": "Broke bad",
            "rating": 1.0,
            "channel": "site_c",
            "role": "member",
        },
        {
            "review_id": "rev_distinct_04",  # Distinct physical failure mode
            "tenant_id": "tenant_omega",
            "product_id": "prod_wash_300",
            "text": "Drum failed to spin and display gave error E04 after filling with water.",
            "rating": 1.0,
            "channel": "site_d",
            "role": "member",
        },
    ]

    context = generator.retrieve_from_memory(
        cluster=cluster,
        product=product,
        members=members,
        tenant_id="tenant_omega",
    )

    assert context.is_sufficient is True
    assert len(context.evidence_items) == 2

    # Verify exact review IDs and provenance preservation
    retrieved_ids = [e.review_id for e in context.evidence_items]
    assert retrieved_ids == ["rev_substantive_01", "rev_distinct_04"]
    assert "rev_dupe_02" not in retrieved_ids
    assert "rev_too_short_03" not in retrieved_ids

    # Roles preserved
    assert context.evidence_items[0].role == "exemplar"
    assert context.evidence_items[1].role == "member"


# ── 3. PII Exclusion in Retrieved Evidence ───────────────────────────────────

def test_pii_exclusion_in_retrieved_evidence():
    """Verify that emails, phone numbers, and order numbers are masked before prompt injection."""
    generator = SurveyGenerator()

    cluster = {"id": "c1", "tenant_id": "t1", "product_id": "p1", "feature": "door_hinge"}
    product = {"id": "p1", "tenant_id": "t1", "category": "appliances"}
    members = [
        {
            "review_id": "rev_pii_01",
            "tenant_id": "t1",
            "product_id": "p1",
            "text": "Please contact me at customer.vip@gmail.com or call +91-9876543210 regarding order ORD-884920. The door hinge snapped.",
            "rating": 1.0,
        }
    ]

    context = generator.retrieve_from_memory(cluster, product, members, tenant_id="t1")
    assert context.is_sufficient is True

    evidence_text = context.evidence_items[0].text
    assert "customer.vip@gmail.com" not in evidence_text
    assert "+91-9876543210" not in evidence_text
    assert "ORD-884920" not in evidence_text
    assert "[EMAIL_0]" in evidence_text
    assert "[PHONE_0]" in evidence_text
    assert "[ORDER_0]" in evidence_text


# ── 4. Grounded Questions versus Unsupported Claims ──────────────────────────

def test_grounded_questions_versus_unsupported_claims():
    """Verify question validation rejects assertive claims and ungrounded evidence references."""
    generator = SurveyGenerator()

    context = SurveyRetrievalContext(
        tenant_id="t1",
        product_id="p1",
        issue_id="c1",
        feature="battery",
        category="electronics",
        evidence_items=[
            RetrievedEvidence(review_id="rev_bat_01", text="Battery drops from 80% to 0% in 10 minutes."),
            RetrievedEvidence(review_id="rev_bat_02", text="Device shuts down without low battery warning."),
        ],
        specs={"battery_capacity_mah": "5000", "fast_charge": "65W"},
        dominant_batch_id="BAT-LOT-44",
    )

    # Valid grounded questions
    valid_raw = [
        {
            "question_id": "q1",
            "question_text": "Does the sudden battery shutdown happen only below a specific charge percentage?",
            "options": ["Below 20%", "Below 50%", "At any percentage randomly", "I'm not sure"],
            "evidence_refs": ["rev_bat_01", "rev_bat_02"],
            "rationale": "Isolates cell voltage collapse under load from BMS fuel-gauge calibration drift.",
        },
        {
            "question_id": "q2",
            "question_text": "When charging with the 65W fast charger, does the device casing become excessively hot?",
            "options": ["Normal warm charging", "Extremely hot to the touch", "Device halts charging with thermal alert", "I'm not sure"],
            "evidence_refs": ["fast_charge", "BAT-LOT-44"],
            "rationale": "Differentiates battery internal resistance spike from normal fast charge dissipation.",
        },
    ]

    is_valid, questions, err = generator.validate_questions(valid_raw, context)
    assert is_valid is True
    assert len(questions) == 2
    assert err is None
    assert questions[0].evidence_refs == ["rev_bat_01", "rev_bat_02"]

    # Test 1: Assertive ungrounded cause stated as fact
    assertive_raw = [
        {
            "question_id": "q1",
            "question_text": "Because the battery failed due to low-grade cathode materials, how long did it last?",
            "options": ["1 hour", "2 hours", "I'm not sure"],
            "evidence_refs": ["rev_bat_01"],
            "rationale": "Unverified assumption.",
        }
    ]
    is_valid_assertive, _, err_assertive = generator.validate_questions(assertive_raw, context)
    assert is_valid_assertive is False
    assert "asserts ungrounded cause as fact" in str(err_assertive)

    # Test 2: Hallucinated / invented evidence reference rejected (never filled in with arbitrary IDs)
    hallucinated_refs_raw = [
        {
            "question_id": "q1",
            "question_text": "Did the battery discharge faster when playing 3D video games?",
            "options": ["Yes, rapidly", "No difference", "I'm not sure"],
            "evidence_refs": ["rev_hallucinated_999", "ghost_spec"],  # NOT in context!
            "rationale": "Gaming discharge check.",
        }
    ]
    is_valid_hal, q_hal, err_hal = generator.validate_questions(hallucinated_refs_raw, context)
    assert is_valid_hal is False
    assert "ungrounded or invented evidence_ref" in str(err_hal)


# ── 5. Empty Cluster and Insufficient Evidence Behavior ──────────────────────

def test_empty_cluster_and_insufficient_evidence():
    """Verify explicit insufficient_evidence outcome when evidence is missing or non-substantive."""
    generator = SurveyGenerator()

    # Case A: Cluster has 0 members
    empty_cluster = {"id": "c_empty", "tenant_id": "t1", "product_id": "p1", "feature": "audio"}
    context_empty = generator.retrieve_from_memory(empty_cluster, None, [], tenant_id="t1")
    assert context_empty.is_sufficient is False
    assert "No representative customer review verbatims" in (context_empty.insufficient_reason or "")

    # Generation on insufficient context returns explicit insufficient_evidence status
    import asyncio
    res_empty = asyncio.run(generator.generate_diagnostic_survey(context_empty))
    assert res_empty.status == "insufficient_evidence"
    assert len(res_empty.questions) == 0
    assert res_empty.is_fallback is False

    # Case B: Cluster has only non-substantive (< 3 words) reviews
    short_members = [
        {"review_id": "r1", "tenant_id": "t1", "product_id": "p1", "text": "bad"},
        {"review_id": "r2", "tenant_id": "t1", "product_id": "p1", "text": "not good"},
    ]
    context_short = generator.retrieve_from_memory(empty_cluster, None, short_members, tenant_id="t1")
    assert context_short.is_sufficient is False

    res_short = asyncio.run(generator.generate_diagnostic_survey(context_short))
    assert res_short.status == "insufficient_evidence"
    assert len(res_short.questions) == 0


# ── 6. Missing Specs and Batch Details Graceful Handling ─────────────────────

def test_missing_specs_and_batch_details():
    """Verify generator functions cleanly when catalog specs, batch code, or version are null."""
    generator = SurveyGenerator()

    cluster = {
        "id": "c_nospec",
        "tenant_id": "t1",
        "product_id": "p_nospec",
        "feature": "water_dispenser",
        "dominant_batch_id": None,
        "version_label": None,
    }
    # Product with no specs
    product = {"id": "p_nospec", "tenant_id": "t1", "category": "appliances", "specs": None}
    members = [
        {
            "review_id": "rev_disp_01",
            "tenant_id": "t1",
            "product_id": "p_nospec",
            "text": "The water dispenser drips constantly after filling a glass and leaks onto the kitchen floor.",
            "rating": 1.0,
        }
    ]

    context = generator.retrieve_from_memory(cluster, product, members, tenant_id="t1")
    assert context.is_sufficient is True
    assert context.specs == {}
    assert context.dominant_batch_id is None

    # Fallback templates should generate valid questions without throwing NoneType errors
    fallback_qs = generator.get_category_fallback_questions("appliances", "water_dispenser", context)
    assert len(fallback_qs) == 3
    for q in fallback_qs:
        assert q.is_fallback is True
        assert "water dispenser" in q.question_text.lower()
        assert any("not sure" in opt.lower() for opt in q.options)


# ── 7. Malformed Gemini Output, Timeouts, and Fallback Templates ─────────────

def test_malformed_gemini_output_triggers_fallback_template():
    """Verify that malformed JSON, truncated lists, or invalid fields trigger calibrated fallback."""
    generator = SurveyGenerator()

    context = SurveyRetrievalContext(
        tenant_id="t1",
        product_id="p1",
        issue_id="c1",
        feature="compressor",
        category="appliances",
        evidence_items=[
            RetrievedEvidence(review_id="rev_01", text="Compressor clicking and buzzing loudly without cooling."),
        ],
    )

    # Test malformed payloads:
    # 1. Truncated / empty list
    is_valid, _, err = generator.validate_questions([], context)
    assert is_valid is False

    # 2. String instead of dict
    is_valid_str, _, _ = generator.validate_questions(["Not a dict"], context)  # type: ignore
    assert is_valid_str is False

    # 3. Missing options
    is_valid_no_opts, _, _ = generator.validate_questions(
        [{"question_id": "q1", "question_text": "Is the compressor cycling properly?"}], context
    )
    assert is_valid_no_opts is False

    # In all validation failures, generator produces category fallback questions
    fallback_qs = generator.get_category_fallback_questions(context.category, context.feature, context)
    assert len(fallback_qs) == 3
    for q in fallback_qs:
        assert q.is_fallback is True
        assert len(q.options) >= 3
        assert any("not sure" in opt.lower() for opt in q.options)
        assert q.evidence_refs == ["rev_01"]


# ── 8. Offline Mode and Gemini Fallback Execution ────────────────────────────

def test_offline_mode_generates_calibrated_category_fallback():
    """When GEMINI_KEY is absent or fallback enabled, generator safely returns fallback result."""
    import asyncio
    generator = SurveyGenerator()

    context = SurveyRetrievalContext(
        tenant_id="t_offline",
        product_id="p_headphone",
        issue_id="c_anc",
        feature="noise_cancellation",
        category="audio",
        evidence_items=[
            RetrievedEvidence(review_id="rev_anc_01", text="High-pitched whistling feedback when ANC is toggled on."),
            RetrievedEvidence(review_id="rev_anc_02", text="Active noise cancellation produces popping sounds in left ear."),
        ],
    )

    result: SurveyGenerationResult = asyncio.run(generator.generate_diagnostic_survey(context))

    assert result.status == "fallback"
    assert result.is_fallback is True
    assert len(result.questions) == 3

    for q in result.questions:
        assert q.is_fallback is True
        assert "noise cancellation" in q.question_text.lower()
        # Uncertainty option check
        assert any("not sure" in opt.lower() for opt in q.options)
        # Provenance check: evidence_refs points to real review IDs
        assert set(q.evidence_refs).issubset({"rev_anc_01", "rev_anc_02"})


# ── 9. Consent and HMAC Expiring Token Verification ──────────────────────────

def test_survey_token_generation_and_expiry_verification():
    """Verify HMAC token signing, tamper rejection, and consent gate."""
    secret = "production-survey-hmac-secret-994"

    token = generate_survey_token(survey_id="srv_live_44", tenant_id="tenant_gamma", secret=secret)
    assert isinstance(token, str) and len(token) > 20

    # 1. Valid token verification
    verified, srv_id, ten_id = verify_survey_token(token, secret=secret)
    assert verified is True
    assert srv_id == "srv_live_44"
    assert ten_id == "tenant_gamma"

    # 2. Tampered token verification fails
    tampered_token = token[:-6] + "xxxxxx"
    verified_tampered, _, _ = verify_survey_token(tampered_token, secret=secret)
    assert verified_tampered is False

    # 3. Wrong secret key verification fails
    verified_wrong_key, _, _ = verify_survey_token(token, secret="completely-wrong-secret")
    assert verified_wrong_key is False


# ── 10. Gemini Fewer Than 3 Questions Triggers Fallback ───────────────────────

@pytest.mark.asyncio
async def test_gemini_fewer_than_3_valid_questions_uses_category_fallback():
    """Verify that when Gemini returns fewer than 3 valid questions, category fallback is triggered."""
    generator = SurveyGenerator()

    context = SurveyRetrievalContext(
        tenant_id="tenant_gamma",
        product_id="prod_gamma_01",
        issue_id="issue_gamma_01",
        feature="compressor",
        category="appliances",
        evidence_items=[
            RetrievedEvidence(review_id="rev_01", text="Compressor vibrates loudly and stops cooling."),
            RetrievedEvidence(review_id="rev_02", text="Fridge compressor emits high heat."),
        ],
    )

    # Incomplete LLM output containing only 1 valid question
    incomplete_gemini_json = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": '[{"question_id": "q1", "question_text": "Does the compressor vibrate on startup?", "options": ["Yes immediately", "Only after 30 mins", "I\'m not sure"], "evidence_refs": ["rev_01"], "rationale": "Startup test."}]'
                }]
            }
        }]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value=incomplete_gemini_json)

    with patch.object(generator, "_get_api_key", return_value="fake_gemini_key"):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
            result = await generator.generate_diagnostic_survey(context)

    # Validates final count < 3 and triggers category fallback to return exactly 3 questions
    assert result.status == "fallback"
    assert result.is_fallback is True
    assert len(result.questions) == 3
    assert "expected exactly 3" in (result.fallback_reason or "")


# ── 11. Fallback Questions Specific Evidence Provenance ───────────────────────

def test_fallback_questions_evidence_provenance_and_empty_list():
    """Verify fallback template questions attach evidence_refs only if specifically supported."""
    generator = SurveyGenerator()

    # Evidence only mentions cooling, nothing about power reset or heat
    context = SurveyRetrievalContext(
        tenant_id="tenant_p",
        product_id="prod_p1",
        issue_id="issue_p1",
        feature="water_dispenser",
        category="appliances",
        evidence_items=[
            RetrievedEvidence(review_id="rev_spec_01", text="The water dispenser has a loose latch mechanism."),
        ],
    )

    fallback_qs = generator.get_category_fallback_questions("appliances", "water_dispenser", context)
    assert len(fallback_qs) == 3

    for q in fallback_qs:
        assert q.is_fallback is True
        assert "Category template" in q.rationale
        # If review mentions the feature, it is cited; otherwise evidence_refs is an empty list
        if "water dispenser" in q.question_text.lower():
            assert q.evidence_refs == ["rev_spec_01"]
        else:
            assert q.evidence_refs == []


# ── 12. Token Expiry, Cross-Tenant Rejection, and Production Secret ───────────

def test_token_expiry_and_cross_tenant_rejection():
    """Verify expired tokens and cross-tenant access are strictly rejected."""
    secret = "secure-test-signing-secret-key-32chars"

    # Expired token (7 days in the past)
    expired_token = generate_survey_token(
        survey_id="srv_exp_01",
        tenant_id="tenant_x",
        secret=secret,
        recipient_id="cust_01",
        expires_in_seconds=-3600,
    )
    is_valid, _, _ = verify_survey_token(expired_token, secret=secret)
    assert is_valid is False

    # Cross-tenant scoping rejection
    valid_token = generate_survey_token(
        survey_id="srv_valid_01",
        tenant_id="tenant_x",
        secret=secret,
        recipient_id="cust_01",
        expires_in_seconds=3600,
    )
    is_valid_cross, _, _ = verify_survey_token(valid_token, secret=secret, expected_tenant_id="tenant_y")
    assert is_valid_cross is False

    # Recipient scoping rejection
    is_valid_recip, _, _ = verify_survey_token(valid_token, secret=secret, expected_recipient_id="cust_other")
    assert is_valid_recip is False

    # Production signing secret check
    with patch("prism_core.survey.get_settings") as mock_settings:
        mock_obj = MagicMock()
        mock_obj.environment = "production"
        mock_obj.secret_key = SecretStr("short")
        mock_settings.return_value = mock_obj
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Production survey token signing secret"):
                get_survey_signing_secret()


# ── 13. Consented Email Delivery Gate and Idempotency ─────────────────────────

@pytest.mark.asyncio
async def test_consented_email_delivery_scenarios():
    """Verify consent gates (missing, false, true), recipient mismatch, and duplicate retries."""
    import hashlib

    # Case 1: Consent missing / false
    survey = Survey(
        id="srv_test_01",
        tenant_id="tenant_mail",
        issue_id="issue_01",
        review_id="raw_rev_unconsented",
        token_hash="hash01",
        questions=[{"question_id": "q1", "question_text": "Test"}],
    )

    unconsented_raw = RawReview(
        id="raw_rev_unconsented",
        tenant_id="tenant_mail",
        source_id="widget",
        idempotency_key="idem_01",
        payload={
            "contact": {"email": "user@example.com", "consent_followup": False},
        },
    )

    mock_sess = MagicMock()
    mock_sess.get = AsyncMock(return_value=unconsented_raw)

    res_unconsented = await send_survey_invite(
        survey=survey,
        raw_token="tok1",
        to_email="user@example.com",
        tenant_id="tenant_mail",
        session=mock_sess,
    )
    assert res_unconsented["status"] == "skipped"
    assert res_unconsented["reason"] == "consent_missing"
    assert "user@example.com" not in str(res_unconsented)

    # Case 2: Recipient mismatch (caller supplies different address than consented)
    consented_raw = RawReview(
        id="raw_rev_consented",
        tenant_id="tenant_mail",
        source_id="widget",
        idempotency_key="idem_02",
        payload={
            "contact": {"email": "legit@example.com", "consent_followup": True},
        },
    )
    mock_sess.get = AsyncMock(return_value=consented_raw)

    res_mismatch = await send_survey_invite(
        survey=survey,
        raw_token="tok1",
        to_email="attacker@evil.com",
        tenant_id="tenant_mail",
        session=mock_sess,
    )
    assert res_mismatch["status"] == "skipped"
    assert res_mismatch["reason"] == "recipient_mismatch"
    assert "attacker@evil.com" not in str(res_mismatch)

    # Case 3: Duplicate-send retries (already dispatched)
    to_hash = hashlib.sha256("legit@example.com".encode("utf-8")).hexdigest()
    existing_outbox = EmailOutbox(
        id="outbox_exist_01",
        tenant_id="tenant_mail",
        template="survey",
        to_hash=to_hash,
        payload={"survey_id": survey.id, "to_email": "legit@example.com"},
        status="sent",
    )

    mock_exec_res = MagicMock()
    mock_exec_res.scalars.return_value.first.return_value = existing_outbox
    mock_sess.execute = AsyncMock(return_value=mock_exec_res)

    res_dup = await send_survey_invite(
        survey=survey,
        raw_token="tok1",
        to_email="legit@example.com",
        tenant_id="tenant_mail",
        session=mock_sess,
    )
    assert res_dup["status"] == "duplicate_skipped"
    assert res_dup["reason"] == "already_dispatched"


# ── 14. Response Loop and Bounded SurveyDelta Updates ─────────────────────────

def _build_test_survey_and_cluster(
    initial_confidence: float = 0.60,
    survey_id: str = "srv_loop_01",
    issue_id: str = "issue_loop_01",
    secret: str = "testing-secret-key-32-chars-minimum-abc12345",
):
    import hashlib
    from datetime import datetime, timedelta, timezone

    raw_token = generate_survey_token(survey_id, "tenant_loop", secret=secret)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    questions = [
        {
            "question_id": "q1",
            "question_text": "When operating the unit, does the issue occur immediately upon startup?",
            "options": [
                "Immediately upon startup / power-on",
                "Device operates normally",
                "Not applicable",
                "I'm not sure",
            ],
        },
        {
            "question_id": "q2",
            "question_text": "Have you observed any unusual sensory indicators such as heat or clicking?",
            "options": [
                "Noticeable excess heat on the external casing",
                "No unusual sound, heat, or moisture observed",
                "Did not observe or check",
                "I'm not sure",
            ],
        },
        {
            "question_id": "q3",
            "question_text": "Did power cycling or adjusting settings alter the issue behavior?",
            "options": [
                "Had no effect whatsoever on the issue",
                "Works fine / resolved completely",
                "I did not attempt a power reset",
                "I'm not sure",
            ],
        },
    ]

    survey = Survey(
        id=survey_id,
        tenant_id="tenant_loop",
        issue_id=issue_id,
        review_id="rev_loop_01",
        token_hash=token_hash,
        questions=questions,
        status="sent",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    cluster = IssueCluster(
        id=issue_id,
        tenant_id="tenant_loop",
        product_id="prod_01",
        feature="thermal",
        confidence=initial_confidence,
    )

    mock_sess = MagicMock()
    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = survey
    mock_sess.execute = AsyncMock(return_value=mock_exec)
    mock_sess.get = AsyncMock(return_value=cluster)
    mock_sess.add = MagicMock()
    mock_sess.flush = AsyncMock()

    return survey, cluster, raw_token, secret, mock_sess


@pytest.mark.asyncio
async def test_survey_confirming_responses_bounded_delta():
    """Verify confirming answers calculate a positive, bounded confidence delta (+0.20)."""
    survey, cluster, raw_token, secret, mock_sess = _build_test_survey_and_cluster(initial_confidence=0.60)

    confirming_answers = {
        "q1": "Immediately upon startup / power-on",
        "q2": "Noticeable excess heat on the external casing",
        "q3": "Had no effect whatsoever on the issue",
    }

    with patch("prism_core.survey.emit", new=AsyncMock()):
        res = await ingest_reply(raw_token, confirming_answers, secret=secret, session=mock_sess)

    assert res["status"] == "success"
    assert res["confidence_delta"] == 0.20
    assert cluster.confidence == 0.80  # 0.60 + 0.20
    assert survey.status == "answered"
    assert res["signals"] == {"q1": "confirm", "q2": "confirm", "q3": "confirm"}
    assert "confirmed failure symptoms" in res["summary"]


@pytest.mark.asyncio
async def test_survey_denying_responses_bounded_delta():
    """Verify denying answers calculate a negative, bounded confidence delta (-0.20)."""
    survey, cluster, raw_token, secret, mock_sess = _build_test_survey_and_cluster(initial_confidence=0.60)

    denying_answers = {
        "q1": "Device operates normally",
        "q2": "No unusual sound, heat, or moisture observed",
        "q3": "Works fine / resolved completely",
    }

    with patch("prism_core.survey.emit", new=AsyncMock()):
        res = await ingest_reply(raw_token, denying_answers, secret=secret, session=mock_sess)

    assert res["status"] == "success"
    assert res["confidence_delta"] == -0.20
    assert cluster.confidence == 0.40  # 0.60 - 0.20
    assert survey.status == "answered"
    assert res["signals"] == {"q1": "deny", "q2": "deny", "q3": "deny"}
    assert "absent" in res["summary"]


@pytest.mark.asyncio
async def test_survey_mixed_responses_delta():
    """Verify mixed answers (confirm + deny + neutral) correctly balance out to 0.00 delta."""
    survey, cluster, raw_token, secret, mock_sess = _build_test_survey_and_cluster(initial_confidence=0.60)

    mixed_answers = {
        "q1": "Immediately upon startup / power-on",  # confirm (+0.067)
        "q2": "No unusual sound, heat, or moisture observed",  # deny (-0.067)
        "q3": "I did not attempt a power reset",  # neutral (0.0)
    }

    with patch("prism_core.survey.emit", new=AsyncMock()):
        res = await ingest_reply(raw_token, mixed_answers, secret=secret, session=mock_sess)

    assert res["status"] == "success"
    assert res["confidence_delta"] == 0.00
    assert cluster.confidence == 0.60  # unchanged
    assert res["signals"] == {"q1": "confirm", "q2": "deny", "q3": "neutral"}
    assert "mixed" in res["summary"].lower()


@pytest.mark.asyncio
async def test_survey_neutral_responses_no_confidence_change():
    """Verify neutral answers have zero effect on confidence."""
    survey, cluster, raw_token, secret, mock_sess = _build_test_survey_and_cluster(initial_confidence=0.60)

    neutral_answers = {
        "q1": "Not applicable",
        "q2": "Did not observe or check",
        "q3": "I did not attempt a power reset",
    }

    with patch("prism_core.survey.emit", new=AsyncMock()):
        res = await ingest_reply(raw_token, neutral_answers, secret=secret, session=mock_sess)

    assert res["status"] == "success"
    assert res["confidence_delta"] == 0.00
    assert cluster.confidence == 0.60
    assert res["signals"] == {"q1": "neutral", "q2": "neutral", "q3": "neutral"}
    assert "neutral or unclear" in res["summary"].lower()


@pytest.mark.asyncio
async def test_survey_unclear_responses_no_confidence_change():
    """Verify unclear / uncertain answers have zero effect on confidence."""
    survey, cluster, raw_token, secret, mock_sess = _build_test_survey_and_cluster(initial_confidence=0.60)

    unclear_answers = {
        "q1": "I'm not sure",
        "q2": "I'm not sure",
        "q3": "I'm not sure",
    }

    with patch("prism_core.survey.emit", new=AsyncMock()):
        res = await ingest_reply(raw_token, unclear_answers, secret=secret, session=mock_sess)

    assert res["status"] == "success"
    assert res["confidence_delta"] == 0.00
    assert cluster.confidence == 0.60
    assert res["signals"] == {"q1": "unclear", "q2": "unclear", "q3": "unclear"}
    assert "neutral or unclear" in res["summary"].lower()


@pytest.mark.asyncio
async def test_survey_confidence_boundary_clamping():
    """Verify confidence strictly stays clamped within [0.0, 1.0] across extreme deltas."""
    # Upper bound: 0.95 initial confidence + 0.20 delta -> clamped at 1.0
    survey_high, cluster_high, tok_high, sec_high, sess_high = _build_test_survey_and_cluster(
        initial_confidence=0.95, survey_id="srv_high"
    )
    confirming = {
        "q1": "Immediately upon startup / power-on",
        "q2": "Noticeable excess heat on the external casing",
        "q3": "Had no effect whatsoever on the issue",
    }
    with patch("prism_core.survey.emit", new=AsyncMock()):
        res_high = await ingest_reply(tok_high, confirming, secret=sec_high, session=sess_high)
    assert res_high["confidence_delta"] == 0.20
    assert cluster_high.confidence == 1.0  # Clamped from 1.15 to 1.0!
    assert res_high["new_confidence"] == 1.0

    # Lower bound: 0.05 initial confidence - 0.20 delta -> clamped at 0.0
    survey_low, cluster_low, tok_low, sec_low, sess_low = _build_test_survey_and_cluster(
        initial_confidence=0.05, survey_id="srv_low"
    )
    denying = {
        "q1": "Device operates normally",
        "q2": "No unusual sound, heat, or moisture observed",
        "q3": "Works fine / resolved completely",
    }
    with patch("prism_core.survey.emit", new=AsyncMock()):
        res_low = await ingest_reply(tok_low, denying, secret=sec_low, session=sess_low)
    assert res_low["confidence_delta"] == -0.20
    assert cluster_low.confidence == 0.0  # Clamped from -0.15 to 0.0!
    assert res_low["new_confidence"] == 0.0


@pytest.mark.asyncio
async def test_survey_rejects_invalid_answers_and_duplicate_submissions():
    """Verify rejection of invalid options, unknown keys, empty answers, and duplicate submissions."""
    survey, cluster, raw_token, secret, mock_sess = _build_test_survey_and_cluster(initial_confidence=0.60)

    with patch("prism_core.survey.emit", new=AsyncMock()):
        # 1. Reject empty answers dict
        with pytest.raises(ValueError, match="answers cannot be empty"):
            await ingest_reply(raw_token, {}, secret=secret, session=mock_sess)
        assert cluster.confidence == 0.60

        # 2. Reject answers with only whitespace
        with pytest.raises(ValueError, match="answers cannot be empty"):
            await ingest_reply(raw_token, {"q1": "   "}, secret=secret, session=mock_sess)
        assert cluster.confidence == 0.60

        # 3. Reject unknown question keys
        with pytest.raises(ValueError, match="Invalid answer key: 'q_fake'"):
            await ingest_reply(raw_token, {"q_fake": "Immediately upon startup / power-on"}, secret=secret, session=mock_sess)
        assert cluster.confidence == 0.60

        # 4. Reject answer not matching question's allowed options
        with pytest.raises(ValueError, match="is not a valid option"):
            await ingest_reply(
                raw_token,
                {"q1": "Hacked or hallucinated answer text"},
                secret=secret,
                session=mock_sess,
            )
        assert cluster.confidence == 0.60

        # 5. Valid submission succeeds
        valid_ans = {
            "q1": "Immediately upon startup / power-on",
            "q2": "Noticeable excess heat on the external casing",
            "q3": "Had no effect whatsoever on the issue",
        }
        res_valid = await ingest_reply(raw_token, valid_ans, secret=secret, session=mock_sess)
        assert res_valid["status"] == "success"
        assert survey.status == "answered"

        # 6. Duplicate submission is strictly rejected
        with pytest.raises(ValueError, match="already been submitted"):
            await ingest_reply(raw_token, valid_ans, secret=secret, session=mock_sess)


@pytest.mark.asyncio
async def test_simulated_outbox_labeled_simulated_never_sent_or_delivered():
    """Verify simulated outbox messages are strictly labeled 'simulated', never 'sent' or 'delivered'."""
    from prism_core.mail import send

    session_mock = MagicMock()
    session_mock.add = MagicMock()
    session_mock.flush = AsyncMock()

    ctx = {
        "customer_name": "QA Lead",
        "product_name": "Smart Thermostat Pro",
        "feature_name": "Sensor Calibration",
        "survey_url": "https://prism.app/v1/survey/sim_token_123",
        "survey_id": "srv_sim_01",
    }

    # Dispatch email using the simulated outbox provider (default test environment)
    res = await send(
        template_name="survey",
        to_email="quality.lead@company.com",
        ctx=ctx,
        tenant_id="tenant_sim_test",
        session=session_mock,
    )

    # Must be labeled 'simulated'
    assert res["status"] == "simulated"
    assert res["provider"] == "simulated"
    assert res["status"] not in ("sent", "delivered")
    assert "sim_" in res["provider_id"]
    assert res["to_email"] == "quality.lead@company.com"
    assert "/v1/email/outbox/" in res["preview_url"]

    # Verify outbox entity passed to DB session is also labeled 'simulated'
    assert session_mock.add.called
    outbox_entry = session_mock.add.call_args[0][0]
    assert outbox_entry.status == "simulated"
    assert outbox_entry.status not in ("sent", "delivered")
    assert outbox_entry.payload.get("survey_id") == "srv_sim_01"


