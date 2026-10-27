"""
db/repositories

Clean exports of all multi-tenant repositories.
"""
from db.repositories.base import BaseRepository
from db.repositories.users import UserRepository, APIKeyRepository
from db.repositories.catalog import (
    ProductRepository,
    ProductVersionRepository,
    BatchRepository,
    ModificationRepository,
    FeatureTaxonomyRepository,
)
from db.repositories.ingest import (
    SourceRepository,
    SourceHealthRepository,
    RawReviewRepository,
)
from db.repositories.reviews import (
    ReviewRepository,
    ReviewFeatureRepository,
    TrustGateLogRepository,
)
from db.repositories.graph import (
    GraphEdgeRepository,
    IssueClusterRepository,
    ClusterMemberRepository,
)
from db.repositories.metrics import (
    MetricRollupRepository,
    TrendPointRepository,
    ReturnsSeriesRepository,
)
from db.repositories.actions import (
    SeriousComplaintRepository,
    SurveyRepository,
    SurveyResponseRepository,
    EmailOutboxRepository,
    AlertRepository,
    ReportRepository,
)
from db.repositories.events import (
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
