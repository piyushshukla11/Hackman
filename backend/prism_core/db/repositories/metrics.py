"""
prism_core/db/repositories/metrics.py

Repositories for Metrics, Trends, and Returns Series.
Single source of truth for comparison engine and health index.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.models import MetricRollup, ReturnsSeries, TrendPoint
from prism_core.db.repositories.base import BaseRepository


class MetricRollupRepository(BaseRepository[MetricRollup]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(MetricRollup, session, tenant_id)

    async def get_for_slice(
        self,
        product_id: str,
        feature: str | None = None,
        channel: str | None = None,
        batch_id: str | None = None,
        version_id: str | None = None,
        start_week: date | None = None,
        end_week: date | None = None,
    ) -> Sequence[MetricRollup]:
        clauses = [MetricRollup.product_id == product_id]
        if feature:
            clauses.append(MetricRollup.feature == feature)
        if channel:
            clauses.append(MetricRollup.channel == channel)
        if batch_id:
            clauses.append(MetricRollup.batch_id == batch_id)
        if version_id:
            clauses.append(MetricRollup.version_id == version_id)
        if start_week:
            clauses.append(MetricRollup.week >= start_week)
        if end_week:
            clauses.append(MetricRollup.week <= end_week)

        stmt = self._scoped_query(*clauses).order_by(MetricRollup.week.asc())
        res = await self.session.execute(stmt)
        return res.scalars().all()


class TrendPointRepository(BaseRepository[TrendPoint]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(TrendPoint, session, tenant_id)

    async def list_trends(
        self,
        product_id: str,
        feature: str | None = None,
        channel: str | None = None,
    ) -> Sequence[TrendPoint]:
        clauses = [TrendPoint.product_id == product_id]
        if feature:
            clauses.append(TrendPoint.feature == feature)
        if channel:
            clauses.append(TrendPoint.channel == channel)

        stmt = self._scoped_query(*clauses).order_by(TrendPoint.window.asc())
        res = await self.session.execute(stmt)
        return res.scalars().all()


class ReturnsSeriesRepository(BaseRepository[ReturnsSeries]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(ReturnsSeries, session, tenant_id)

    async def list_by_product(self, product_id: str) -> Sequence[ReturnsSeries]:
        stmt = self._scoped_query(ReturnsSeries.product_id == product_id).order_by(ReturnsSeries.week.asc())
        res = await self.session.execute(stmt)
        return res.scalars().all()
