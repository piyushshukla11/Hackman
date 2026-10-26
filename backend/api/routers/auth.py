"""
api/routers/auth.py

Authentication and Role Onboarding Router:
- Register, Login (HttpOnly JWT cookie), Logout
- First-login role onboarding: save custom role title & selected module views
- Persona quick switcher (QA, CX, PM, Exec)
- API key generation
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import (
    create_access_token,
    get_current_user,
    get_db,
    get_tenant_id,
    hash_password,
    require_role,
    verify_password,
)
from prism_core.config.settings import Settings, get_settings
from prism_core.db.models import APIKey, User
from prism_core.db.repositories.users import APIKeyRepository, UserRepository
from prism_core.schemas.ops import OnboardingPayload, PersonaPresetPayload, UserProfile

router = APIRouter(tags=["Auth"])

# Persona Presets for the 1-Click Judge Quick Switcher
PERSONA_PRESETS = {
    "qa": {
        "role_title": "Senior QA Lead",
        "views": ["issues", "defect_concentration", "batches", "xray", "audit_drawer"],
    },
    "cx": {
        "role_title": "Head of Customer Experience",
        "views": ["serious_queue", "surveys", "language_breakdown", "sentiment_trends"],
    },
    "pm": {
        "role_title": "Principal Product Manager",
        "views": ["overview", "comparisons", "version_impact", "feature_matrix", "custom_features"],
    },
    "exec": {
        "role_title": "VP of Engineering & Quality",
        "views": ["health_index", "executive_summary", "returns_lead_time", "reports"],
    },
}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "member"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class APIKeyCreateRequest(BaseModel):
    name: str
    role: str = "admin"


class APIKeyResponse(BaseModel):
    id: str
    name: str
    api_key: str
    role: str


@router.post("/auth/register", response_model=UserProfile)
async def register(
    req: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
):
    user_repo = UserRepository(db, tenant_id)
    existing = await user_repo.get_by_email(req.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered in this tenant")

    new_user = User(
        email=req.email.lower().strip(),
        password_hash=hash_password(req.password),
        role=req.role,
        tenant_id=tenant_id,
        has_completed_onboarding=False,
    )
    await user_repo.add(new_user)
    await db.flush()

    return UserProfile(
        id=new_user.id,
        email=new_user.email,
        role=new_user.role,
        role_title=new_user.role_title,
        selected_views=new_user.selected_views or [],
        has_completed_onboarding=new_user.has_completed_onboarding,
        tenant_id=new_user.tenant_id,
    )


@router.post("/auth/login")
async def login(
    req: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
):
    user_repo = UserRepository(db, tenant_id)
    user = await user_repo.get_by_email(req.email)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role}, settings)

    # Set HttpOnly JWT cookie (8 hours expiry)
    response.set_cookie(
        key="prism_token",
        value=token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.jwt_expire_hours * 3600,
    )
    # Also set a readable tenant cookie
    response.set_cookie(key="prism_tenant", value=user.tenant_id, samesite="lax", max_age=settings.jwt_expire_hours * 3600)

    return {
        "status": "success",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "role_title": user.role_title,
            "selected_views": user.selected_views or [],
            "has_completed_onboarding": user.has_completed_onboarding,
            "tenant_id": user.tenant_id,
        },
        "token": token,
    }


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="prism_token")
    return {"status": "logged_out"}


@router.get("/auth/me", response_model=UserProfile)
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    return UserProfile(
        id=user.id,
        email=user.email,
        role=user.role,
        role_title=user.role_title,
        selected_views=user.selected_views or [],
        has_completed_onboarding=user.has_completed_onboarding,
        tenant_id=user.tenant_id,
    )


@router.post("/auth/onboarding", response_model=UserProfile)
async def complete_onboarding(
    payload: OnboardingPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Save user custom role title and selected views upon first login."""
    user_repo = UserRepository(db, user.tenant_id)
    updated = await user_repo.update_onboarding(user.id, payload.role_title, payload.selected_views)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfile(
        id=updated.id,
        email=updated.email,
        role=updated.role,
        role_title=updated.role_title,
        selected_views=updated.selected_views or [],
        has_completed_onboarding=updated.has_completed_onboarding,
        tenant_id=updated.tenant_id,
    )


@router.patch("/auth/me/preferences", response_model=UserProfile)
async def update_preferences(
    payload: PersonaPresetPayload,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """1-Click Persona quick-switcher for demo & testing (QA, CX, PM, Exec)."""
    preset = PERSONA_PRESETS.get(payload.persona)
    if not preset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown persona: {payload.persona}")

    user_repo = UserRepository(db, user.tenant_id)
    updated = await user_repo.update_onboarding(user.id, preset["role_title"], preset["views"])

    return UserProfile(
        id=updated.id,
        email=updated.email,
        role=updated.role,
        role_title=updated.role_title,
        selected_views=updated.selected_views or [],
        has_completed_onboarding=updated.has_completed_onboarding,
        tenant_id=updated.tenant_id,
    )


@router.post("/keys", response_model=APIKeyResponse)
async def create_api_key(
    req: APIKeyCreateRequest,
    user: Annotated[User, Depends(require_role(["admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin-only API key generation for adapters or external pipelines."""
    raw_key = f"prism_key_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    key_repo = APIKeyRepository(db, user.tenant_id)
    new_key = APIKey(
        tenant_id=user.tenant_id,
        key_hash=key_hash,
        name=req.name,
        role=req.role,
    )
    await key_repo.add(new_key)
    await db.flush()

    return APIKeyResponse(
        id=new_key.id,
        name=new_key.name,
        api_key=raw_key,
        role=new_key.role,
    )
