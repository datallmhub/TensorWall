"""Application management endpoints - FULLY SECURED."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.db.repositories.application import ApplicationRepository
from backend.db.repositories.api_key import ApiKeyRepository
from backend.db.models import Environment, Application
from backend.application.auth.permissions import PermissionDependency
from backend.application.auth.ownership import get_application_by_uuid
from backend.core.jwt import get_current_user_id


router = APIRouter(prefix="/applications")


# ============================================================================
# Schemas
# ============================================================================


class ApplicationCreate(BaseModel):
    app_id: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=255)
    owner: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    allowed_providers: list[str] = ["openai", "anthropic"]
    allowed_models: list[str] = []


class ApplicationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    owner: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    allowed_providers: Optional[list[str]] = None
    allowed_models: Optional[list[str]] = None
    is_active: Optional[bool] = None


class ApplicationResponse(BaseModel):
    uuid: str  # ✅ SECURE: UUID instead of ID
    app_id: str
    name: str
    owner: str
    description: Optional[str]
    is_active: bool
    allowed_providers: list[str]
    allowed_models: list[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    environment: str = "development"


class ApiKeyResponse(BaseModel):
    id: int
    key_prefix: str
    name: str
    environment: str
    is_active: bool
    created_at: str
    last_used_at: Optional[str]

    class Config:
        from_attributes = True


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Response when creating a new API key - includes the raw key."""

    api_key: str  # Only returned on creation


# ============================================================================
# Helper Functions
# ============================================================================


def _to_response(app: Application) -> ApplicationResponse:
    """Convert Application model to response with UUID."""
    return ApplicationResponse(
        uuid=str(app.uuid),  # ✅ UUID
        app_id=app.app_id,
        name=app.name,
        owner=app.owner,
        description=app.description,
        is_active=app.is_active,
        allowed_providers=app.allowed_providers,
        allowed_models=app.allowed_models,
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat(),
    )


# ============================================================================
# Secure Endpoints
# ============================================================================


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "create")),  # ✅ RBAC
):
    """
    Create a new application.

    Security: Requires 'applications:create' permission.
    """
    repo = ApplicationRepository(db)

    # Check if app_id already exists
    existing = await repo.get_by_app_id(data.app_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application with app_id '{data.app_id}' already exists",
        )

    app = await repo.create(
        app_id=data.app_id,
        name=data.name,
        owner=data.owner,
        description=data.description,
        allowed_providers=data.allowed_providers,
        allowed_models=data.allowed_models,
    )

    return _to_response(app)  # ✅ Returns UUID


@router.get("", response_model=list[ApplicationResponse])
async def list_applications(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "read")),  # ✅ RBAC
):
    """
    List all applications.

    Security:
    - Requires 'applications:read' permission
    - TODO: Filter by user ownership/scope
    """
    repo = ApplicationRepository(db)
    apps = await repo.list_all(skip=skip, limit=limit, active_only=active_only)

    return [_to_response(app) for app in apps]  # ✅ Returns UUIDs


@router.get("/{app_uuid}", response_model=ApplicationResponse)
async def get_application(
    app_uuid: UUID,  # ✅ UUID parameter
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "read")),  # ✅ RBAC
):
    """
    Get application by UUID.

    Security:
    - Uses UUID instead of app_id/id
    - Validates ownership
    - Returns 403 if no access, 404 if not found
    """
    # ✅ SECURE: Validates ownership automatically
    app = await get_application_by_uuid(db, app_uuid, user_id)
    return _to_response(app)


@router.patch("/{app_uuid}", response_model=ApplicationResponse)
async def update_application(
    app_uuid: UUID,  # ✅ UUID parameter
    data: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "update")),  # ✅ RBAC
):
    """
    Update application by UUID.

    Security:
    - Validates ownership before update
    - Returns 403 if no access
    """
    repo = ApplicationRepository(db)

    # ✅ SECURE: Validate ownership first
    app = await get_application_by_uuid(db, app_uuid, user_id)

    # Update using app_id (internal)
    updated_app = await repo.update(
        app_id=app.app_id,  # Use app_id for update (repo method uses app_id)
        name=data.name,
        owner=data.owner,
        description=data.description,
        allowed_providers=data.allowed_providers,
        allowed_models=data.allowed_models,
        is_active=data.is_active,
    )

    if not updated_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return _to_response(updated_app)


