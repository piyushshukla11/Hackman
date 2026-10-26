"""
prism_core/db/repositories

Clean exports of all multi-tenant repositories.
"""
from prism_core.db.repositories.base import BaseRepository
from prism_core.db.repositories.users import UserRepository, APIKeyRepository
from prism_core.db.repositories.catalog import (
    ProductRepository,
    ProductVersionRepository,
    BatchRepository,
    ModificationRepository,
    FeatureTaxonomyRepository,
)
from prism_core.db.repositories.ingest import (
    SourceRepository,
    SourceHealthRepository,
    RawReviewRepository,
)
from prism_core.db.repositories.reviews import (
    ReviewRepository,
    ReviewFeatureRepository,
    TrustGateLogRepository,
)
from prism_core.db.repositories.graph import (
    GraphEdgeRepository,
    IssueClusterRepository,
    ClusterMemberRepository,
)
from prism_core.db.repositories.metrics import (
    MetricRollupRepository,
    TrendPointRepository,
    ReturnsSeriesRepository,
)
from prism_core.db.repositories.actions import (
    SeriousComplaintRepository,
    SurveyRepository,
    SurveyResponseRepository,
    EmailOutboxRepository,
    AlertRepository,
    ReportRepository,
)
from prism_core.db.repositories.events import (
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
