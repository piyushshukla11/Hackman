"""
prism_core/db/repositories/base.py

Base repository class enforcing strict multi-tenancy.
Every query must carry tenant_id.
"""
from __future__ import annotations

from typing import Generic, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from prism_core.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Abstract base repository that enforces tenant isolation on all queries.
    Raises ValueError if tenant_id is omitted or empty.
    """

    def __init__(self, model_cls: Type[ModelT], session: AsyncSession, tenant_id: str):
        if not tenant_id or not tenant_id.strip():
            raise ValueError(f"Strict multi-tenancy violation: tenant_id is required for {model_cls.__name__}")
        self.model_cls = model_cls
        self.session = session
        self.tenant_id = tenant_id.strip()

    def _scoped_query(self, *where_clauses):
        """Construct a SELECT statement with mandatory tenant_id filter."""
        return select(self.model_cls).where(
            and_(
                getattr(self.model_cls, "tenant_id") == self.tenant_id,
                *where_clauses,
            )
        )

    async def get_by_id(self, item_id: str) -> ModelT | None:
        """Fetch a single record by primary key id, strictly scoped to tenant_id."""
        stmt = self._scoped_query(getattr(self.model_cls, "id") == item_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, entity: ModelT) -> ModelT:
        """Add an entity to the session, ensuring its tenant_id matches the repository scope."""
        entity.tenant_id = self.tenant_id
        self.session.add(entity)
        return entity
