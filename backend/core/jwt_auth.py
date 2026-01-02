"""JWT Authentication for admin dashboard users."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import HTTPException, Request, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import settings
from backend.db.session import get_db
from backend.db.models import User
from backend.core.rbac import Role, ROLE_PERMISSIONS

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user email
    user_id: int
    role: str
    exp: datetime
    type: str  # "access" or "refresh"


class AuthenticatedUser(BaseModel):
    """Authenticated user data."""

    id: int
    email: str
    name: str
    role: str
    permissions: list[str]

    class Config:
        from_attributes = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(user: User) -> str:
    """Create a short-lived access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": user.email,
        "user_id": user.id,
        "role": user.role.value,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(user: User) -> str:
    """Create a long-lived refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": user.email,
        "user_id": user.id,
        "role": user.role.value,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return TokenPayload(**payload)
    except JWTError:
        return None


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set authentication cookies on response."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def get_role_permissions(role_value: str) -> list[str]:
    """Get permissions for a role."""
    try:
        role = Role(role_value)
        permissions = ROLE_PERMISSIONS.get(role, set())
        return [p.value for p in permissions]
    except ValueError:
        return []


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """
    Get the current authenticated user from JWT cookie.

    Raises HTTPException 401 if not authenticated.
    """
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    if not payload or payload.type != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fetch user from database to ensure they still exist and are active
    stmt = select(User).where(User.id == payload.user_id, User.is_active.is_(True))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    # Get permissions from RBAC
    permissions = get_role_permissions(user.role.value)

    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        permissions=permissions,
    )


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[AuthenticatedUser]:
    """Get current user if authenticated, None otherwise."""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
