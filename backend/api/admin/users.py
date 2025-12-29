"""
Admin Users API -

Provides basic user management for admin access.

OSS Features:
- List admin users
- Create/delete users
- Reset passwords
- Enable/disable users

All users have full admin access .
All users have full admin access.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.db.models import User, UserRole
from backend.core.jwt import get_current_user_id
from backend.core.jwt_auth import hash_password

router = APIRouter(prefix="/users")


# ============================================================================
# Response Models
# ============================================================================


class UserItem(BaseModel):
    """User list item."""

    id: int
    uuid: str
    email: str
    name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserList(BaseModel):
    """Paginated user list."""

    items: list[UserItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserCreate(BaseModel):
    """Create user request."""

    email: EmailStr
    name: str
    password: Optional[str] = None  # If not provided, user must set via /auth/set-password


class UserUpdate(BaseModel):
    """Update user request."""

    name: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    new_password: str


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=UserList)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=10, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    List all admin users.

    All users have full admin access.
    """
    # Count total
    count_query = select(func.count(User.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get users
    offset = (page - 1) * page_size
    query = select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    items = [
        UserItem(
            id=u.id,
            uuid=str(u.uuid),
            email=u.email,
            name=u.name,
            role=u.role.value,
            is_active=u.is_active,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in users
    ]

    total_pages = (total + page_size - 1) // page_size

    return UserList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=UserItem, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Create a new admin user.

    New users get 'admin' role (full access).
    If password is not provided, user must set it via /auth/set-password.
    """
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create user with admin role (OSS)
    user = User(
        email=data.email,
        name=data.name,
        role=UserRole.ADMIN,  # All users are admins
        password_hash=hash_password(data.password) if data.password else None,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserItem(
        id=user.id,
        uuid=str(user.uuid),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.get("/{user_id}", response_model=UserItem)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """Get user details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserItem(
        id=user.id,
        uuid=str(user.uuid),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.patch("/{user_id}", response_model=UserItem)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Update user details.

    Can update name and active status.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent self-deactivation
    if data.is_active is False and user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself"
        )

    if data.name is not None:
        user.name = data.name
    if data.is_active is not None:
        user.is_active = data.is_active

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    return UserItem(
        id=user.id,
        uuid=str(user.uuid),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Delete a user.

    Cannot delete yourself.
    """
    if user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()


@router.post("/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_user_password(
    user_id: int,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Reset a user's password (admin action).

    Password must be at least 8 characters.
    """
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = hash_password(data.new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Password reset successfully"}
