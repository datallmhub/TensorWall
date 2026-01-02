"""Feature management endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.application.engines.features import (
    feature_engine,
    FeatureConfig,
    FeatureRegistry,
    FeatureAction,
)
from backend.core.jwt import get_current_user_id
from backend.application.auth.permissions import PermissionDependency
from backend.application.auth.ownership import get_application_by_app_id


router = APIRouter(prefix="/features")


# ============================================================================
# Schemas
# ============================================================================


class FeatureCreate(BaseModel):
    """Create a feature."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    enabled: bool = True

    # Action restrictions
    allowed_actions: list[str] = ["generate", "chat"]

    # Model restrictions
    allowed_models: list[str] = []
    denied_models: list[str] = []

    # Token limits
    max_input_tokens: Optional[int] = Field(None, gt=0)
    max_output_tokens: Optional[int] = Field(None, gt=0)

    # Environment restrictions
    allowed_environments: list[str] = []
    denied_environments: list[str] = []

    # Output constraints
    require_json_output: bool = False
    json_schema: Optional[dict] = None

    # Rate limits
    rate_limit_per_minute: Optional[int] = Field(None, gt=0)
    rate_limit_per_hour: Optional[int] = Field(None, gt=0)

    # Cost controls
    max_cost_per_request_usd: Optional[float] = Field(None, gt=0)


class FeatureResponse(BaseModel):
    """Feature response."""

    name: str
    description: Optional[str]
    enabled: bool
    allowed_actions: list[str]
    allowed_models: list[str]
    denied_models: list[str]
    max_input_tokens: Optional[int]
    max_output_tokens: Optional[int]
    allowed_environments: list[str]
    denied_environments: list[str]
    require_json_output: bool
    rate_limit_per_minute: Optional[int]
    rate_limit_per_hour: Optional[int]
    max_cost_per_request_usd: Optional[float]


class RegistryCreate(BaseModel):
    """Create a feature registry for an app."""

    strict_mode: bool = True
    default_feature: Optional[str] = None
    global_allowed_models: list[str] = []
    global_denied_models: list[str] = []


