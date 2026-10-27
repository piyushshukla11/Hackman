"""
api/routers/privacy.py

Privacy & DPDP Compliance Router:
DELETE /v1/privacy/author/{author_hash}
Redacts consumer identifiable information and replaces original review text with an anonymized notice.
"""
from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_role
from prism_core.db.models import RawReview, Review, User

router = APIRouter(prefix="/v1/privacy", tags=["Privacy"])


@router.delete("/author/{author_hash}")
async def anonymize_author_data(
    author_hash: str,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    DPDP / GDPR Compliance:
    Redacts personal data and review verbatims associated with the author_hash across the tenant.
    """
    stmt = (
        update(Review)
        .where(Review.tenant_id == user.tenant_id, Review.author_hash == author_hash)
        .values(
            text_original="[REDACTED PURSUANT TO DATA PRIVACY REQUEST]",
            text_en="[REDACTED PURSUANT TO DATA PRIVACY REQUEST]",
            author_hash=None,
        )
    )
    result = await db.execute(stmt)

    return {
        "status": "success",
        "author_hash": author_hash,
        "records_redacted": result.rowcount,
        "message": "Consumer data has been anonymized across tenant reviews.",
    }
