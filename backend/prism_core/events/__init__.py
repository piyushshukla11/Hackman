"""
prism_core/events/__init__.py

Pipeline event emitter.
Records event in pipeline_events table and publishes to Postgres NOTIFY channel 'prism_events'
for real-time fan-out via SSE (/v1/stream).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.base import get_sessionmaker
from prism_core.db.models import PipelineEvent


async def emit(
    stage: str,
    status: Literal["started", "done", "failed", "retry"],
    run_id: str,
    tenant_id: str = "default",
    review_id: str | None = None,
    attempt: int = 1,
    duration_ms: int | None = None,
    session: AsyncSession | None = None,
    **detail: Any,
) -> None:
    """
    Emit a pipeline event:
    1. Persists record in pipeline_events
    2. Sends NOTIFY prism_events payload
    """
    event_payload = {
        "stage": stage,
        "status": status,
        "run_id": run_id,
        "tenant_id": tenant_id,
        "review_id": review_id,
        "attempt": attempt,
        "duration_ms": duration_ms,
        "detail": detail,
        "at": datetime.now(timezone.utc).isoformat(),
    }

    async def _record(sess: AsyncSession):
        ev = PipelineEvent(
            tenant_id=tenant_id,
            run_id=run_id,
            review_id=review_id,
            stage=stage,
            status=status,
            attempt=attempt,
            duration_ms=duration_ms,
            detail=detail,
        )
        sess.add(ev)
        # Execute Postgres NOTIFY if using Postgres
        notify_str = json.dumps(event_payload).replace("'", "''")
        try:
            await sess.execute(text(f"NOTIFY prism_events, '{notify_str}';"))
        except Exception:
            # Safe ignore if on sqlite or non-postgres driver during unit tests
            pass

    if session is not None:
        await _record(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            await _record(sess)
            await sess.commit()
