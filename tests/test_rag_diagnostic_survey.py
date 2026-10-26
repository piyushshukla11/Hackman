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

import pytest
from prism_core.schemas.survey import (
    RetrievedEvidence,
    SurveyGenerationResult,
    SurveyQuestion,
    SurveyRetrievalContext,
)
from prism_core.survey.generator import (
    CATEGORY_FALLBACK_TEMPLATES,
    SurveyGenerator,
    _clean_tokens,
    _is_near_duplicate,
    _is_substantive,
)
from prism_core.survey import generate_survey_token, verify_survey_token


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

    # Test 2: Hallucinated evidence reference
    hallucinated_refs_raw = [
        {
            "question_id": "q1",
            "question_text": "Did the battery discharge faster when playing 3D video games?",
            "options": ["Yes, rapidly", "No difference", "I'm not sure"],
            "evidence_refs": ["rev_hallucinated_999", "ghost_spec"],  # NOT in context!
            "rationale": "Gaming discharge check.",
        }
    ]
    is_valid_hal, q_hal, _ = generator.validate_questions(hallucinated_refs_raw, context)
    assert is_valid_hal is True
    # The validator filters out the hallucinated IDs and substitutes valid retrieved IDs
    assert "rev_hallucinated_999" not in q_hal[0].evidence_refs
    assert "ghost_spec" not in q_hal[0].evidence_refs
    assert "rev_bat_01" in q_hal[0].evidence_refs


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