class RegistryResponse(BaseModel):
    """Feature registry response."""

    app_id: str
    strict_mode: bool
    default_feature: Optional[str]
    global_allowed_models: list[str]
    global_denied_models: list[str]
    feature_count: int
    features: list[str]


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/{app_id}/registry",
    response_model=RegistryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_registry(
    app_id: str,
    data: RegistryCreate,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("features", "create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update a feature registry for an application.

    Requires features:create permission and application ownership.
    """
    # Validate ownership
    await get_application_by_app_id(db, app_id, user_id)
    registry = FeatureRegistry(
        app_id=app_id,
        strict_mode=data.strict_mode,
        default_feature=data.default_feature,
        global_allowed_models=data.global_allowed_models,
        global_denied_models=data.global_denied_models,
    )

    feature_engine.register_app(registry)

    return RegistryResponse(
        app_id=app_id,
        strict_mode=registry.strict_mode,
        default_feature=registry.default_feature,
        global_allowed_models=registry.global_allowed_models,
        global_denied_models=registry.global_denied_models,
        feature_count=len(registry.features),
        features=list(registry.features.keys()),
    )


@router.get("/{app_id}/registry", response_model=RegistryResponse)
async def get_registry(
    app_id: str,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("features", "read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get feature registry for an application.

    Requires features:read permission and application ownership.
    """
    # Validate ownership
    await get_application_by_app_id(db, app_id, user_id)
    registry = feature_engine.get_registry(app_id)

    if not registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No feature registry found for app '{app_id}'",
        )

    return RegistryResponse(
        app_id=app_id,
        strict_mode=registry.strict_mode,
        default_feature=registry.default_feature,
        global_allowed_models=registry.global_allowed_models,
        global_denied_models=registry.global_denied_models,
        feature_count=len(registry.features),
        features=list(registry.features.keys()),
    )


@router.post(
    "/{app_id}", response_model=FeatureResponse, status_code=status.HTTP_201_CREATED
)
async def create_feature(
    app_id: str,
    data: FeatureCreate,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("features", "create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new feature for an application.

    Requires features:create permission and application ownership.
    """
    # Validate ownership
    await get_application_by_app_id(db, app_id, user_id)
    # Validate actions
    try:
        allowed_actions = [FeatureAction(a) for a in data.allowed_actions]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {e}",
        )

    config = FeatureConfig(
        name=data.name,
        description=data.description,
        enabled=data.enabled,
        allowed_actions=allowed_actions,
        allowed_models=data.allowed_models,
        denied_models=data.denied_models,
        max_input_tokens=data.max_input_tokens,
        max_output_tokens=data.max_output_tokens,
        allowed_environments=data.allowed_environments,
        denied_environments=data.denied_environments,
        require_json_output=data.require_json_output,
        json_schema=data.json_schema,
        rate_limit_per_minute=data.rate_limit_per_minute,
        rate_limit_per_hour=data.rate_limit_per_hour,
        max_cost_per_request_usd=data.max_cost_per_request_usd,
    )

    feature_engine.add_feature(app_id, config)

    return FeatureResponse(
        name=config.name,
        description=config.description,
        enabled=config.enabled,
        allowed_actions=[a.value for a in config.allowed_actions],
        allowed_models=config.allowed_models,
        denied_models=config.denied_models,
        max_input_tokens=config.max_input_tokens,
        max_output_tokens=config.max_output_tokens,
        allowed_environments=config.allowed_environments,
        denied_environments=config.denied_environments,
        require_json_output=config.require_json_output,
        rate_limit_per_minute=config.rate_limit_per_minute,
        rate_limit_per_hour=config.rate_limit_per_hour,
        max_cost_per_request_usd=config.max_cost_per_request_usd,
    )


@router.get("/{app_id}", response_model=list[FeatureResponse])
async def list_features(
    app_id: str,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("features", "read")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all features for an application.

    Requires features:read permission and application ownership.
    """
    # Validate ownership
    await get_application_by_app_id(db, app_id, user_id)
    features = feature_engine.list_features(app_id)

    return [
        FeatureResponse(
            name=f.name,
            description=f.description,
            enabled=f.enabled,
            allowed_actions=[a.value for a in f.allowed_actions],
            allowed_models=f.allowed_models,
            denied_models=f.denied_models,
            max_input_tokens=f.max_input_tokens,
            max_output_tokens=f.max_output_tokens,
            allowed_environments=f.allowed_environments,
            denied_environments=f.denied_environments,
            require_json_output=f.require_json_output,
            rate_limit_per_minute=f.rate_limit_per_minute,
            rate_limit_per_hour=f.rate_limit_per_hour,
            max_cost_per_request_usd=f.max_cost_per_request_usd,
        )
        for f in features
    ]


@router.get("/{app_id}/{feature_name}", response_model=FeatureResponse)
async def get_feature(
    app_id: str,
    feature_name: str,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("features", "read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific feature.

    Requires features:read permission and application ownership.
    """
    # Validate ownership
    await get_application_by_app_id(db, app_id, user_id)
    registry = feature_engine.get_registry(app_id)

    if not registry or feature_name not in registry.features:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature '{feature_name}' not found for app '{app_id}'",
        )

    f = registry.features[feature_name]

    return FeatureResponse(
        name=f.name,
        description=f.description,
        enabled=f.enabled,
        allowed_actions=[a.value for a in f.allowed_actions],
        allowed_models=f.allowed_models,
        denied_models=f.denied_models,
        max_input_tokens=f.max_input_tokens,
        max_output_tokens=f.max_output_tokens,
        allowed_environments=f.allowed_environments,
        denied_environments=f.denied_environments,
        require_json_output=f.require_json_output,
        rate_limit_per_minute=f.rate_limit_per_minute,
        rate_limit_per_hour=f.rate_limit_per_hour,
        max_cost_per_request_usd=f.max_cost_per_request_usd,
    )


@router.delete("/{app_id}/{feature_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature(
    app_id: str,
    feature_name: str,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("features", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a feature.

    Requires features:delete permission and application ownership.
    """
    # Validate ownership
    await get_application_by_app_id(db, app_id, user_id)
    success = feature_engine.remove_feature(app_id, feature_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature '{feature_name}' not found for app '{app_id}'",
        )


@router.post("/{app_id}/{feature_name}/enable", response_model=FeatureResponse)
async def enable_feature(
    app_id: str,
    feature_name: str,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("features", "update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Enable a feature.

    Requires features:update permission and application ownership.
    """
    # Validate ownership
    await get_application_by_app_id(db, app_id, user_id)
    registry = feature_engine.get_registry(app_id)

    if not registry or feature_name not in registry.features:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature '{feature_name}' not found",
        )

    registry.features[feature_name].enabled = True
    f = registry.features[feature_name]

    return FeatureResponse(
        name=f.name,
        description=f.description,
        enabled=f.enabled,
        allowed_actions=[a.value for a in f.allowed_actions],
        allowed_models=f.allowed_models,
        denied_models=f.denied_models,
        max_input_tokens=f.max_input_tokens,
        max_output_tokens=f.max_output_tokens,
        allowed_environments=f.allowed_environments,
        denied_environments=f.denied_environments,
        require_json_output=f.require_json_output,
        rate_limit_per_minute=f.rate_limit_per_minute,
        rate_limit_per_hour=f.rate_limit_per_hour,
        max_cost_per_request_usd=f.max_cost_per_request_usd,
    )


@router.post("/{app_id}/{feature_name}/disable", response_model=FeatureResponse)
async def disable_feature(
    app_id: str,
    feature_name: str,
    user_id: int = Depends(get_current_user_id),
    _: None = Depends(PermissionDependency("features", "update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Disable a feature.

    Requires features:update permission and application ownership.
    """
    # Validate ownership
    await get_application_by_app_id(db, app_id, user_id)
    registry = feature_engine.get_registry(app_id)

    if not registry or feature_name not in registry.features:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature '{feature_name}' not found",
        )

    registry.features[feature_name].enabled = False
    f = registry.features[feature_name]

    return FeatureResponse(
        name=f.name,
        description=f.description,
        enabled=f.enabled,
        allowed_actions=[a.value for a in f.allowed_actions],
        allowed_models=f.allowed_models,
        denied_models=f.denied_models,
        max_input_tokens=f.max_input_tokens,
        max_output_tokens=f.max_output_tokens,
        allowed_environments=f.allowed_environments,
        denied_environments=f.denied_environments,
        require_json_output=f.require_json_output,
        rate_limit_per_minute=f.rate_limit_per_minute,
        rate_limit_per_hour=f.rate_limit_per_hour,
        max_cost_per_request_usd=f.max_cost_per_request_usd,
    )
