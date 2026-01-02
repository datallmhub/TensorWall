"""Authentication endpoints for admin dashboard."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db.models import User
from backend.core.jwt_auth import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    set_auth_cookies,
    clear_auth_cookies,
    get_current_user,
    get_role_permissions,
    AuthenticatedUser,
)
from backend.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Schemas
# ============================================================================


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response."""

    user: dict
    message: str


class UserResponse(BaseModel):
    """User info response."""

    id: int
    email: str
    name: str
    role: str
    permissions: list[str]


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str


class SetPasswordRequest(BaseModel):
    """Set initial password (for users without password)."""

    email: EmailStr
    password: str


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user with email/password.

    Sets HttpOnly cookies for access and refresh tokens.
    """
    # Find user by email
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")

    if not user.password_hash:
        raise HTTPException(
            status_code=401, detail="Password not set. Please contact administrator."
        )

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Generate tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    # Set cookies
    set_auth_cookies(response, access_token, refresh_token)

    # Get permissions
    permissions = get_role_permissions(user.role.value)

    return LoginResponse(
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "permissions": permissions,
        },
        message="Login successful",
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Logout user by clearing auth cookies.
    """
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token cookie.
    """
    refresh_token_cookie = request.cookies.get("refresh_token")

    if not refresh_token_cookie:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decode_token(refresh_token_cookie)
    if not payload or payload.type != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Fetch user
    stmt = select(User).where(User.id == payload.user_id, User.is_active.is_(True))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Generate new access token
    new_access_token = create_access_token(user)

    # Update access token cookie
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )

    return {"message": "Token refreshed"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get current authenticated user info.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        permissions=current_user.permissions,
    )


@router.post("/change-password")
async def change_password(
    data: PasswordChangeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password for authenticated user.
    """
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.password_hash or not verify_password(
        data.current_password, user.password_hash
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    user.password_hash = hash_password(data.new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Password changed successfully"}


@router.post("/set-password")
async def set_initial_password(
    data: SetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Set initial password for a user (one-time setup).

    Only works if user exists and has no password set.
    """
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.password_hash:
        raise HTTPException(status_code=400, detail="Password already set")

    if len(data.password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    user.password_hash = hash_password(data.password)
    user.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Password set successfully"}
