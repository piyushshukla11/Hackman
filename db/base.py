"""
db/base.py

SQLAlchemy 2.0 async engine, session factory, declarative base, and multi-tenant mixin.
All PRISM models inherit from Base and TenantMixin.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import DateTime, String, func
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Base declarative class for all SQLAlchemy models in PRISM."""
    pass


class TenantMixin:
    """
    Mandatory multi-tenancy and audit mixin.
    Enforces that every table carries tenant_id and created_at.
    """
    tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Tenant or organization identifier for strict multi-tenant isolation.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        doc="UTC timestamp when record was created.",
    )


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://prism:prism@localhost:5432/prism")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        db_url = get_database_url()
        _engine = create_async_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency helper for acquiring an async database session."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
