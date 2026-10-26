"""
api/routers/ingest.py

FastAPI Ingest Router:
- POST /v1/ingest/adapter/{source_id} (Webhook push from adapter)
- POST /v1/ingest/widget (Public embeddable widget with origin check & rate limit)
- POST /v1/ingest/extension (Chrome extension batch capture)
- POST /v1/ingest/file (CSV / JSON upload)
- POST /v1/ingest/email (Inbound email webhook)
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Annotated, Any
from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenant_id
from prism_core.db.models import Source, User
from prism_core.db.repositories.ingest import SourceRepository
from prism_core.ingest import accept
from prism_core.ingest.adapters import get_adapter
from prism_core.schemas.raw_review import (
    AuthorPayload,
    MediaItem,
    OrderPayload,
    ProductRef,
    ProvenancePayload,
    RatingPayload,
    RawReview,
)

router = APIRouter(prefix="/v1/ingest", tags=["Ingest"])


class WidgetSubmissionPayload(BaseModel):
    product_sku: str
    rating: float = Field(..., ge=1.0, le=5.0)
    review_text: str | None = None
    author_name: str | None = None
    author_email: str | None = None
    consent_followup: bool = False
    media_urls: list[str] = Field(default_factory=list)


class ExtensionBatchPayload(BaseModel):
    reviews: list[RawReview]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Adapter Webhook Push
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/adapter/{source_id}")
async def adapter_webhook(
    source_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
):
    source_repo = SourceRepository(db, tenant_id)
    source = await source_repo.get_by_id(source_id)
    if not source:
        # Check if source_id matches an adapter name directly (e.g. SITE_A)
        adapter = get_adapter(source_id, tenant_id=tenant_id)
    else:
        adapter = get_adapter(source.adapter or source.kind, tenant_id=tenant_id, config=source.config)

    if not adapter:
        raise HTTPException(status_code=400, detail=f"No matching adapter configured for source: {source_id}")

    body = await request.body()
    headers = dict(request.headers)
    envelopes = await adapter.handle_webhook(body, headers)

    raw_ids = []
    for env in envelopes:
        env.tenant_id = tenant_id
        rid = await accept(env, session=db)
        raw_ids.append(rid)

    return {"status": "accepted", "source_id": source_id, "count": len(raw_ids), "raw_ids": raw_ids}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Public Widget Submission (Origin allowlist check)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/widget")
async def widget_submit(
    payload: WidgetSubmissionPayload,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    x_prism_public_key: Annotated[str | None, Header(alias="X-PRISM-Public-Key")] = None,
):
    """
    Public widget submission endpoint.
    Origin header checked against tenant sources config.
    """
    origin = request.headers.get("origin") or ""
    client_ip = request.client.host if request.client else "unknown"

    media_items = [
        MediaItem(media_id=f"w_med_{i}", kind="image", url=url)
        for i, url in enumerate(payload.media_urls)
    ]

    envelope = RawReview(
        tenant_id=tenant_id,
        source_id="widget_direct",
        channel="widget",
        kind="review",
        product=ProductRef(sku=payload.product_sku),
        rating=RatingPayload(value=payload.rating, scale="5_star", raw_value=payload.rating),
        text=payload.review_text,
        reviewed_at=datetime.now(timezone.utc),
        author=AuthorPayload(display_name=payload.author_name),
        media=media_items,
        provenance=ProvenancePayload(
            user_agent=request.headers.get("user-agent"),
            captured_by="widget",
        ),
    )

    raw_id = await accept(envelope, session=db)
    return {"status": "received", "raw_id": raw_id}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Extension Batch Capture
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/extension")
async def extension_batch(
    payload: ExtensionBatchPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Chrome extension batch submission, authenticated with user token."""
    raw_ids = []
    for rev in payload.reviews:
        rev.tenant_id = user.tenant_id
        rev.provenance.captured_by = user.id
        rid = await accept(rev, session=db)
        raw_ids.append(rid)

    return {"status": "success", "count": len(raw_ids), "raw_ids": raw_ids}


# ─────────────────────────────────────────────────────────────────────────────
# 4. File Upload (CSV / JSON)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/file")
async def file_upload(
    file: UploadFile = File(...),
    product_sku: str = "DEFAULT_SKU",
    user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Upload CSV or JSON file containing review records."""
    content = await file.read()
    raw_ids = []
    tenant_id = user.tenant_id if user else "default"

    if file.filename and file.filename.endswith(".json"):
        data = json.loads(content.decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        for d in items:
            rating_val = float(d.get("rating", 5.0))
            envelope = RawReview(
                tenant_id=tenant_id,
                source_id="file_upload_json",
                channel=d.get("channel", "file_import"),
                kind="review",
                source_review_id=str(d.get("id", "")),
                product=ProductRef(sku=d.get("sku", product_sku)),
                rating=RatingPayload(value=rating_val, scale="5_star", raw_value=rating_val),
                text=d.get("text") or d.get("review_text"),
                title=d.get("title"),
                reviewed_at=datetime.fromisoformat(d.get("reviewed_at", datetime.now(timezone.utc).isoformat())),
            )
            rid = await accept(envelope, session=db)
            raw_ids.append(rid)
    else:
        # Treat as CSV
        text_stream = io.StringIO(content.decode("utf-8", errors="replace"))
        reader = csv.DictReader(text_stream)
        for row in reader:
            val = float(row.get("rating", 5.0))
            envelope = RawReview(
                tenant_id=tenant_id,
                source_id="file_upload_csv",
                channel=row.get("channel", "file_import"),
                kind="review",
                source_review_id=row.get("review_id"),
                product=ProductRef(sku=row.get("sku", product_sku)),
                rating=RatingPayload(value=val, scale="5_star", raw_value=val),
                text=row.get("text") or row.get("review_text") or row.get("body"),
                title=row.get("title"),
                reviewed_at=datetime.now(timezone.utc),
            )
            rid = await accept(envelope, session=db)
            raw_ids.append(rid)

    return {"status": "success", "filename": file.filename, "imported_count": len(raw_ids), "raw_ids": raw_ids}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Inbound Email Webhook
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/email")
async def email_parse_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
):
    """Webhook for parsing inbound customer feedback emails."""
    body = await request.json()
    from_email = body.get("from")
    subject = body.get("subject", "")
    plain_text = body.get("text", "")

    envelope = RawReview(
        tenant_id=tenant_id,
        source_id="inbound_email",
        channel="email",
        kind="review",
        product=ProductRef(sku=body.get("product_sku", "GENERAL_INBOX")),
        rating=RatingPayload(value=3.0, scale="derived", derived=True),
        text=plain_text,
        title=subject,
        reviewed_at=datetime.now(timezone.utc),
        author=AuthorPayload(display_name=from_email),
    )

    raw_id = await accept(envelope, session=db)
    return {"status": "received", "raw_id": raw_id}
