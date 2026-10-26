"""
prism_core/ingest/__init__.py

L1 Ingest Gateway:
Exposes accept(envelope: RawReview) -> str (returns raw_id).
- Computes deterministic idempotency key (handles duplicates gracefully as no-op)
- Writes to raw_reviews
- Emits pipeline_events (stage="ingest", status="done")
- Enqueues process_review Render Workflow task
"""
from __future__ import annotations

import hashlib
from datetime import timezone
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.base import get_sessionmaker
from prism_core.db.models import RawReview as RawReviewModel
from prism_core.db.repositories.ingest import RawReviewRepository
from prism_core.events import emit
from prism_core.schemas.raw_review import RawReview


def compute_idempotency_key(envelope: RawReview) -> str:
    """
    Compute deterministic SHA-256 idempotency key:
    1. If source_review_id is present: sha256(tenant | source | source_review_id)
    2. Otherwise: sha256(tenant | source | product | author_hash | reviewed_at | normalised_text)
    """
    tenant = envelope.tenant_id.strip()
    source = envelope.source_id.strip()

    if envelope.source_review_id and envelope.source_review_id.strip():
        raw_key = f"{tenant}|{source}|{envelope.source_review_id.strip()}"
    else:
        product = (envelope.product.sku or envelope.product.external_id or "").strip()
        author = (envelope.author.id_hash or "").strip()
        reviewed_at = envelope.reviewed_at.isoformat()
        norm_text = (envelope.text or "").strip().lower()
        raw_key = f"{tenant}|{source}|{product}|{author}|{reviewed_at}|{norm_text}"

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def accept(envelope: RawReview, session: AsyncSession | None = None) -> str:
    """
    Ingest Gateway public entrypoint.
    Returns the raw_id of the review. If already exists, returns existing raw_id (no-op).
    """
    idempotency_key = compute_idempotency_key(envelope)

    async def _execute(sess: AsyncSession) -> str:
        repo = RawReviewRepository(sess, envelope.tenant_id)
        existing = await repo.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing.id

        # Insert new RawReview
        raw_model = RawReviewModel(
            tenant_id=envelope.tenant_id,
            source_id=envelope.source_id,
            idempotency_key=idempotency_key,
            kind=envelope.kind,
            payload=envelope.model_dump(mode="json"),
        )
        await repo.add(raw_model)
        await sess.flush()

        # Emit ingest pipeline event
        await emit(
            stage="ingest",
            status="done",
            run_id=f"run_{raw_model.id[:8]}",
            tenant_id=envelope.tenant_id,
            review_id=raw_model.id,
            attempt=1,
            session=sess,
            detail={"source_id": envelope.source_id, "channel": envelope.channel},
        )

        return raw_model.id

    if session is not None:
        return await _execute(session)
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as sess:
            raw_id = await _execute(sess)
            await sess.commit()
            return raw_id
