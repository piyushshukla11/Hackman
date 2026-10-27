"""
api/routers/catalog.py

Catalog management router:
- Products CRUD & Technical specs (for RAG context)
- Company Custom Features (GET / POST max 15 features per product)
- Product Versions & Modifications CRUD
- Manufacturing Batches CRUD
- Ingestion Sources CRUD
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_role
from prism_core.db.models import Batch, Modification, Product, ProductVersion, Source, User
from prism_core.db.repositories.catalog import (
    BatchRepository,
    ModificationRepository,
    ProductRepository,
    ProductVersionRepository,
)
from prism_core.db.repositories.ingest import SourceRepository

router = APIRouter(prefix="/v1", tags=["Catalog"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas for Catalog CRUD
# ─────────────────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    category: str
    taxonomy_id: str | None = None
    specs: dict[str, Any] = Field(default_factory=dict, description="Technical specifications for RAG context")


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    taxonomy_id: str | None = None
    specs: dict[str, Any] | None = None


class CustomFeatureItem(BaseModel):
    name: str = Field(..., description="Feature name or phrase e.g. 'ear cushion comfort'")
    description: str | None = None
    anchor_keywords: list[str] = Field(default_factory=list)


class CustomFeaturesPayload(BaseModel):
    features: list[CustomFeatureItem] = Field(..., max_length=15, description="Max 15 company custom features")


class VersionCreate(BaseModel):
    label: str
    effective_from: date
    notes: str | None = None


class ModificationCreate(BaseModel):
    product_id: str
    from_version: str
    to_version: str
    change_note: str
    target_feature: str
    target_issue_id: str | None = None
    effective_at: datetime


class BatchCreate(BaseModel):
    product_id: str
    version_id: str | None = None
    code: str
    mfg_start: date | None = None
    mfg_end: date | None = None
    ship_start: date | None = None
    ship_end: date | None = None
    warehouse: str | None = None
    notes: str | None = None


class SourceCreate(BaseModel):
    kind: str  # adapter | widget | extension | file | email
    adapter: str | None = None
    display_name: str
    config: dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Product Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/catalog/products")
@router.get("/products")
async def list_products(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
    offset: int = 0,
):
    repo = ProductRepository(db, user.tenant_id)
    return await repo.list_products(limit=limit, offset=offset)


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ProductRepository(db, user.tenant_id)
    product = Product(
        name=payload.name,
        category=payload.category,
        taxonomy_id=payload.taxonomy_id,
        specs=payload.specs,
        custom_features=[],
        tenant_id=user.tenant_id,
    )
    await repo.add(product)
    await db.flush()
    return product


@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ProductRepository(db, user.tenant_id)
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ProductRepository(db, user.tenant_id)
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.name is not None:
        product.name = payload.name
    if payload.category is not None:
        product.category = payload.category
    if payload.taxonomy_id is not None:
        product.taxonomy_id = payload.taxonomy_id
    if payload.specs is not None:
        product.specs = payload.specs

    return product


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic Company Custom Features (Max 15 per product)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/products/{product_id}/features")
async def get_custom_features(
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve company custom features defined for a product."""
    repo = ProductRepository(db, user.tenant_id)
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product_id": product_id, "custom_features": product.custom_features or []}


@router.post("/products/{product_id}/features")
async def set_custom_features(
    product_id: str,
    payload: CustomFeaturesPayload,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Define or update company custom features (max 15).
    Zero-shot semantic discovery will match reviews against these terms.
    """
    repo = ProductRepository(db, user.tenant_id)
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    features_dict = [f.model_dump() for f in payload.features]
    await repo.update_custom_features(product_id, features_dict)
    return {"status": "success", "product_id": product_id, "count": len(features_dict), "custom_features": features_dict}


# ─────────────────────────────────────────────────────────────────────────────
# Versions, Modifications, Batches & Sources
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/products/{product_id}/versions")
async def list_versions(
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ProductVersionRepository(db, user.tenant_id)
    return await repo.list_by_product(product_id)


@router.post("/products/{product_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_version(
    product_id: str,
    payload: VersionCreate,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ProductVersionRepository(db, user.tenant_id)
    version = ProductVersion(
        product_id=product_id,
        label=payload.label,
        effective_from=payload.effective_from,
        notes=payload.notes,
        tenant_id=user.tenant_id,
    )
    await repo.add(version)
    await db.flush()
    return version


@router.get("/modifications")
async def list_modifications(
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ModificationRepository(db, user.tenant_id)
    return await repo.list_by_product(product_id)


@router.post("/modifications", status_code=status.HTTP_201_CREATED)
async def create_modification(
    payload: ModificationCreate,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = ModificationRepository(db, user.tenant_id)
    mod = Modification(
        product_id=payload.product_id,
        from_version=payload.from_version,
        to_version=payload.to_version,
        change_note=payload.change_note,
        target_feature=payload.target_feature,
        target_issue_id=payload.target_issue_id,
        effective_at=payload.effective_at,
        tenant_id=user.tenant_id,
    )
    await repo.add(mod)
    await db.flush()
    return mod


@router.get("/batches")
async def list_batches(
    product_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = BatchRepository(db, user.tenant_id)
    return await repo.list_by_product(product_id)


@router.post("/batches", status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: BatchCreate,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = BatchRepository(db, user.tenant_id)
    batch = Batch(
        product_id=payload.product_id,
        version_id=payload.version_id,
        code=payload.code,
        mfg_start=payload.mfg_start,
        mfg_end=payload.mfg_end,
        ship_start=payload.ship_start,
        ship_end=payload.ship_end,
        warehouse=payload.warehouse,
        notes=payload.notes,
        tenant_id=user.tenant_id,
    )
    await repo.add(batch)
    await db.flush()
    return batch


@router.get("/sources")
async def list_sources(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = SourceRepository(db, user.tenant_id)
    return await repo.list_sources()


@router.post("/sources", status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: SourceCreate,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = SourceRepository(db, user.tenant_id)
    src = Source(
        kind=payload.kind,
        adapter=payload.adapter,
        display_name=payload.display_name,
        config=payload.config,
        tenant_id=user.tenant_id,
    )
    await repo.add(src)
    await db.flush()
    return src
