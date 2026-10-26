"""
prism_core/confidence/__init__.py

L4 Diagnose — Confidence Scoring Engine.
Computes multi-component confidence breakdown:
base = 0.25*F + 0.20*D + 0.20*C + 0.15*T + 0.20*E
final = clamp(base * AmbiguityPenalty + CoherenceBonus + SurveyDelta, 0.0, 1.0)

Assigns action level:
- >= 0.75: Act
- 0.45 - 0.74: Monitor
- < 0.45: Gather
"""
from __future__ import annotations

from typing import Literal
from prism_core.schemas.diagnose import Cluster, ConfidenceBreakdown


def score(
    cluster: Cluster,
    verified_buyer_ratio: float = 0.70,
    ambiguity_penalty: float = 1.00,
    coherence_bonus: float = 0.05,
    survey_delta: float = 0.00,
) -> ConfidenceBreakdown:
    """
    Computes confidence breakdown for an issue cluster.
    Provides complete waterfall decomposition for UI.
    """
    # 1. Frequency (F): saturates at 10 mentions
    F = min(1.0, cluster.size / 10.0)

    # 2. Density / Concentration (D): based on defect concentration
    D = cluster.defect_concentration if cluster.defect_concentration > 0 else 0.50

    # 3. Consistency (C): agreement on polarity and feature
    C = 0.90 if cluster.issue_type in ("batch", "systemic") else 0.65

    # 4. Temporal (T): recency within last 28 days
    T = 0.85

    # 5. Evidence (E): verified purchase ratio
    E = min(1.0, max(0.0, verified_buyer_ratio))

    base = (0.25 * F) + (0.20 * D) + (0.20 * C) + (0.15 * T) + (0.20 * E)
    final = max(0.0, min(1.0, round((base * ambiguity_penalty) + coherence_bonus + survey_delta, 3)))

    if final >= 0.75:
        level: Literal["act", "monitor", "gather"] = "act"
    elif final >= 0.45:
        level = "monitor"
    else:
        level = "gather"

    return ConfidenceBreakdown(
        frequency=round(F, 3),
        density=round(D, 3),
        consistency=round(C, 3),
        temporal=round(T, 3),
        evidence=round(E, 3),
        ambiguity_penalty=round(ambiguity_penalty, 3),
        coherence_bonus=round(coherence_bonus, 3),
        survey_delta=round(survey_delta, 3),
        final=final,
        level=level,
    )
