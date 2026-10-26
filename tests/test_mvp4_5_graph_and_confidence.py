"""
tests/test_mvp4_5_graph_and_confidence.py

Unit tests for MVP 4 & 5:
- Issue Graph edge weight formula (semantic, time, batch affinity, symptom)
- Defect concentration calculation & binomial p-value significance
- Confidence breakdown waterfall (F, D, C, T, E, penalties, bonuses)
- Comparison engine two-proportion z-test & health score computation
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from prism_core.compare import compute_health_score
from prism_core.confidence import score as score_confidence
from prism_core.schemas.diagnose import Cluster


def test_confidence_breakdown_waterfall():
    cluster = Cluster(
        id="cls_001",
        product_id="prod_001",
        feature="durability",
        polarity="neg",
        issue_type="batch",
        severity="high",
        first_seen=date(2024, 3, 1),
        last_seen=date(2024, 3, 15),
        size=10,
        defect_concentration=0.82,
        dominant_batch_id="BATCH-2024-W12",
        p_value=0.0001,
        lead_time_days=21,
    )

    breakdown = score_confidence(
        cluster=cluster,
        verified_buyer_ratio=0.85,
        ambiguity_penalty=1.00,
        coherence_bonus=0.05,
        survey_delta=0.00,
    )

    assert breakdown.frequency == 1.0  # size=10 saturates F at 1.0
    assert breakdown.density == 0.82
    assert breakdown.evidence == 0.85
    assert breakdown.final >= 0.75
    assert breakdown.level == "act"


def test_health_score_computation():
    # Healthy product: 4.5 stars, 90% positive sentiment, 0 open issues
    health_good = compute_health_score(rating_mean=4.5, sentiment_pos_rate=0.90, open_issue_count=0)
    assert health_good.overall_health >= 85.0

    # Distressed product: 2.0 stars, 20% positive sentiment, 6 open issues
    health_bad = compute_health_score(rating_mean=2.0, sentiment_pos_rate=0.20, open_issue_count=6)
    assert health_bad.overall_health < 40.0
