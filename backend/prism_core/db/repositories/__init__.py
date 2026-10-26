"""
prism_core/db/repositories

Clean exports of all multi-tenant repositories.
Delegates to top-level `db.repositories` package with local fallback.
"""
from __future__ import annotations

try:
    from db.repositories import (
        AlertRepository,
        APIKeyRepository,
        BaseRepository,
        BatchRepository,
        ClusterMemberRepository,
        EmailOutboxRepository,
        EvalRunRepository,
        FeatureTaxonomyRepository,
        GraphEdgeRepository,
        IssueClusterRepository,
        MetricRollupRepository,
        ModificationRepository,
        PipelineEventRepository,
        ProductRepository,
        ProductVersionRepository,
        RawReviewRepository,
        ReportRepository,
        ReturnsSeriesRepository,
        ReviewFeatureRepository,
        ReviewRepository,
        SeriousComplaintRepository,
        SourceHealthRepository,
        SourceRepository,
        SurveyRepository,
        SurveyResponseRepository,
        TrendPointRepository,
        TrustGateLogRepository,
        UserRepository,
    )
except ImportError:
    from prism_core.db.repositories.base import BaseRepository  # type: ignore
    from prism_core.db.repositories.users import UserRepository, APIKeyRepository  # type: ignore
    from prism_core.db.repositories.catalog import (  # type: ignore
        ProductRepository,
        ProductVersionRepository,
        BatchRepository,
        ModificationRepository,
        FeatureTaxonomyRepository,
    )
    from prism_core.db.repositories.ingest import (  # type: ignore
        SourceRepository,
        SourceHealthRepository,
        RawReviewRepository,
    )
    from prism_core.db.repositories.reviews import (  # type: ignore
        ReviewRepository,
        ReviewFeatureRepository,
        TrustGateLogRepository,
    )
    from prism_core.db.repositories.graph import (  # type: ignore
        GraphEdgeRepository,
        IssueClusterRepository,
        ClusterMemberRepository,
    )
    from prism_core.db.repositories.metrics import (  # type: ignore
        MetricRollupRepository,
        TrendPointRepository,
        ReturnsSeriesRepository,
    )
    from prism_core.db.repositories.actions import (  # type: ignore
        SeriousComplaintRepository,
        SurveyRepository,
        SurveyResponseRepository,
        EmailOutboxRepository,
        AlertRepository,
        ReportRepository,
    )
    from prism_core.db.repositories.events import (  # type: ignore
        PipelineEventRepository,
        EvalRunRepository,
    )

__all__ = [
    "BaseRepository",
    "UserRepository",
    "APIKeyRepository",
    "ProductRepository",
    "ProductVersionRepository",
    "BatchRepository",
    "ModificationRepository",
    "FeatureTaxonomyRepository",
    "SourceRepository",
    "SourceHealthRepository",
    "RawReviewRepository",
    "ReviewRepository",
    "ReviewFeatureRepository",
    "TrustGateLogRepository",
    "GraphEdgeRepository",
    "IssueClusterRepository",
    "ClusterMemberRepository",
    "MetricRollupRepository",
    "TrendPointRepository",
    "ReturnsSeriesRepository",
    "SeriousComplaintRepository",
    "SurveyRepository",
    "SurveyResponseRepository",
    "EmailOutboxRepository",
    "AlertRepository",
    "ReportRepository",
    "PipelineEventRepository",
    "EvalRunRepository",
]
