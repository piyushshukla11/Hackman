"""
prism_core/trend/__init__.py

L4 Diagnose — Metrics Rollups and Trend Analysis.
Aggregates review data into metric_rollups table and detects negative rate spikes.
Exposes:
async def roll_up(product_id: str, tenant_id: str = "default", session: AsyncSession | None = None) -> list[TrendPointSchema]
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Sequence
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.base import get_sessionmaker
from prism_core.db.models import Alert, MetricRollup, Review, ReviewFeature, TrendPoint
from prism_core.schemas.diagnose import TrendPointSchema


def get_monday(d: date) -> date:
    """Return Monday of the given date's week."""
    return d - timedelta(days=d.weekday())


def wilson_score_interval(pos: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculate Wilson score interval for a binomial proportion."""
    if n <= 0:
        return 0.0, 0.0
    z = 1.96  # 95% confidence
    phat = pos / n
    denominator = 1.0 + (z**2 / n)
    center = (phat + (z**2 / (2 * n))) / denominator
    spread = (z * math.sqrt((phat * (1.0 - phat) / n) + (z**2 / (4 * n**2)))) / denominator
    return max(0.0, round(center - spread, 3)), min(1.0, round(center + spread, 3))


async def roll_up(
    product_id: str,
    tenant_id: str = "default",
    session: AsyncSession | None = None,
) -> list[TrendPointSchema]:
    """
    Public entrypoint for L4 Rollups and Trends.
    Rebuilds metric_rollups and trend_points, emitting spike alerts if negative rate exceeds 60%.
    """
    async def _execute(sess: AsyncSession) -> list[TrendPointSchema]:
        # Pull reviews and feature mentions
        stmt = (
            select(Review, ReviewFeature)
            .join(ReviewFeature, Review.id == ReviewFeature.review_id)
            .where(
                Review.tenant_id == tenant_id,
                Review.product_id == product_id,
            )
        )
        res = await sess.execute(stmt)
        rows = res.all()

        # Group by (version_id, batch_id, channel, feature, week)
        rollups_map: dict[tuple, dict] = defaultdict(lambda: {
            "n_reviews": 0, "n_neg": 0, "n_pos": 0,
            "rating_w_sum": 0.0, "rating_w": 0.0,
            "rating_n_all": 0, "rating_sum_all": 0.0,
        })

        for rev, rf in rows:
            week = get_monday(rev.reviewed_at.date())
            key = (rev.version_id, rev.batch_id, rev.channel, rf.feature, week)
            bucket = rollups_map[key]

            bucket["n_reviews"] += 1
            if rf.polarity == "neg":
                bucket["n_neg"] += 1
            elif rf.polarity == "pos":
                bucket["n_pos"] += 1

            r_val = float(rev.rating)
            bucket["rating_n_all"] += 1
            bucket["rating_sum_all"] += r_val

            # Trust weighted
            if rev.rating_status == "counted":
                bucket["rating_w_sum"] += r_val * 1.0
                bucket["rating_w"] += 1.0
            elif rev.rating_status == "downweighted":
                w = rev.trust_score
                bucket["rating_w_sum"] += r_val * w
                bucket["rating_w"] += w

        # Clear existing rollups for this product
        await sess.execute(delete(MetricRollup).where(MetricRollup.tenant_id == tenant_id, MetricRollup.product_id == product_id))
        await sess.execute(delete(TrendPoint).where(TrendPoint.tenant_id == tenant_id, TrendPoint.product_id == product_id))

        saved_rollups: list[MetricRollup] = []
        trend_points_out: list[TrendPointSchema] = []

        # Feature/channel weekly trends
        feature_channel_trends: dict[tuple[str, str, date], list] = defaultdict(list)

        for (v_id, b_id, chan, feat, wk), data in rollups_map.items():
            mr = MetricRollup(
                tenant_id=tenant_id,
                product_id=product_id,
                version_id=v_id,
                batch_id=b_id,
                channel=chan,
                feature=feat,
                week=wk,
                n_reviews=data["n_reviews"],
                n_neg=data["n_neg"],
                n_pos=data["n_pos"],
                rating_w_sum=round(data["rating_w_sum"], 2),
                rating_w=round(data["rating_w"], 2),
                rating_n_all=data["rating_n_all"],
                rating_sum_all=round(data["rating_sum_all"], 2),
            )
            saved_rollups.append(mr)
            feature_channel_trends[(feat, chan, wk)].append(data)

            # Spike detection: neg rate >= 60% with min 10 reviews
            if data["n_reviews"] >= 10:
                neg_rate = data["n_neg"] / data["n_reviews"]
                if neg_rate >= 0.60:
                    alert = Alert(
                        tenant_id=tenant_id,
                        product_id=product_id,
                        kind="spike",
                        severity="high",
                        message=f"Defect spike on {feat} in channel {chan}: {round(neg_rate*100, 1)}% negative (n={data['n_reviews']})",
                    )
                    sess.add(alert)

        sess.add_all(saved_rollups)

        # Build TrendPoints
        for (feat, chan, wk), buckets in feature_channel_trends.items():
            tot_n = sum(b["n_reviews"] for b in buckets)
            tot_neg = sum(b["n_neg"] for b in buckets)
            neg_rate = round(tot_neg / tot_n, 3) if tot_n > 0 else 0.0
            ci_low, ci_high = wilson_score_interval(tot_neg, tot_n)

            tot_w_sum = sum(b["rating_w_sum"] for b in buckets)
            tot_w = sum(b["rating_w"] for b in buckets)
            mean_trusted = round(tot_w_sum / tot_w, 2) if tot_w > 0 else 3.0

            tot_all_sum = sum(b["rating_sum_all"] for b in buckets)
            tot_all_n = sum(b["rating_n_all"] for b in buckets)
            mean_all = round(tot_all_sum / tot_all_n, 2) if tot_all_n > 0 else 3.0

            pattern = "batch_spike" if neg_rate >= 0.60 else ("healthy" if neg_rate <= 0.15 else "stable")

            tp_model = TrendPoint(
                tenant_id=tenant_id,
                product_id=product_id,
                feature=feat,
                channel=chan,
                window=wk,
                n=tot_n,
                neg_rate=neg_rate,
                neg_ci_low=ci_low,
                neg_ci_high=ci_high,
                rating_mean_trusted=mean_trusted,
                rating_mean_all=mean_all,
                pattern=pattern,
            )
            sess.add(tp_model)

            trend_points_out.append(TrendPointSchema(
                product_id=product_id,
                feature=feat,
                channel=chan,
                window=wk,
                n=tot_n,
                neg_rate=neg_rate,
                neg_ci_low=ci_low,
                neg_ci_high=ci_high,
                rating_mean_trusted=mean_trusted,
                rating_mean_all=mean_all,
                pattern=pattern,
            ))

        await sess.flush()
        return trend_points_out

    if session is not None:
        return await _execute(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            out = await _execute(sess)
            await sess.commit()
            return out
