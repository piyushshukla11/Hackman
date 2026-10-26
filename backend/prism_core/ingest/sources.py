"""
prism_core/ingest/sources.py

ReviewSource protocol and adapter probe interfaces.
All 6 sim-site adapters and production adapters implement this protocol.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from prism_core.schemas.ops import ProbeResult
from prism_core.schemas.raw_review import RawReview


@runtime_checkable
class ReviewSource(Protocol):
    id: str

    async def pull(self, cursor: str | None) -> tuple[list[RawReview], str | None]:
        """Pull reviews from source using cursor pagination. Returns (reviews, next_cursor)."""
        ...

    async def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> list[RawReview]:
        """Parse incoming push webhook into RawReview envelopes."""
        ...

    async def health_probe(self) -> ProbeResult:
        """Run health and connectivity probe."""
        ...
