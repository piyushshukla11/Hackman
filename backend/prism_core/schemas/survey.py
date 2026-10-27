"""
prism_core/schemas/survey.py

Pydantic v2 schemas for RAG diagnostic survey generation:
- Evidence retrieval context (masked verbatims, product specs, batch/version)
- Structured diagnostic questions with evidence references and rationales
- Diagnostic survey generation outcomes (success, fallback, insufficient_evidence)
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class RetrievedEvidence(BaseModel):
    """A representative customer verbatim quote preserved with provenance."""
    review_id: str
    text: str = Field(..., description="Masked customer verbatim review quote")
    rating: float | None = None
    channel: str | None = None
    role: str = "member"


class SurveyRetrievalContext(BaseModel):
    """Context assembled for RAG diagnostic question drafting."""
    tenant_id: str
    product_id: str
    issue_id: str
    feature: str
    category: str | None = None
    evidence_items: list[RetrievedEvidence] = Field(default_factory=list)
    specs: dict[str, Any] = Field(default_factory=dict)
    dominant_batch_id: str | None = None
    version_label: str | None = None
    is_sufficient: bool = True
    insufficient_reason: str | None = None
    target_question_count: int = Field(default=3, description="Target number of diagnostic questions to generate (default 3, 6-7 when requested)")
    rag_memory_trace: dict[str, Any] = Field(default_factory=dict, description="Trace of simulation memory consulted")



class SurveyQuestion(BaseModel):
    """A single diagnostic multiple-choice question isolating engineering failure modes."""
    question_id: str
    question_text: str
    options: list[str] = Field(..., min_length=2)
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Source review IDs or specification keys grounding this question",
    )
    rationale: str = Field(
        default="",
        description="Engineering justification for how this question isolates the failure mode",
    )
    is_fallback: bool = Field(
        default=False,
        description="True if generated from category-calibrated fallback template",
    )
    processing_note: str = Field(
        default="",
        description="Trace of how simulation memory or engineering spec was evaluated",
    )
    grounded_data_source: str = Field(
        default="",
        description="Simulation platform, review ID, or hardware spec key grounding this question",
    )


class SurveyGenerationResult(BaseModel):
    """Result of RAG diagnostic question generation and validation."""
    status: Literal["success", "insufficient_evidence", "fallback"]
    questions: list[SurveyQuestion] = Field(default_factory=list)
    evidence_context: list[RetrievedEvidence] = Field(default_factory=list)
    fallback_reason: str | None = None
    is_fallback: bool = False
    rag_processing_trace: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution trace detailing simulation memory chunks, specs, and clusters utilized",
    )

