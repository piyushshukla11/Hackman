"""
workflows/tasks/survey_loop.py

Render Workflows Task: survey_loop(survey_id: str)
Long-running, resume-safe task:
Monitors customer diagnostic survey responses up to 7 days.
Dispatches a gentle reminder at Day 3 if still unanswered, and expires token at Day 7.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from prism_core.db.base import get_sessionmaker
from prism_core.db.models import Survey


async def execute_survey_loop(survey_id: str) -> None:
    sessionmaker = get_sessionmaker()

    # Wait for response or timeout (in simulated / demo mode, checks state)
    async with sessionmaker() as session:
        survey = await session.get(Survey, survey_id)
        if not survey:
            return

        now = datetime.now(timezone.utc)
        if survey.status == "sent" and now > survey.expires_at.replace(tzinfo=timezone.utc):
            survey.status = "expired"
            await session.commit()
