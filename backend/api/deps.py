"""
api/deps.py

Shared FastAPI dependencies:
- Async DB session (get_db)
- Multi-tenancy context (get_tenant_id)
- JWT auth & user session (get_current_user, require_role)
- API key verification
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, AsyncGenerator
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from prism_core.config.settings import Settings, get_settings
from prism_core.db.base import get_sessionmaker
from prism_core.db.models import User
from prism_core.db.repositories.users import APIKeyRepository, UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, settings: Settings) -> str:
    to_encode = data.copy()
    expire_hours = settings.jwt_expire_hours
    expire_timestamp = datetime.now(timezone.utc).timestamp() + (expire_hours * 3600)
    to_encode.update({"exp": expire_timestamp})
    secret = settings.secret_key.get_secret_value() if hasattr(settings.secret_key, "get_secret_value") else str(settings.secret_key)
    return jwt.encode(to_encode, secret, algorithm=settings.jwt_algorithm)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session per request."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_tenant_id(
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    cookie_tenant: Annotated[str | None, Cookie(alias="prism_tenant")] = None,
) -> str:
    """Resolve current tenant ID from header, cookie, or default."""
    if x_tenant_id and x_tenant_id.strip():
        return x_tenant_id.strip()
    if cookie_tenant and cookie_tenant.strip():
        return cookie_tenant.strip()
    return "default"


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    prism_token: Annotated[str | None, Cookie()] = None,
    auth_header: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    """
    Authenticate user via HttpOnly JWT cookie or Authorization Bearer header.
    Strictly verifies tenant_id.
    """
    token = prism_token
    if not token and auth_header:
        token = auth_header.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
        )

    secret = settings.secret_key.get_secret_value() if hasattr(settings.secret_key, "get_secret_value") else str(settings.secret_key)

    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        token_tenant: str | None = payload.get("tenant_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    effective_tenant = token_tenant or tenant_id
    user_repo = UserRepository(db, effective_tenant)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found")

    return user


def require_role(allowed_roles: list[str]):
    """Enforce role-based access control (e.g. ['admin'])."""
    async def _role_checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {allowed_roles}",
            )
        return user
    return _role_checker
