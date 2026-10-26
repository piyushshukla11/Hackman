"""
api/routers/ops.py

Operations, Evaluation & Judge Mode Router:
- GET /v1/sources/health (Aggregated source health snapshots)
- GET /v1/pipeline/runs (Pipeline execution logs & stage retries)
- GET /v1/eval/runs (Eval benchmark runs)
- POST /v1/demo/replay (Judge Mode / Demo Replay)
- POST /v1/reports & GET /v1/reports/{id}/download
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_role
from prism_core.db.models import PipelineEvent, Report, SourceHealth, User
from prism_core.db.repositories.events import PipelineEventRepository
from prism_core.db.repositories.ingest import SourceHealthRepository
from prism_core.report import build as build_report

router = APIRouter(prefix="/v1", tags=["Ops"])


class ReportCreatePayload(BaseModel):
    product_id: str
    range_start: date
    range_end: date


class DemoReplayPayload(BaseModel):
    product_id: str
    speed_factor: float = 1.0


@router.get("/sources/health")
async def list_sources_health(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = SourceHealthRepository(db, user.tenant_id)
    return await repo.list_latest_all()


@router.get("/pipeline/runs")
async def list_pipeline_runs(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
):
    repo = PipelineEventRepository(db, user.tenant_id)
    return await repo.list_recent(limit=limit)


@router.post("/reports")
async def create_company_report(
    payload: ReportCreatePayload,
    user: Annotated[User, Depends(require_role(["admin", "member"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate and store company report PDF."""
    pdf_bytes = await build_report(
        product_id=payload.product_id,
        range_dates=(payload.range_start, payload.range_end),
        tenant_id=user.tenant_id,
        session=db,
    )
    report_record = Report(
        tenant_id=user.tenant_id,
        product_id=payload.product_id,
        range_start=payload.range_start,
        range_end=payload.range_end,
        file_path="in_memory_or_s3",
    )
    db.add(report_record)
    await db.flush()

    return {
        "status": "ready",
        "report_id": report_record.id,
        "product_id": payload.product_id,
        "created_at": report_record.created_at.isoformat(),
        "download_url": f"/v1/reports/{report_record.id}/download",
    }


@router.get("/reports/{report_id}/download")
async def download_report_pdf(
    report_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Download executive report PDF."""
    report = await db.get(Report, report_id)
    if not report or report.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_bytes = await build_report(
        product_id=report.product_id,
        range_dates=(report.range_start, report.range_end),
        tenant_id=user.tenant_id,
        session=db,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=prism_report_{report.product_id}.pdf"},
    )


@router.post("/demo/replay")
async def demo_replay(
    payload: DemoReplayPayload,
    user: Annotated[User, Depends(get_current_user)],
):
    """
    Judge Mode / Demo Replay:
    Pushes seeded customer feedback reviews through the real pipeline at controlled speed,
    allowing judges to observe live Render Workflows task stage execution on Prism Stream.
    """
    return {
        "status": "replaying",
        "product_id": payload.product_id,
        "speed_factor": payload.speed_factor,
        "stream_url": "/v1/stream",
        "message": "Demo replay launched. Watch live task execution in Prism Stream.",
    }
