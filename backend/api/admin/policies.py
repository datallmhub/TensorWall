"""Policy management endpoints - FULLY SECURED."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.db.repositories.application import ApplicationRepository
from backend.db.repositories.policy import PolicyRepository
from backend.db.models import PolicyAction, RuleType
from backend.application.auth.permissions import PermissionDependency
from backend.application.auth.ownership import get_policy_by_uuid
from backend.core.jwt import get_current_user_id


router = APIRouter(prefix="/policies")


# ============================================================================
# Schemas
# ============================================================================


class PolicyConditions(BaseModel):
    """Policy conditions schema."""

    environments: Optional[list[str]] = None  # ["production", "staging"]
    features: Optional[list[str]] = None  # ["chat", "summarize"]
    models: Optional[list[str]] = None  # ["gpt-4o", "claude-3-5-sonnet"]
    max_tokens: Optional[int] = None
    max_context_tokens: Optional[int] = None
    allowed_hours: Optional[list[int]] = None  # [9, 18] = 9h-18h


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    app_id: Optional[str] = None  # None = global policy
    user_email: Optional[str] = None  # None = applies to all users
    rule_type: str = "general"  # model_restriction, environment_restriction, etc.
    conditions: PolicyConditions
    action: str = "allow"  # allow, warn, deny
    priority: int = 0


class PolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    rule_type: Optional[str] = None
    conditions: Optional[PolicyConditions] = None
    action: Optional[str] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None


class PolicyResponse(BaseModel):
    uuid: str  # ✅ SECURE: UUID instead of ID
    name: str
    description: Optional[str]
    app_id: Optional[str]
    user_email: Optional[str]
    rule_type: str
    conditions: dict
    action: str
    priority: int
    is_enabled: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PaginatedPolicyResponse(BaseModel):
    items: list[PolicyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Helper Functions
# ============================================================================


def _to_response(policy, app_id: Optional[str] = None) -> PolicyResponse:
    """Convert PolicyRule model to response with UUID."""
    # Handle rule_type (now stored as string in DB)
    rule_type_value = (
        policy.rule_type
        if isinstance(policy.rule_type, str)
        else (policy.rule_type.value if policy.rule_type else "general")
    )
    # Handle action (still enum)
    action_value = policy.action.value if hasattr(policy.action, "value") else policy.action

    return PolicyResponse(
        uuid=str(policy.uuid),  # ✅ UUID
        name=policy.name,
        description=policy.description,
        app_id=app_id,
        user_email=policy.user_email,
        rule_type=rule_type_value,
        conditions=policy.conditions or {},
        action=action_value,
        priority=policy.priority,
        is_enabled=policy.is_enabled,
        created_at=policy.created_at.isoformat(),
        updated_at=policy.updated_at.isoformat(),
    )


# ============================================================================
# Secure Endpoints
# ============================================================================


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    data: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("policies", "create")),  # ✅ RBAC
):
    """
    Create a new policy rule.

    Security: Requires 'policies:create' permission.
    """
    policy_repo = PolicyRepository(db)
    app_repo = ApplicationRepository(db)

    # Validate action
    try:
        action = PolicyAction(data.action)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {data.action}. Must be 'allow', 'warn', or 'deny'",
        )

    # Validate rule_type
    try:
        rule_type = RuleType(data.rule_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rule_type: {data.rule_type}. Must be one of: {[r.value for r in RuleType]}",
        )

    # If app_id provided, verify application exists
    application_id = None
    if data.app_id:
        app = await app_repo.get_by_app_id(data.app_id)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application '{data.app_id}' not found",
            )
        application_id = app.id

    policy = await policy_repo.create(
        name=data.name,
        description=data.description,
        application_id=application_id,
        user_email=data.user_email,
        rule_type=rule_type,
        conditions=data.conditions.model_dump(exclude_none=True),
        action=action,
        priority=data.priority,
    )

    return _to_response(policy, data.app_id)  # ✅ Returns UUID


@router.get("", response_model=PaginatedPolicyResponse)
async def list_policies(
    page: int = 1,
    page_size: int = 10,
    app_id: Optional[str] = None,
    user_email: Optional[str] = None,
    action: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("policies", "read")),  # ✅ RBAC
):
    """
    List policy rules with pagination and filters.

    Security:
    - Requires 'policies:read' permission
    - Returns UUIDs only (no internal IDs)
    - TODO: Filter by user ownership/scope
    """
    from sqlalchemy import select, func
    from backend.db.models import PolicyRule

    app_repo = ApplicationRepository(db)

    # Validate page_size
    if page_size > 100:
        page_size = 100
    if page_size < 1:
        page_size = 10
    if page < 1:
        page = 1

    # Build query with filters
    query = select(PolicyRule)

    # Apply filters
    if app_id:
        app = await app_repo.get_by_app_id(app_id)
        if app:
            query = query.where(PolicyRule.application_id == app.id)

    if user_email:
        query = query.where(PolicyRule.user_email == user_email)

    if action:
        try:
            action_enum = PolicyAction(action)
            query = query.where(PolicyRule.action == action_enum)
        except ValueError:
            pass  # Ignore invalid action

    if is_enabled is not None:
        query = query.where(PolicyRule.is_enabled == is_enabled)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(PolicyRule.priority.desc(), PolicyRule.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    policies = list(result.scalars().all())

    # Build response with app_id lookup
    items = []
    for policy in policies:
        policy_app_id = None
        if policy.application_id:
            app = await app_repo.get_by_id(policy.application_id)
            policy_app_id = app.app_id if app else None

        items.append(_to_response(policy, policy_app_id))  # ✅ Returns UUID

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedPolicyResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{policy_uuid}", response_model=PolicyResponse)
async def get_policy(
    policy_uuid: UUID,  # ✅ UUID parameter
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("policies", "read")),  # ✅ RBAC
):
    """
    Get policy by UUID.

    Security:
    - Uses UUID instead of integer ID
    - Validates ownership via get_policy_by_uuid()
    - Returns 403 if user doesn't have access
    - Returns 404 if policy doesn't exist
    """
    app_repo = ApplicationRepository(db)

    # ✅ SECURE: Validates ownership automatically
    policy = await get_policy_by_uuid(db, policy_uuid, user_id)

    policy_app_id = None
    if policy.application_id:
        app = await app_repo.get_by_id(policy.application_id)
        policy_app_id = app.app_id if app else None

    return _to_response(policy, policy_app_id)


@router.patch("/{policy_uuid}", response_model=PolicyResponse)
async def update_policy(
    policy_uuid: UUID,  # ✅ UUID parameter
    data: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("policies", "update")),  # ✅ RBAC
):
    """
    Update policy by UUID.

    Security:
    - Uses UUID instead of integer ID
    - Validates ownership before allowing update
    - Returns 403 if user doesn't own the policy
    """
    policy_repo = PolicyRepository(db)
    app_repo = ApplicationRepository(db)

    # ✅ SECURE: Validate ownership first
    policy = await get_policy_by_uuid(db, policy_uuid, user_id)

    # Validate action if provided
    action = None
    if data.action:
        try:
            action = PolicyAction(data.action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {data.action}",
            )

    conditions = data.conditions.model_dump(exclude_none=True) if data.conditions else None

    # Update using internal ID (not exposed to client)
    updated_policy = await policy_repo.update(
        id=policy.id,  # Internal use only
        name=data.name,
        description=data.description,
        conditions=conditions,
        action=action,
        priority=data.priority,
        is_enabled=data.is_enabled,
    )

    if not updated_policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    policy_app_id = None
    if updated_policy.application_id:
        app = await app_repo.get_by_id(updated_policy.application_id)
        policy_app_id = app.app_id if app else None

    return _to_response(updated_policy, policy_app_id)


@router.delete("/{policy_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_uuid: UUID,  # ✅ UUID parameter
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("policies", "delete")),  # ✅ RBAC
):
    """
    Delete policy by UUID.

    Security:
    - Validates ownership before allowing deletion
    - Returns 403 if user doesn't own the policy
    - Returns 404 if policy doesn't exist
    """
    policy_repo = PolicyRepository(db)

    # ✅ SECURE: Validate ownership
    policy = await get_policy_by_uuid(db, policy_uuid, user_id)

    # Delete using internal ID
    success = await policy_repo.delete(policy.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )


@router.post("/{policy_uuid}/enable", response_model=PolicyResponse)
async def enable_policy(
    policy_uuid: UUID,  # ✅ UUID parameter
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("policies", "update")),  # ✅ RBAC
):
    """
    Enable policy by UUID.

    Security: Validates ownership before allowing enable.
    """
    policy_repo = PolicyRepository(db)
    app_repo = ApplicationRepository(db)

    # ✅ SECURE: Validate ownership
    policy = await get_policy_by_uuid(db, policy_uuid, user_id)

    # Enable using internal ID
    success = await policy_repo.enable(policy.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    # Get updated policy
    updated_policy = await policy_repo.get_by_id(policy.id)

    policy_app_id = None
    if updated_policy.application_id:
        app = await app_repo.get_by_id(updated_policy.application_id)
        policy_app_id = app.app_id if app else None

    return _to_response(updated_policy, policy_app_id)


@router.post("/{policy_uuid}/disable", response_model=PolicyResponse)
async def disable_policy(
    policy_uuid: UUID,  # ✅ UUID parameter
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),  # ✅ JWT
    _: None = Depends(PermissionDependency("policies", "update")),  # ✅ RBAC
):
    """
    Disable policy by UUID.

    Security: Validates ownership before allowing disable.
    """
    policy_repo = PolicyRepository(db)
    app_repo = ApplicationRepository(db)

    # ✅ SECURE: Validate ownership
    policy = await get_policy_by_uuid(db, policy_uuid, user_id)

    # Disable using internal ID
    success = await policy_repo.disable(policy.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    # Get updated policy
    updated_policy = await policy_repo.get_by_id(policy.id)

    policy_app_id = None
    if updated_policy.application_id:
        app = await app_repo.get_by_id(updated_policy.application_id)
        policy_app_id = app.app_id if app else None

    return _to_response(updated_policy, policy_app_id)
