"""
prism_core/db/repositories/catalog.py

Repositories for Catalog entities: Products, Versions, Batches, Modifications, Taxonomies.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.db.models import Batch, FeatureTaxonomy, Modification, Product, ProductVersion
from prism_core.db.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(Product, session, tenant_id)

    async def list_products(self, limit: int = 100, offset: int = 0) -> list[Product]:
        stmt = self._scoped_query().limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_custom_features(self, product_id: str, custom_features: list[dict[str, Any]]) -> Product | None:
        """Update company custom features, strictly capped at 15 items."""
        if len(custom_features) > 15:
            raise ValueError("Company custom features are limited to a maximum of 15 features per product.")
        product = await self.get_by_id(product_id)
        if product:
            product.custom_features = custom_features
        return product


class ProductVersionRepository(BaseRepository[ProductVersion]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(ProductVersion, session, tenant_id)

    async def list_by_product(self, product_id: str) -> list[ProductVersion]:
        stmt = self._scoped_query(ProductVersion.product_id == product_id).order_by(ProductVersion.effective_from.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class BatchRepository(BaseRepository[Batch]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(Batch, session, tenant_id)

    async def list_by_product(self, product_id: str) -> list[Batch]:
        stmt = self._scoped_query(Batch.product_id == product_id).order_by(Batch.mfg_start.desc().nullslast())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_code(self, product_id: str, code: str) -> Batch | None:
        stmt = self._scoped_query(Batch.product_id == product_id, Batch.code == code)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class ModificationRepository(BaseRepository[Modification]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(Modification, session, tenant_id)

    async def list_by_product(self, product_id: str) -> list[Modification]:
        stmt = self._scoped_query(Modification.product_id == product_id).order_by(Modification.effective_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class FeatureTaxonomyRepository(BaseRepository[FeatureTaxonomy]):
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(FeatureTaxonomy, session, tenant_id)

    async def get_by_category(self, category: str) -> FeatureTaxonomy | None:
        stmt = self._scoped_query(FeatureTaxonomy.category == category)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
