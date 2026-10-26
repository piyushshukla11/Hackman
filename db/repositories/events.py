"""
db/repositories/events.py

Repositories for Pipeline Events and Eval Runs.
"""
from __future__ import annotations

from typing import Sequence
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import EvalRun, PipelineEvent
from db.repositories.base import BaseRepository


class PipelineEventRepository(BaseRepository[PipelineEvent]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(PipelineEvent, session, tenant_id)

    async def list_recent(self, limit: int = 100) -> Sequence[PipelineEvent]:
        stmt = self._scoped_query().order_by(desc(PipelineEvent.at)).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_by_run(self, run_id: str) -> Sequence[PipelineEvent]:
        stmt = self._scoped_query(PipelineEvent.run_id == run_id).order_by(PipelineEvent.at.asc())
        res = await self.session.execute(stmt)
        return res.scalars().all()


class EvalRunRepository(BaseRepository[EvalRun]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(EvalRun, session, tenant_id)

    async def list_runs(self, limit: int = 50) -> Sequence[EvalRun]:
        stmt = self._scoped_query().order_by(desc(EvalRun.at)).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()
