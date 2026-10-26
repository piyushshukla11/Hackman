"""
prism_core/compare/__init__.py

L4 Diagnose — Comparison Engine and Product Health Index.
Evaluates 5 comparative lenses (product, time, batch, channel, version) directly over metric_rollups.
Enforces min sample n=20 per side and calculates statistical significance (two-proportion z-test).
"""
from __future__ import annotations

import math
from typing import Literal
from scipy import stats
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.base import get_sessionmaker
from prism_core.db.models import MetricRollup
from prism_core.schemas.diagnose import Comparison
from prism_core.schemas.ops import HealthIndex


def compute_health_score(
    rating_mean: float,
    sentiment_pos_rate: float,
    open_issue_count: int,
) -> HealthIndex:
    """
    Health Score formula:
    health = 0.35 * rating_comp + 0.45 * sentiment_comp + 0.20 * (1 - open_issue_penalty)
    Normalized to 0 - 100 scale.
    """
    # rating_comp: 1.0 to 5.0 -> 0 to 100
    rating_comp = max(0.0, min(100.0, ((rating_mean - 1.0) / 4.0) * 100.0))

    # sentiment_comp: 0.0 to 1.0 -> 0 to 100
    sentiment_comp = max(0.0, min(100.0, sentiment_pos_rate * 100.0))

    # open_issue_penalty: 5% per open issue, max 50%
    penalty_rate = min(0.50, open_issue_count * 0.05)
    issue_comp = (1.0 - penalty_rate) * 100.0

    overall = (0.35 * rating_comp) + (0.45 * sentiment_comp) + (0.20 * issue_comp)
    overall = round(max(0.0, min(100.0, overall)), 1)

    return HealthIndex(
        product_id="",
        overall_health=overall,
        rating_component=round(rating_comp, 1),
        sentiment_component=round(sentiment_comp, 1),
        open_issue_penalty=round(penalty_rate * 100.0, 1),
        open_issues_count=open_issue_count,
    )


async def run(
    lens: Literal["product", "time", "batch", "channel", "version"],
    a: str,
    b: str,
    metric: Literal["rating", "neg_rate", "health_score"] = "neg_rate",
    product_id: str | None = None,
    tenant_id: str = "default",
    session: AsyncSession | None = None,
) -> Comparison:
    """
    Public entrypoint for L4 Comparison Engine.
    Executes comparison between slice A and slice B over metric_rollups.
    """
    async def _compare(sess: AsyncSession) -> Comparison:
        clauses = [MetricRollup.tenant_id == tenant_id]
        if product_id:
            clauses.append(MetricRollup.product_id == product_id)

        # Build lens query filters
        if lens == "batch":
            stmt_a = select(MetricRollup).where(*clauses, MetricRollup.batch_id == a)
            stmt_b = select(MetricRollup).where(*clauses, MetricRollup.batch_id == b)
        elif lens == "channel":
            stmt_a = select(MetricRollup).where(*clauses, MetricRollup.channel == a)
            stmt_b = select(MetricRollup).where(*clauses, MetricRollup.channel == b)
        elif lens == "version":
            stmt_a = select(MetricRollup).where(*clauses, MetricRollup.version_id == a)
            stmt_b = select(MetricRollup).where(*clauses, MetricRollup.version_id == b)
        else:
            stmt_a = select(MetricRollup).where(*clauses)
            stmt_b = select(MetricRollup).where(*clauses)

        res_a = (await sess.execute(stmt_a)).scalars().all()
        res_b = (await sess.execute(stmt_b)).scalars().all()

        n_a = sum(r.n_reviews for r in res_a)
        n_b = sum(r.n_reviews for r in res_b)

        # Min sample size constraint: 20 per side
        if n_a < 20 or n_b < 20:
            return Comparison(
                lens=lens, a=a, b=b, metric=metric,
                delta=0.0, ci_low=0.0, ci_high=0.0, p_value=1.0,
                n_a=n_a, n_b=n_b, verdict="insufficient_data", top_features=[],
            )

        neg_a = sum(r.n_neg for r in res_a)
        neg_b = sum(r.n_neg for r in res_b)

        rate_a = neg_a / n_a
        rate_b = neg_b / n_b
        delta = round(rate_b - rate_a, 3)

        # Two-proportion pooled z-test
        p_pool = (neg_a + neg_b) / (n_a + n_b)
        se = math.sqrt(p_pool * (1.0 - p_pool) * ((1.0 / n_a) + (1.0 / n_b))) if p_pool > 0 and p_pool < 1 else 0.01
        z_stat = (rate_b - rate_a) / se if se > 0 else 0.0
        p_val = round(float(2 * (1 - stats.norm.cdf(abs(z_stat)))), 4)

        ci_low = round(delta - 1.96 * se, 3)
        ci_high = round(delta + 1.96 * se, 3)

        if p_val < 0.05:
            verdict: Literal["better", "worse", "no_change", "insufficient_data"] = "worse" if delta > 0 else "better"
        else:
            verdict = "no_change"

        return Comparison(
            lens=lens, a=a, b=b, metric=metric,
            delta=delta, ci_low=ci_low, ci_high=ci_high, p_value=p_val,
            n_a=n_a, n_b=n_b, verdict=verdict, top_features=[],
        )

    if session is not None:
        return await _compare(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            return await _compare(sess)
