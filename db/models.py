"""
db/models.py

All SQLAlchemy 2.0 multi-tenant declarative models for PRISM.
Every model carries tenant_id and created_at via TenantMixin.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base, TenantMixin

# Safe pgvector import with fallback for environments where pgvector binary isn't pre-installed
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy.types import UserDefinedType

    class Vector(UserDefinedType):  # type: ignore[no-redef]
        def __init__(self, dim: int):
            self.dim = dim

        def get_col_spec(self, **kw: Any) -> str:
            return f"vector({self.dim})"


JSONType = JSONB().with_variant(JSON, "sqlite")


def gen_uuid() -> str:
    """Generate a clean string UUID4."""
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# 1. Auth & Users
# ─────────────────────────────────────────────────────────────────────────────

class User(Base, TenantMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member")  # admin | member
    role_title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # e.g. "Senior QA Lead"
    selected_views: Mapped[Optional[list[str]]] = mapped_column(JSONType, default=list)  # personalized dashboard views
    has_completed_onboarding: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )


class APIKey(Base, TenantMixin):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="admin")
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Catalog & Taxonomy
# ─────────────────────────────────────────────────────────────────────────────

class FeatureTaxonomy(Base, TenantMixin):
    __tablename__ = "feature_taxonomies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    features: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class Product(Base, TenantMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    taxonomy_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("feature_taxonomies.id"), nullable=True)
    custom_features: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)  # Up to 15 company custom features
    specs: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)  # Technical specifications for RAG context

    versions: Mapped[List["ProductVersion"]] = relationship("ProductVersion", back_populates="product", cascade="all, delete-orphan")
    batches: Mapped[List["Batch"]] = relationship("Batch", back_populates="product", cascade="all, delete-orphan")


class ProductVersion(Base, TenantMixin):
    __tablename__ = "product_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="versions")


class Modification(Base, TenantMixin):
    __tablename__ = "modifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    from_version: Mapped[str] = mapped_column(String(64), nullable=False)
    to_version: Mapped[str] = mapped_column(String(64), nullable=False)
    change_note: Mapped[str] = mapped_column(Text, nullable=False)
    target_feature: Mapped[str] = mapped_column(String(128), nullable=False)
    target_issue_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Batch(Base, TenantMixin):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    version_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("product_versions.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mfg_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    mfg_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ship_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ship_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warehouse: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="batches")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Ingest & Sources
# ─────────────────────────────────────────────────────────────────────────────

class Source(Base, TenantMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    cursor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SourceHealth(Base, TenantMixin):
    __tablename__ = "source_health"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("sources.id"), nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    status: Mapped[str] = mapped_column(String(32), default="healthy")
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lag_seconds: Mapped[int] = mapped_column(Integer, default=0)
    items_24h: Mapped[int] = mapped_column(Integer, default=0)
    expected_24h: Mapped[int] = mapped_column(Integer, default=0)
    error_rate: Mapped[float] = mapped_column(Float, default=0.0)
    schema_drift: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class RawReview(Base, TenantMixin):
    __tablename__ = "raw_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("sources.id"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), default="review")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Canonical Reviews & Trust
# ─────────────────────────────────────────────────────────────────────────────

class Review(Base, TenantMixin):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    raw_id: Mapped[str] = mapped_column(String(64), ForeignKey("raw_reviews.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("sources.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    rating_raw: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rating_scale: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    text_original: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lang: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    script: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    dispatch_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warehouse: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    seller: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    author_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    media: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)

    # Batch and Version Inference
    batch_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("batches.id"), nullable=True, index=True)
    batch_method: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    batch_conf: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    version_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("product_versions.id"), nullable=True, index=True)

    # Trust Cascade
    text_status: Mapped[str] = mapped_column(String(32), default="accepted")
    rating_status: Mapped[str] = mapped_column(String(32), default="counted")
    trust_score: Mapped[float] = mapped_column(Float, default=1.0)

    # Ambiguity
    ambiguity: Mapped[str] = mapped_column(String(32), default="none")
    ambiguity_mult: Mapped[float] = mapped_column(Float, default=1.0)

    # 384-d vector embedding
    embedding = mapped_column(Vector(384), nullable=True)

    # Version tracking for idempotency
    stage_versions: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)

    __table_args__ = (
        Index("ix_reviews_tenant_product_reviewed", "tenant_id", "product_id", "reviewed_at"),
        Index("ix_reviews_embedding_hnsw", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class ReviewFeature(Base, TenantMixin):
    __tablename__ = "review_features"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    review_id: Mapped[str] = mapped_column(String(64), ForeignKey("reviews.id"), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    polarity: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    ambiguity: Mapped[str] = mapped_column(String(32), default="none")
    sentence_idx: Mapped[int] = mapped_column(Integer, default=0)
    anchor_sim: Mapped[float] = mapped_column(Float, default=0.0)


class TrustGateLog(Base, TenantMixin):
    __tablename__ = "trust_gate_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    review_id: Mapped[str] = mapped_column(String(64), ForeignKey("reviews.id"), nullable=False, index=True)
    gate: Mapped[str] = mapped_column(String(8), nullable=False)
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Diagnosis, Issue Graph & Metrics
# ─────────────────────────────────────────────────────────────────────────────

class GraphEdge(Base, TenantMixin):
    __tablename__ = "graph_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    src_review_id: Mapped[str] = mapped_column(String(64), ForeignKey("reviews.id"), nullable=False, index=True)
    dst_review_id: Mapped[str] = mapped_column(String(64), ForeignKey("reviews.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(128), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)


class IssueCluster(Base, TenantMixin):
    __tablename__ = "issue_clusters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    polarity: Mapped[str] = mapped_column(String(16), default="neg")
    issue_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_parts: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    first_seen: Mapped[date] = mapped_column(Date, nullable=False)
    last_seen: Mapped[date] = mapped_column(Date, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0)
    channels: Mapped[dict[str, int]] = mapped_column(JSONType, default=dict)
    batches: Mapped[dict[str, float]] = mapped_column(JSONType, default=dict)
    versions: Mapped[list[str]] = mapped_column(JSONType, default=list)

    defect_concentration: Mapped[float] = mapped_column(Float, default=0.0)
    dominant_batch_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("batches.id"), nullable=True)
    p_value: Mapped[float] = mapped_column(Float, default=1.0)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(32), default="open")


class ClusterMember(Base, TenantMixin):
    __tablename__ = "cluster_members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    cluster_id: Mapped[str] = mapped_column(String(64), ForeignKey("issue_clusters.id"), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(String(64), ForeignKey("reviews.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), default="member")


class MetricRollup(Base, TenantMixin):
    __tablename__ = "metric_rollups"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    week: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    n_reviews: Mapped[int] = mapped_column(Integer, default=0)
    n_neg: Mapped[int] = mapped_column(Integer, default=0)
    n_pos: Mapped[int] = mapped_column(Integer, default=0)
    rating_w_sum: Mapped[float] = mapped_column(Float, default=0.0)
    rating_w: Mapped[float] = mapped_column(Float, default=0.0)
    rating_n_all: Mapped[int] = mapped_column(Integer, default=0)
    rating_sum_all: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (
        Index("ix_metric_rollups_lookup", "tenant_id", "product_id", "feature", "week"),
    )


class TrendPoint(Base, TenantMixin):
    __tablename__ = "trend_points"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    window: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    n: Mapped[int] = mapped_column(Integer, default=0)
    neg_rate: Mapped[float] = mapped_column(Float, default=0.0)
    neg_ci_low: Mapped[float] = mapped_column(Float, default=0.0)
    neg_ci_high: Mapped[float] = mapped_column(Float, default=0.0)
    rating_mean_trusted: Mapped[float] = mapped_column(Float, default=0.0)
    rating_mean_all: Mapped[float] = mapped_column(Float, default=0.0)
    pattern: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Action, Surveys & Ops
# ─────────────────────────────────────────────────────────────────────────────

class SeriousComplaint(Base, TenantMixin):
    __tablename__ = "serious_complaints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    review_id: Mapped[str] = mapped_column(String(64), ForeignKey("reviews.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="high")
    urgency: Mapped[str] = mapped_column(String(16), default="high")
    status: Mapped[str] = mapped_column(String(32), default="open")
    alerted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Survey(Base, TenantMixin):
    __tablename__ = "surveys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    issue_id: Mapped[str] = mapped_column(String(64), ForeignKey("issue_clusters.id"), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(String(64), ForeignKey("reviews.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(32), default="sent")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SurveyResponse(Base, TenantMixin):
    __tablename__ = "survey_responses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    survey_id: Mapped[str] = mapped_column(String(64), ForeignKey("surveys.id"), nullable=False, index=True)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_delta: Mapped[float] = mapped_column(Float, default=0.0)


class EmailOutbox(Base, TenantMixin):
    __tablename__ = "email_outbox"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    to_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    provider_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Alert(Base, TenantMixin):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    message: Mapped[Text] = mapped_column(Text, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class Report(Base, TenantMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    range_start: Mapped[date] = mapped_column(Date, nullable=False)
    range_end: Mapped[date] = mapped_column(Date, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)


class PipelineEvent(Base, TenantMixin):
    __tablename__ = "pipeline_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)


class EvalRun(Base, TenantMixin):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    dataset: Mapped[str] = mapped_column(String(128), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    git_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)


class ReturnsSeries(Base, TenantMixin):
    __tablename__ = "returns_series"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=gen_uuid)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), nullable=False, index=True)
    version_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("product_versions.id"), nullable=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("batches.id"), nullable=True)
    week: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    returns_n: Mapped[int] = mapped_column(Integer, default=0)
    units_n: Mapped[int] = mapped_column(Integer, default=0)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
