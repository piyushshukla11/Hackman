"""
db/repositories/users.py

Repository for users and API keys.
"""
from __future__ import annotations

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, APIKey
from db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(User, session, tenant_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = self._scoped_query(User.email == email.lower().strip())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def update_onboarding(self, user_id: str, role_title: str, selected_views: list[str]) -> User | None:
        user = await self.get_by_id(user_id)
        if user:
            user.role_title = role_title
            user.selected_views = selected_views
            user.has_completed_onboarding = True
        return user


class APIKeyRepository(BaseRepository[APIKey]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(APIKey, session, tenant_id)

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        stmt = self._scoped_query(
            and_(
                APIKey.key_hash == key_hash,
                APIKey.revoked_at.is_(None),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