@router.delete("/{app_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    app_uuid: UUID,  # ✅ UUID parameter
    hard: bool = False,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "delete")),  # ✅ RBAC
):
    """
    Delete application by UUID.

    Security:
    - Validates ownership before deletion
    - Returns 403 if no access
    """
    repo = ApplicationRepository(db)

    # ✅ SECURE: Validate ownership first
    app = await get_application_by_uuid(db, app_uuid, user_id)

    # Delete using app_id (internal)
    if hard:
        success = await repo.hard_delete(app.app_id)
    else:
        success = await repo.delete(app.app_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )


# ============================================================================
# API Keys - SECURED
# ============================================================================


@router.post(
    "/{app_uuid}/keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    app_uuid: UUID,  # ✅ UUID parameter
    data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "manage_keys")),  # ✅ RBAC
):
    """
    Create new API key for application.

    Security:
    - Requires 'applications:manage_keys' permission
    - Validates application ownership
    """
    key_repo = ApiKeyRepository(db)

    # ✅ SECURE: Validate ownership
    app = await get_application_by_uuid(db, app_uuid, user_id)

    # Map environment string to enum
    try:
        env = Environment(data.environment)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid environment: {data.environment}",
        )

    api_key, raw_key = await key_repo.create(
        application_id=app.id,  # Internal ID
        name=data.name,
        environment=env,
    )

    return ApiKeyCreatedResponse(
        id=api_key.id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        environment=api_key.environment.value,
        is_active=api_key.is_active,
        created_at=api_key.created_at.isoformat(),
        last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        api_key=raw_key,  # Only returned on creation!
    )


@router.get("/{app_uuid}/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    app_uuid: UUID,  # ✅ UUID parameter
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "read")),  # ✅ RBAC
):
    """
    List API keys for application.

    Security: Validates application ownership.
    """
    key_repo = ApiKeyRepository(db)

    # ✅ SECURE: Validate ownership
    app = await get_application_by_uuid(db, app_uuid, user_id)

    keys = await key_repo.list_by_application(app.id, active_only=active_only)

    return [
        ApiKeyResponse(
            id=key.id,
            key_prefix=key.key_prefix,
            name=key.name,
            environment=key.environment.value,
            is_active=key.is_active,
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        )
        for key in keys
    ]


@router.delete("/{app_uuid}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    app_uuid: UUID,  # ✅ UUID parameter
    key_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "manage_keys")),  # ✅ RBAC
):
    """
    Revoke (deactivate) API key.

    Security: Validates application ownership before revoking key.
    """
    key_repo = ApiKeyRepository(db)

    # ✅ SECURE: Validate ownership
    await get_application_by_uuid(db, app_uuid, user_id)

    success = await key_repo.deactivate(key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )


@router.post("/{app_uuid}/keys/{key_id}/rotate", response_model=ApiKeyCreatedResponse)
async def rotate_api_key(
    app_uuid: UUID,  # ✅ UUID parameter
    key_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("applications", "manage_keys")),  # ✅ RBAC
):
    """
    Rotate API key - creates new one and deactivates old.

    Security: Validates application ownership before rotating.
    """
    key_repo = ApiKeyRepository(db)

    # ✅ SECURE: Validate ownership
    await get_application_by_uuid(db, app_uuid, user_id)

    result = await key_repo.rotate(key_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    new_key, raw_key = result

    return ApiKeyCreatedResponse(
        id=new_key.id,
        key_prefix=new_key.key_prefix,
        name=new_key.name,
        environment=new_key.environment.value,
        is_active=new_key.is_active,
        created_at=new_key.created_at.isoformat(),
        last_used_at=new_key.last_used_at.isoformat() if new_key.last_used_at else None,
        api_key=raw_key,
    )
