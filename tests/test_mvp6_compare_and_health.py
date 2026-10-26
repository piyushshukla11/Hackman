"""
tests/test_mvp6_compare_and_health.py

Unit tests for MVP 6:
- Comparison Engine (5 comparative lenses: overall, by_batch, by_version, by_channel, returns_correlation)
- Statistical significance (two-proportion z-test with p-value calculation and sample size guard n >= 20)
- Single source of truth Product Health Score calculation
"""
from __future__ import annotations

import pytest
from prism_core.compare import (
    ComparisonEngine,
    two_proportion_z_test,
    compute_health_score,
)
from prism_core.schemas.diagnose import SliceRollup


def test_two_proportion_z_test():
    # Large significant defect spike between batches
    # Batch A: 5 defects out of 100 reviews (5%)
    # Batch B: 30 defects out of 100 reviews (30%)
    z_stat, p_val, is_sig = two_proportion_z_test(count1=5, nobs1=100, count2=30, nobs2=100)
    assert is_sig is True
    assert p_val < 0.001
    assert z_stat < -4.0

    # Insignificant difference
    # Batch A: 10 out of 100 (10%)
    # Batch B: 11 out of 100 (11%)
    z_stat2, p_val2, is_sig2 = two_proportion_z_test(count1=10, nobs1=100, count2=11, nobs2=100)
    assert is_sig2 is False
    assert p_val2 > 0.05

    # Small sample size (< 20) must return not significant
    _, p_val3, is_sig3 = two_proportion_z_test(count1=2, nobs1=10, count2=5, nobs2=12)
    assert is_sig3 is False
    assert p_val3 == 1.0


def test_comparison_engine_slices():
    engine = ComparisonEngine()

    batch_a = SliceRollup(slice_key="BATCH-A", n_reviews=50, n_neg=2, neg_rate=0.04, rating_mean=4.6)
    batch_b = SliceRollup(slice_key="BATCH-B", n_reviews=60, n_neg=25, neg_rate=0.416, rating_mean=2.8)

    diff = engine.compare_slices(slice_a=batch_a, slice_b=batch_b, feature="battery")
    assert diff.is_significant is True
    assert diff.delta_neg_rate > 0.30
    assert diff.p_value < 0.001
