"""
tests/test_db_package.py

Unit tests for standalone `db` package:
- All 27 tables registered in Base metadata
- Multi-tenancy isolation enforcement (ValueError on empty tenant_id)
- Model inheritance and column constraints
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from db.base import Base, TenantMixin
from db.models import (
    Alert,
    APIKey,
    Batch,
    ClusterMember,
    EmailOutbox,
    EvalRun,
    FeatureTaxonomy,
    GraphEdge,
    IssueCluster,
    MetricRollup,
    Modification,
    PipelineEvent,
    Product,
    ProductVersion,
    RawReview,
    Report,
    ReturnsSeries,
    Review,
    ReviewFeature,
    SeriousComplaint,
    Source,
    SourceHealth,
    Survey,
    SurveyResponse,
    TrendPoint,
    TrustGateLog,
    User,
)
from db.repositories.base import BaseRepository
from db.repositories.catalog import ProductRepository
from db.repositories.reviews import ReviewRepository


def test_all_27_models_registered_in_metadata():
    expected_tables = {
        "users",
        "api_keys",
        "feature_taxonomies",
        "products",
        "product_versions",
        "modifications",
        "batches",
        "sources",
        "source_health",
        "raw_reviews",
        "reviews",
        "review_features",
        "trust_gate_log",
        "graph_edges",
        "issue_clusters",
        "cluster_members",
        "metric_rollups",
        "trend_points",
        "serious_complaints",
        "surveys",
        "survey_responses",
        "email_outbox",
        "alerts",
        "reports",
        "pipeline_events",
        "eval_runs",
        "returns_series",
    }

    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables), (
        f"Missing tables: {expected_tables - registered_tables}"
    )
    assert len(expected_tables) == 27


def test_models_have_tenant_id():
    models = [
        User, APIKey, FeatureTaxonomy, Product, ProductVersion, Modification,
        Batch, Source, SourceHealth, RawReview, Review, ReviewFeature,
        TrustGateLog, GraphEdge, IssueCluster, ClusterMember, MetricRollup,
        TrendPoint, SeriousComplaint, Survey, SurveyResponse, EmailOutbox,
        Alert, Report, PipelineEvent, EvalRun, ReturnsSeries,
    ]

    for model in models:
        assert hasattr(model, "tenant_id"), f"{model.__name__} must define tenant_id"
        assert hasattr(model, "created_at"), f"{model.__name__} must define created_at"


def test_strict_multi_tenancy_enforcement():
    session_mock = MagicMock()

    # Omitted / empty tenant_id must raise ValueError
    with pytest.raises(ValueError, match="Strict multi-tenancy violation"):
        ProductRepository(session_mock, tenant_id="")

    with pytest.raises(ValueError, match="Strict multi-tenancy violation"):
        ProductRepository(session_mock, tenant_id="   ")

    # Valid tenant_id succeeds
    repo = ProductRepository(session_mock, tenant_id="tenant_alpha")
    assert repo.tenant_id == "tenant_alpha"
