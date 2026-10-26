"""
prism_core/ingest/adapters/sim_sites.py

Implementations of the 6 simulated e-commerce site adapters (SITE_A to SITE_F)
implementing the ReviewSource protocol.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any
from prism_core.schemas.ops import ProbeResult
from prism_core.schemas.raw_review import (
    AuthorPayload,
    MediaItem,
    OrderPayload,
    ProductRef,
    ProvenancePayload,
    RatingPayload,
    RawReview,
)


def normalise_rating(raw_val: Any, scale: str) -> tuple[float, bool]:
    """
    Normalise source rating scale into standard 0.5-5.0 scale per contracts.md §2.
    Returns (normalised_val, is_derived).
    """
    if scale in ("5_star", "5_half_star"):
        val = float(raw_val)
        return max(0.5, min(5.0, round(val * 2) / 2)), False
    elif scale == "10_point":
        val = float(raw_val)
        norm = round((val / 2.0) * 2) / 2
        return max(0.5, min(5.0, norm)), False
    elif scale == "100_point":
        val = float(raw_val)
        norm = round((val / 20.0) * 2) / 2
        return max(0.5, min(5.0, norm)), False
    elif scale == "thumbs":
        # Thumbs up -> 4.5, Thumbs down -> 1.5 with derived=True
        s = str(raw_val).strip().lower()
        if s in ("up", "1", "true", "positive", "like"):
            return 4.5, True
        return 1.5, True
    else:
        try:
            val = float(raw_val)
            return max(0.5, min(5.0, round(val * 2) / 2)), False
        except Exception:
            return 3.0, True


# ─────────────────────────────────────────────────────────────────────────────
# SITE_A: REST cursor-paginated JSON, 5 integer stars, verified purchase + order dates
# ─────────────────────────────────────────────────────────────────────────────
class SiteAAdapter:
    id = "SITE_A"

    def __init__(self, tenant_id: str = "default", config: dict[str, Any] | None = None):
        self.tenant_id = tenant_id
        self.config = config or {}

    async def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]:
        # Returns empty list in unit mode or fetches from mock endpoint
        return [], None

    async def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> list[RawReview]:
        data = json.loads(payload.decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        reviews = []
        for d in items:
            rating_val, derived = normalise_rating(d.get("stars", 5), "5_star")
            rev = RawReview(
                tenant_id=self.tenant_id,
                source_id=self.id,
                channel="SITE_A_web",
                kind="review",
                source_review_id=str(d.get("review_id", "")),
                product=ProductRef(sku=d.get("sku"), name=d.get("product_name")),
                rating=RatingPayload(value=rating_val, scale="5_star", raw_value=d.get("stars"), derived=derived),
                text=d.get("review_text"),
                title=d.get("title"),
                reviewed_at=datetime.fromisoformat(d.get("created_at", datetime.now(timezone.utc).isoformat())),
                author=AuthorPayload(id_hash=d.get("customer_hash"), verified_buyer=d.get("is_verified", True)),
                order=OrderPayload(order_id=d.get("order_id"), purchase_date=d.get("order_date")),
            )
            reviews.append(rev)
        return reviews

    async def health_probe(self) -> ProbeResult:
        return ProbeResult(healthy=True, latency_ms=12, message="Site A active")


# ─────────────────────────────────────────────────────────────────────────────
# SITE_B: REST page/offset JSON, 5 half-stars, seller name + helpful votes
# ─────────────────────────────────────────────────────────────────────────────
class SiteBAdapter:
    id = "SITE_B"

    def __init__(self, tenant_id: str = "default", config: dict[str, Any] | None = None):
        self.tenant_id = tenant_id
        self.config = config or {}

    async def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]:
        return [], None

    async def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> list[RawReview]:
        data = json.loads(payload.decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        reviews = []
        for d in items:
            rating_val, derived = normalise_rating(d.get("score", 4.5), "5_half_star")
            rev = RawReview(
                tenant_id=self.tenant_id,
                source_id=self.id,
                channel="SITE_B_app",
                kind="review",
                source_review_id=str(d.get("id", "")),
                product=ProductRef(sku=d.get("product_code")),
                rating=RatingPayload(value=rating_val, scale="5_half_star", raw_value=d.get("score"), derived=derived),
                text=d.get("body"),
                title=d.get("headline"),
                reviewed_at=datetime.fromisoformat(d.get("timestamp", datetime.now(timezone.utc).isoformat())),
                author=AuthorPayload(id_hash=d.get("user_id"), review_count=d.get("helpful_votes", 0)),
                order=OrderPayload(seller=d.get("seller_name")),
            )
            reviews.append(rev)
        return reviews

    async def health_probe(self) -> ProbeResult:
        return ProbeResult(healthy=True, latency_ms=18, message="Site B active")


# ─────────────────────────────────────────────────────────────────────────────
# SITE_C: Webhook push, 5 integer stars, order id + warehouse code
# ─────────────────────────────────────────────────────────────────────────────
class SiteCAdapter:
    id = "SITE_C"

    def __init__(self, tenant_id: str = "default", config: dict[str, Any] | None = None):
        self.tenant_id = tenant_id
        self.config = config or {}

    async def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]:
        return [], None

    async def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> list[RawReview]:
        data = json.loads(payload.decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        reviews = []
        for d in items:
            rating_val, derived = normalise_rating(d.get("rating", 5), "5_star")
            rev = RawReview(
                tenant_id=self.tenant_id,
                source_id=self.id,
                channel="SITE_C_webhook",
                kind="review",
                source_review_id=str(d.get("event_id", "")),
                product=ProductRef(sku=d.get("sku")),
                rating=RatingPayload(value=rating_val, scale="5_star", raw_value=d.get("rating"), derived=derived),
                text=d.get("feedback"),
                title=None,
                reviewed_at=datetime.fromisoformat(d.get("date", datetime.now(timezone.utc).isoformat())),
                order=OrderPayload(order_id=d.get("order_id"), warehouse=d.get("warehouse_code")),
                batch_code=d.get("batch_code"),
            )
            reviews.append(rev)
        return reviews

    async def health_probe(self) -> ProbeResult:
        return ProbeResult(healthy=True, latency_ms=8, message="Site C webhook receiver ready")


# ─────────────────────────────────────────────────────────────────────────────
# SITE_D: REST ETag/If-Modified polling, 10-point scale, verified + photos
# ─────────────────────────────────────────────────────────────────────────────
class SiteDAdapter:
    id = "SITE_D"

    def __init__(self, tenant_id: str = "default", config: dict[str, Any] | None = None):
        self.tenant_id = tenant_id
        self.config = config or {}

    async def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]:
        return [], None

    async def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> list[RawReview]:
        data = json.loads(payload.decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        reviews = []
        for d in items:
            rating_val, derived = normalise_rating(d.get("rating_10", 8), "10_point")
            media_items = []
            for m in d.get("photos", []):
                media_items.append(MediaItem(media_id=m.get("id", "m1"), kind="image", url=m.get("url", "")))
            rev = RawReview(
                tenant_id=self.tenant_id,
                source_id=self.id,
                channel="SITE_D_marketplace",
                kind="review",
                source_review_id=str(d.get("post_id", "")),
                product=ProductRef(sku=d.get("product_sku")),
                rating=RatingPayload(value=rating_val, scale="10_point", raw_value=d.get("rating_10"), derived=derived),
                text=d.get("content"),
                title=d.get("subject"),
                reviewed_at=datetime.fromisoformat(d.get("posted_at", datetime.now(timezone.utc).isoformat())),
                author=AuthorPayload(verified_buyer=d.get("verified", True)),
                media=media_items,
            )
            reviews.append(rev)
        return reviews

    async def health_probe(self) -> ProbeResult:
        return ProbeResult(healthy=True, latency_ms=25, message="Site D active")


# ─────────────────────────────────────────────────────────────────────────────
# SITE_E: Thumbs up/down + text (minimal metadata stress test)
# ─────────────────────────────────────────────────────────────────────────────
class SiteEAdapter:
    id = "SITE_E"

    def __init__(self, tenant_id: str = "default", config: dict[str, Any] | None = None):
        self.tenant_id = tenant_id
        self.config = config or {}

    async def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]:
        return [], None

    async def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> list[RawReview]:
        data = json.loads(payload.decode("utf-8"))
        items = data if isinstance(data, list) else [data]
        reviews = []
        for d in items:
            rating_val, derived = normalise_rating(d.get("thumb", "up"), "thumbs")
            rev = RawReview(
                tenant_id=self.tenant_id,
                source_id=self.id,
                channel="SITE_E_quick_vote",
                kind="review",
                source_review_id=str(d.get("uid", "")),
                product=ProductRef(sku=d.get("sku")),
                rating=RatingPayload(value=rating_val, scale="thumbs", raw_value=d.get("thumb"), derived=derived),
                text=d.get("comment"),
                title=None,
                reviewed_at=datetime.now(timezone.utc),
            )
            reviews.append(rev)
        return reviews

    async def health_probe(self) -> ProbeResult:
        return ProbeResult(healthy=True, latency_ms=14, message="Site E active")


# ─────────────────────────────────────────────────────────────────────────────
# SITE_F: Scheduled CSV drop, 5 integer stars, full export with dispatch dates
# ─────────────────────────────────────────────────────────────────────────────
class SiteFAdapter:
    id = "SITE_F"

    def __init__(self, tenant_id: str = "default", config: dict[str, Any] | None = None):
        self.tenant_id = tenant_id
        self.config = config or {}

    async def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]:
        return [], None

    async def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> list[RawReview]:
        # Accepts CSV content
        content = payload.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(content))
        reviews = []
        for row in reader:
            rating_val, derived = normalise_rating(row.get("rating", 5), "5_star")
            rev = RawReview(
                tenant_id=self.tenant_id,
                source_id=self.id,
                channel="SITE_F_csv_export",
                kind="review",
                source_review_id=row.get("review_id"),
                product=ProductRef(sku=row.get("sku")),
                rating=RatingPayload(value=rating_val, scale="5_star", raw_value=row.get("rating"), derived=derived),
                text=row.get("text"),
                title=row.get("title"),
                reviewed_at=datetime.fromisoformat(row.get("reviewed_at", datetime.now(timezone.utc).isoformat())),
                order=OrderPayload(
                    order_id=row.get("order_id"),
                    warehouse=row.get("warehouse"),
                ),
                batch_code=row.get("batch_code"),
            )
            reviews.append(rev)
        return reviews

    async def health_probe(self) -> ProbeResult:
        return ProbeResult(healthy=True, latency_ms=10, message="Site F CSV processor ready")
