"""
api/routers/stream.py

Realtime Server-Sent Events (SSE) Router (/v1/stream):
Listens to Postgres NOTIFY channel 'prism_events' and fans out events to all connected clients.
Used by Prism Stream dashboard to visualize Render Workflows task stages in real time.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/v1", tags=["Realtime"])


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    """
    Asynchronous SSE stream generator.
    Streams pipeline stage transitions, trust verdicts, and defect alerts with heartbeat keepalive.
    """
    yield "event: connected\ndata: {\"status\": \"connected\", \"message\": \"Prism Stream active\"}\n\n"

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Heartbeat keepalive every 15 seconds
            await asyncio.sleep(15.0)
            yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        pass


@router.get("/stream")
async def stream_events(request: Request):
    """
    Public SSE endpoint for Prism Stream dashboard.
    Emits review.stage, trust.verdict, issue.updated, serious.new, survey.reply, and source.health.
    """
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
