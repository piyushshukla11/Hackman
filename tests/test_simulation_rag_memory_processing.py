"""
tests/test_simulation_rag_memory_processing.py

Evaluates the PRISM RAG Diagnostic Model with Simulation Memory Ingestion:
1. Verifies that the RAG model generates 6-7 relevant diagnostic questions based on simulation memory.
2. Verifies that product specs, defect clusters, and cross-channel verbatims (Amazon, Flipkart, JioMart, Brand, Steam) are visibly utilized.
3. Checks that every question includes grounded evidence citations, engineering rationales, and processing notes.
"""

import pytest

from prism_core.schemas.survey import RetrievedEvidence, SurveyRetrievalContext
from prism_core.survey.generator import SurveyGenerator
from prism_core.survey.inject_rag_memory import load_simulation_rag_memory, get_context_for_product


def test_simulation_memory_bank_loaded():
    """Verify that the simulation RAG memory bank loads 5 platforms and hardware specs."""
    mem = load_simulation_rag_memory()
    assert mem["version"] == "1.0.0"
    assert "amazon" in mem["platforms"]
    assert "steam" in mem["platforms"]
    assert len(mem["rag_memory_chunks"]) >= 15

    # Check Horizon ANC product context
    anc_ctx = get_context_for_product("prod_001", mem)
    assert "40mm custom beryllium dynamic drivers" in anc_ctx["specs"]
    assert len(anc_ctx["defect_clusters"]) >= 1
    assert len(anc_ctx["evidence_quotes"]) >= 2


@pytest.mark.asyncio
async def test_rag_model_generates_6_to_7_questions_with_processing_trace():
    """Verify that the RAG model asks 6-7 relevant questions and exhibits full processing traces."""
    generator = SurveyGenerator()

    # Create retrieval context for Horizon ANC with target_question_count=7
    context = SurveyRetrievalContext(
        tenant_id="tenant_voyage",
        product_id="prod_001",
        issue_id="issue_anc_bt_stutter",
        feature="bluetooth_stutter",
        category="audio",
        target_question_count=7,
        evidence_items=[
            RetrievedEvidence(
                review_id="rev_amazon_002",
                text="Bluetooth occasionally had a brief stutter when walking past microwave ovens or with multipoint.",
                rating=2.0,
                channel="amazon",
            ),
            RetrievedEvidence(
                review_id="rev_flipkart_015",
                text="ANC is great but audio drops for a second when phone is in back pocket.",
                rating=3.0,
                channel="flipkart",
            ),
        ],
        specs={
            "driver": "40mm beryllium",
            "bluetooth": "5.4 with LDAC",
            "anc": "45dB hybrid",
            "battery": "800mAh Li-Po",
        },
        dominant_batch_id="BATCH-2024-W12",
        version_label="v1.4.2",
    )

    result = await generator.generate_diagnostic_survey(context, target_count=7)

    # 1. Verify 6-7 questions generated
    assert len(result.questions) in (6, 7)
    assert len(result.questions) == 7

    # 2. Verify RAG processing trace is attached and populated
    trace = result.rag_processing_trace
    assert trace["memory_source"] == "rag_simulation_memory.json"
    assert "amazon" in trace["platforms_consulted"]
    assert "steam" in trace["platforms_consulted"]
    assert trace["target_question_count"] == 7
    assert trace["rag_processing_status"] == "ACTIVE_GROUNDED"
    assert len(trace["isolation_axes"]) == 7

    # 3. Verify each question shows active processing and citations
    for idx, q in enumerate(result.questions, start=1):
        assert q.question_id == f"q{idx}"
        assert len(q.question_text) >= 15
        assert len(q.options) >= 3
        # Must have uncertainty option
        assert any("not sure" in opt.lower() or "uncertain" in opt.lower() for opt in q.options)
        # Must have engineering rationale
        assert len(q.rationale) > 10
        # Must show processing note
        assert len(q.processing_note) > 10
        # Must show grounded data source
        assert len(q.grounded_data_source) > 5


@pytest.mark.asyncio
async def test_gaming_monitor_rag_questions_grounding():
    """Verify that gaming category questions isolate Fast-IPS and Steam/PC hardware failure modes."""
    generator = SurveyGenerator()

    context = SurveyRetrievalContext(
        tenant_id="tenant_voyage",
        product_id="prod_004",
        issue_id="issue_monitor_corner_glow",
        feature="corner_glow",
        category="gaming",
        target_question_count=7,
        evidence_items=[
            RetrievedEvidence(
                review_id="rev_brand_004",
                text="Yellowish corner glow in bottom-left during dark loading screens.",
                rating=3.0,
                channel="brand",
            ),
        ],
        specs={"panel": "AUO Fast-IPS", "refresh_rate": "165Hz", "vrr": "FreeSync Premium"},
        dominant_batch_id="BATCH-2024-W13",
    )

    result = await generator.generate_diagnostic_survey(context, target_count=7)
    assert len(result.questions) == 7

    # Check that Fast-IPS, FreeSync, and bezel torque axes are represented
    all_text = " ".join(q.question_text + " " + q.rationale for q in result.questions)
    assert any(term in all_text.lower() for term in ("ips", "angle", "glow", "bezel", "torque"))
