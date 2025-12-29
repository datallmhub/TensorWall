"""Settings management endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.core.config import settings as app_settings
from backend.core.jwt import get_current_user_id
from backend.application.auth.permissions import PermissionDependency


router = APIRouter(prefix="/settings")


# ============================================================================
# Schemas
# ============================================================================


class SystemSettings(BaseModel):
    """System settings response."""

    store_prompts: bool
    audit_retention_days: int
    default_max_tokens: int
    default_max_context: int
    max_latency_ms: int

    class Config:
        from_attributes = True


class SystemSettingsUpdate(BaseModel):
    """System settings update."""

    store_prompts: Optional[bool] = None
    audit_retention_days: Optional[int] = Field(None, ge=1, le=730)  # Max 2 years
    default_max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    default_max_context: Optional[int] = Field(None, ge=1, le=1000000)
    max_latency_ms: Optional[int] = Field(None, ge=1, le=30000)


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=SystemSettings)
async def get_system_settings(
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("settings", "read")),
):
    """
    Get current system settings.

    Requires settings:read permission.
    """
    return SystemSettings(
        store_prompts=app_settings.store_prompts,
        audit_retention_days=app_settings.audit_retention_days,
        default_max_tokens=app_settings.default_max_tokens,
        default_max_context=app_settings.default_max_context,
        max_latency_ms=app_settings.max_latency_ms,
    )


@router.patch("", response_model=SystemSettings)
async def update_system_settings(
    data: SystemSettingsUpdate,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("settings", "update")),
):
    """
    Update system settings.

    Note: These changes are in-memory and will reset on restart.
    For persistent changes, update the .env file or environment variables.

    Requires settings:update permission.
    """
    if data.store_prompts is not None:
        app_settings.store_prompts = data.store_prompts

    if data.audit_retention_days is not None:
        app_settings.audit_retention_days = data.audit_retention_days

    if data.default_max_tokens is not None:
        app_settings.default_max_tokens = data.default_max_tokens

    if data.default_max_context is not None:
        app_settings.default_max_context = data.default_max_context

    if data.max_latency_ms is not None:
        app_settings.max_latency_ms = data.max_latency_ms

    return SystemSettings(
        store_prompts=app_settings.store_prompts,
        audit_retention_days=app_settings.audit_retention_days,
        default_max_tokens=app_settings.default_max_tokens,
        default_max_context=app_settings.default_max_context,
        max_latency_ms=app_settings.max_latency_ms,
    )
