"""
Permission decorators and dependencies for FastAPI (OSS version)

In the OSS version, all users have full admin access.
These classes are kept for API compatibility but always allow access.
"""

from functools import wraps
from typing import Callable, List
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.core.jwt import get_current_user_id


class PermissionDependency:
    """
    Dependency class for checking permissions in FastAPI endpoints.

    OSS Version: Always allows access.
    """

    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action

    async def __call__(
        self, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)
    ):
        # OSS: All permissions are granted
        pass


class RoleDependency:
    """
    Dependency class for checking roles in FastAPI endpoints.

    OSS Version: Always allows access.
    """

    def __init__(self, role_name: str):
        self.role_name = role_name

    async def __call__(
        self, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)
    ):
        # OSS: All roles are granted
        pass


def require_permission(resource: str, action: str):
    """
    Decorator to require a specific permission for an endpoint.

    OSS Version: Always allows access.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # OSS: All permissions are granted
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role_name: str):
    """
    Decorator to require a specific role for an endpoint.

    OSS Version: Always allows access.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # OSS: All roles are granted
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permissions: List[tuple[str, str]]):
    """
    Decorator to require ANY of the specified permissions.

    OSS Version: Always allows access.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # OSS: All permissions are granted
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience functions for common permission checks (OSS: always True)
async def can_create_budget(db: AsyncSession, user_id: int) -> bool:
    """Check if user can create budgets - OSS: always True"""
    return True


async def can_delete_budget(db: AsyncSession, user_id: int) -> bool:
    """Check if user can delete budgets - OSS: always True"""
    return True


async def can_reset_budget(db: AsyncSession, user_id: int) -> bool:
    """Check if user can reset budgets - OSS: always True"""
    return True


async def can_manage_users(db: AsyncSession, user_id: int) -> bool:
    """Check if user can manage other users - OSS: always True"""
    return True


async def can_export_analytics(db: AsyncSession, user_id: int) -> bool:
    """Check if user can export analytics data - OSS: always True"""
    return True
