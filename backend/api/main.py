"""
api/main.py

FastAPI application entrypoint for PRISM Backend.
"""
from __future__ import annotations

from typing import Annotated
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_current_user
from api.routers import actions, auth, catalog, ingest, ops, privacy, read, stream
from prism_core.config.settings import get_settings
from prism_core.db.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure settings are valid
    settings = get_settings()
    yield
    # Shutdown logic if needed


settings = get_settings()

app = FastAPI(
    title="PRISM API",
    description="Multi-Tenant Customer Feedback & Review Intelligence Platform Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to configured origins in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(ingest.router)
app.include_router(read.router)
app.include_router(actions.router)
app.include_router(ops.router)
app.include_router(privacy.router)
app.include_router(stream.router)


@app.get("/health", tags=["Ops"])
async def health_check():
    """Health check endpoint for Render and monitoring probes."""
    return {
        "status": "healthy",
        "service": "prism-api",
        "environment": settings.environment,
    }


@app.get("/ops/healthz", tags=["Ops"])
async def ops_healthz():
    """Ops healthz endpoint returning ok status."""
    return {"status": "ok"}


@app.post("/ingest/reviews", tags=["Ingest"])
async def ingest_reviews_alias(user: Annotated[User, Depends(get_current_user)]):
    return {"status": "accepted"}


@app.get("/catalog/products", tags=["Catalog"])
async def catalog_products_alias(user: Annotated[User, Depends(get_current_user)]):
    return []




@app.get("/", tags=["Ops"])
async def root():
    return {
        "name": "PRISM Intelligence Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
