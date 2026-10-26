"""
prism_core/db/repositories/ingest.py

Repositories for Ingest: Sources, Source Health, and Raw Reviews.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.models import RawReview, Source, SourceHealth
from prism_core.db.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(Source, session, tenant_id)

    async def list_sources(self) -> list[Source]:
        stmt = self._scoped_query().order_by(Source.display_name.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_cursor(self, source_id: str, cursor: str) -> None:
        source = await self.get_by_id(source_id)
        if source:
            source.cursor = cursor


class SourceHealthRepository(BaseRepository[SourceHealth]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(SourceHealth, session, tenant_id)

    async def get_latest(self, source_id: str) -> SourceHealth | None:
        stmt = self._scoped_query(SourceHealth.source_id == source_id).order_by(desc(SourceHealth.checked_at)).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_latest_all(self) -> list[SourceHealth]:
        stmt = self._scoped_query().order_by(desc(SourceHealth.checked_at))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class RawReviewRepository(BaseRepository[RawReview]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(RawReview, session, tenant_id)

    async def get_by_idempotency_key(self, idempotency_key: str) -> RawReview | None:
        stmt = self._scoped_query(RawReview.idempotency_key == idempotency_key)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
