"""
db/repositories/reviews.py

Repositories for Canonical Reviews, Features, and Trust Gate Logs.
"""
from __future__ import annotations

from typing import Any, Sequence
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Review, ReviewFeature, TrustGateLog
from db.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(Review, session, tenant_id)

    async def list_reviews(
        self,
        product_id: str | None = None,
        channel: str | None = None,
        lang: str | None = None,
        text_status: str | None = None,
        rating_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Review]:
        clauses = []
        if product_id:
            clauses.append(Review.product_id == product_id)
        if channel:
            clauses.append(Review.channel == channel)
        if lang:
            clauses.append(Review.lang == lang)
        if text_status:
            clauses.append(Review.text_status == text_status)
        if rating_status:
            clauses.append(Review.rating_status == rating_status)

        stmt = self._scoped_query(*clauses).order_by(desc(Review.reviewed_at)).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def find_near_dupes(
        self,
        product_id: str,
        embedding: list[float],
        cosine_threshold: float = 0.95,
        limit: int = 5,
    ) -> Sequence[Review]:
        """Find near duplicates within the same tenant & product using pgvector cosine distance."""
        max_distance = 1.0 - cosine_threshold
        distance_expr = Review.embedding.cosine_distance(embedding)
        stmt = (
            self._scoped_query(
                Review.product_id == product_id,
                Review.embedding.is_not(None),
                distance_expr <= max_distance,
            )
            .order_by(distance_expr.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()


class ReviewFeatureRepository(BaseRepository[ReviewFeature]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(ReviewFeature, session, tenant_id)

    async def list_by_review(self, review_id: str) -> Sequence[ReviewFeature]:
        stmt = self._scoped_query(ReviewFeature.review_id == review_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()


class TrustGateLogRepository(BaseRepository[TrustGateLog]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(TrustGateLog, session, tenant_id)

    async def list_by_review(self, review_id: str) -> Sequence[TrustGateLog]:
        stmt = self._scoped_query(TrustGateLog.review_id == review_id).order_by(TrustGateLog.gate.asc())
        res = await self.session.execute(stmt)
        return res.scalars().all()
