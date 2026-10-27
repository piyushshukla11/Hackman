"""
workflows/tasks/source_health.py

Render Workflows Cron Task: source_health()
Runs every 10 minutes to poll all active ingestion sources, calculate freshness/lag/error-rate,
and update health snapshots.
"""
from __future__ import annotations

from sqlalchemy import select
from prism_core.db.base import get_sessionmaker
from prism_core.db.models import Source
from prism_core.ingest.sources_health import evaluate as evaluate_source_health


async def execute_source_health_check(tenant_id: str = "default") -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = select(Source).where(Source.tenant_id == tenant_id, Source.enabled.is_(True))
        sources = (await session.execute(stmt)).scalars().all()

        for s in sources:
            await evaluate_source_health(source_id=s.id, tenant_id=tenant_id, session=session)

        await session.commit()
