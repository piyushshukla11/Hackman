"""
prism_core/ingest/adapters

Adapter registry and factory for all 6 sim-sites and external sources.
"""
from __future__ import annotations

from typing import Any, Type
from prism_core.ingest.adapters.sim_sites import (
    SiteAAdapter,
    SiteBAdapter,
    SiteCAdapter,
    SiteDAdapter,
    SiteEAdapter,
    SiteFAdapter,
    normalise_rating,
)
from prism_core.ingest.sources import ReviewSource

ADAPTER_REGISTRY: dict[str, Type[Any]] = {
    "SITE_A": SiteAAdapter,
    "SITE_B": SiteBAdapter,
    "SITE_C": SiteCAdapter,
    "SITE_D": SiteDAdapter,
    "SITE_E": SiteEAdapter,
    "SITE_F": SiteFAdapter,
}


def get_adapter(adapter_name: str, tenant_id: str = "default", config: dict[str, Any] | None = None) -> ReviewSource | None:
    cls = ADAPTER_REGISTRY.get(adapter_name.upper())
    if not cls:
        return None
    return cls(tenant_id=tenant_id, config=config)


__all__ = [
    "ADAPTER_REGISTRY",
    "get_adapter",
    "normalise_rating",
    "SiteAAdapter",
    "SiteBAdapter",
    "SiteCAdapter",
    "SiteDAdapter",
    "SiteEAdapter",
    "SiteFAdapter",
]
