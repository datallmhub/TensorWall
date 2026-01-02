"""
Ownership and Context-Based Access Control (OSS version)

In the OSS version, all users have full admin access.
These functions are kept for API compatibility but always allow access.
"""

from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import User, Application, Budget, PolicyRule


class AccessDeniedError(HTTPException):
    """Raised when user tries to access a resource they don't own."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You don't have permission to access this {resource_type} (ID: {resource_id})",
        )


class ResourceNotFoundError(HTTPException):
    """Raised when a resource doesn't exist."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type} not found (ID: {resource_id})",
        )


async def get_user_by_uuid(
    db: AsyncSession, user_uuid: UUID, requesting_user_id: int
) -> User:
    """
    Get user by UUID - OSS: all users can access all users.
    """
    result = await db.execute(select(User).where(User.uuid == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFoundError("User", str(user_uuid))

    # OSS: All users have full access
    return user


async def get_application_by_uuid(
    db: AsyncSession, app_uuid: UUID, user_id: int
) -> Application:
    """
    Get application by UUID - OSS: all users can access all applications.
    """
    result = await db.execute(select(Application).where(Application.uuid == app_uuid))
    app = result.scalar_one_or_none()

    if not app:
        raise ResourceNotFoundError("Application", str(app_uuid))

    # OSS: All users have full access
    return app


async def get_application_by_app_id(
    db: AsyncSession, app_id: str, user_id: int
) -> Application:
    """
    Get application by app_id - OSS: all users can access all applications.
    """
    result = await db.execute(select(Application).where(Application.app_id == app_id))
    app = result.scalar_one_or_none()

    if not app:
        raise ResourceNotFoundError("Application", app_id)

    # OSS: All users have full access
    return app


async def get_budget_by_uuid(
    db: AsyncSession, budget_uuid: UUID, user_id: int
) -> Budget:
    """
    Get budget by UUID - OSS: all users can access all budgets.
    """
    result = await db.execute(select(Budget).where(Budget.uuid == budget_uuid))
    budget = result.scalar_one_or_none()

    if not budget:
        raise ResourceNotFoundError("Budget", str(budget_uuid))

    # OSS: All users have full access
    return budget


async def get_policy_by_uuid(
    db: AsyncSession, policy_uuid: UUID, user_id: int
) -> PolicyRule:
    """
    Get policy by UUID - OSS: all users can access all policies.
    """
    result = await db.execute(select(PolicyRule).where(PolicyRule.uuid == policy_uuid))
    policy = result.scalar_one_or_none()

    if not policy:
        raise ResourceNotFoundError("Policy", str(policy_uuid))

    # OSS: All users have full access
    return policy


async def can_modify_user(
    db: AsyncSession, target_user: User, requesting_user_id: int
) -> bool:
    """
    Check if requesting user can modify target user - OSS: always True.
    """
    return True


async def can_delete_user(
    db: AsyncSession, target_user: User, requesting_user_id: int
) -> bool:
    """
    Check if requesting user can delete target user - OSS: always True except self.
    """
    if target_user.id == requesting_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    return True


async def validate_budget_scope_access(
    db: AsyncSession, budget: Budget, user_id: int
) -> bool:
    """
    Validate that user has access to budget - OSS: always True.
    """
    return True
