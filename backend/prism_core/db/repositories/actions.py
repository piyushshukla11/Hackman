"""
prism_core/db/repositories/actions.py

Repositories for Actions: Serious Complaints, Surveys, Responses, Email Outbox, Alerts, and Reports.
"""
from __future__ import annotations

from typing import Sequence
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.models import Alert, EmailOutbox, Report, SeriousComplaint, Survey, SurveyResponse
from prism_core.db.repositories.base import BaseRepository


class SeriousComplaintRepository(BaseRepository[SeriousComplaint]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(SeriousComplaint, session, tenant_id)

    async def list_complaints(self, status: str | None = None, limit: int = 50) -> Sequence[SeriousComplaint]:
        clauses = []
        if status:
            clauses.append(SeriousComplaint.status == status)
        stmt = self._scoped_query(*clauses).order_by(desc(SeriousComplaint.created_at)).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()


class SurveyRepository(BaseRepository[Survey]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(Survey, session, tenant_id)

    async def get_by_token_hash(self, token_hash: str) -> Survey | None:
        stmt = self._scoped_query(Survey.token_hash == token_hash)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_issue(self, issue_id: str) -> Sequence[Survey]:
        stmt = self._scoped_query(Survey.issue_id == issue_id).order_by(desc(Survey.created_at))
        res = await self.session.execute(stmt)
        return res.scalars().all()


class SurveyResponseRepository(BaseRepository[SurveyResponse]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(SurveyResponse, session, tenant_id)

    async def get_by_survey_id(self, survey_id: str) -> SurveyResponse | None:
        stmt = self._scoped_query(SurveyResponse.survey_id == survey_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class EmailOutboxRepository(BaseRepository[EmailOutbox]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(EmailOutbox, session, tenant_id)

    async def list_queued(self, limit: int = 50) -> Sequence[EmailOutbox]:
        stmt = self._scoped_query(EmailOutbox.status == "queued").order_by(EmailOutbox.created_at.asc()).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(Alert, session, tenant_id)

    async def list_recent(self, product_id: str | None = None, limit: int = 20) -> Sequence[Alert]:
        clauses = []
        if product_id:
            clauses.append(Alert.product_id == product_id)
        stmt = self._scoped_query(*clauses).order_by(desc(Alert.triggered_at)).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()


class ReportRepository(BaseRepository[Report]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(Report, session, tenant_id)

    async def list_by_product(self, product_id: str) -> Sequence[Report]:
        stmt = self._scoped_query(Report.product_id == product_id).order_by(desc(Report.created_at))
        res = await self.session.execute(stmt)
        return res.scalars().all()
