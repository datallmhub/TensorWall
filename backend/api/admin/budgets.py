"""
Budget API - Simple hard limit budget per application.

OSS Budget = Safety guardrail to prevent runaway costs.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.db.models import Budget, BudgetScope, BudgetPeriod, Application
from backend.core.jwt import get_current_user_id

router = APIRouter(prefix="/budgets")


# ============================================================================
# Response Models (OSS - Simplified)
# ============================================================================


class BudgetResponse(BaseModel):
    """Budget response - Simplified version."""

    uuid: str
    app_id: str
    app_name: str | None = None
    limit_usd: float
    spent_usd: float
    remaining_usd: float
    usage_percent: float
    period: str
    is_exceeded: bool

    class Config:
        from_attributes = True


class BudgetListResponse(BaseModel):
    """List of budgets."""

    items: list[BudgetResponse]
    total: int


class CreateBudgetRequest(BaseModel):
    """Create budget request - Only application scope is supported."""

    app_id: str = Field(..., description="Application ID")
    limit_usd: float = Field(..., ge=0, description="Monthly limit in USD")
    period: str = Field(default="monthly", description="Budget period (monthly)")


class UpdateBudgetRequest(BaseModel):
    """Update budget request."""

    limit_usd: float | None = Field(None, ge=0, description="New limit in USD")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=BudgetListResponse)
async def list_budgets(
    app_id: Optional[str] = Query(None, description="Filter by application"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List all application budgets.

    Only application-scoped budgets are shown.
    """
    query = (
        select(Budget)
        .options(selectinload(Budget.application))
        .where(Budget.scope == BudgetScope.APPLICATION)
        .order_by(Budget.created_at.desc())
    )

    if app_id:
        # Find application by app_id
        app_result = await db.execute(
            select(Application).where(Application.app_id == app_id)
        )
        app = app_result.scalar_one_or_none()
        if app:
            query = query.where(Budget.application_id == app.id)

    result = await db.execute(query)
    budgets = result.scalars().all()

    items = []
    for b in budgets:
        # Get app_id from relationship
        app_id_str = ""
        app_name = None
        if b.application:
            app_id_str = b.application.app_id
            app_name = b.application.name

        # Uses hard_limit_usd as the single limit
        limit = float(b.hard_limit_usd)
        spent = float(b.current_spend_usd)
        remaining = max(0, limit - spent)
        usage_pct = (spent / limit * 100) if limit > 0 else 0

        items.append(
            BudgetResponse(
                uuid=str(b.uuid),
                app_id=app_id_str,
                app_name=app_name,
                limit_usd=limit,
                spent_usd=spent,
                remaining_usd=remaining,
                usage_percent=round(usage_pct, 1),
                period=b.period.value if b.period else "monthly",
                is_exceeded=spent >= limit,
            )
        )

    return BudgetListResponse(items=items, total=len(items))


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    request: CreateBudgetRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new application budget.

    Only one budget per application is allowed.
    Action is always 'block' when exceeded.
    """
    # Find application
    app_result = await db.execute(
        select(Application).where(Application.app_id == request.app_id)
    )
    app = app_result.scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{request.app_id}' not found",
        )

    # Check if budget already exists for this app
    existing = await db.execute(
        select(Budget)
        .where(Budget.application_id == app.id)
        .where(Budget.scope == BudgetScope.APPLICATION)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Budget already exists for application '{request.app_id}'. Use PATCH to update.",
        )

    # Validate period (only monthly recommended)
    try:
        period = BudgetPeriod(request.period)
    except ValueError:
        period = BudgetPeriod.MONTHLY

    # Create budget - uses hard_limit only (no soft limit)
    budget = Budget(
        scope=BudgetScope.APPLICATION,
        application_id=app.id,
        hard_limit_usd=request.limit_usd,
        soft_limit_usd=request.limit_usd,  # Set same as hard
        current_spend_usd=0.0,
        period=period,
    )

    db.add(budget)
    await db.commit()
    await db.refresh(budget)

    return BudgetResponse(
        uuid=str(budget.uuid),
        app_id=app.app_id,
        app_name=app.name,
        limit_usd=float(budget.hard_limit_usd),
        spent_usd=0.0,
        remaining_usd=float(budget.hard_limit_usd),
        usage_percent=0.0,
        period=budget.period.value,
        is_exceeded=False,
    )


@router.get("/{budget_uuid}", response_model=BudgetResponse)
async def get_budget(
    budget_uuid: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get a specific budget by UUID."""
    result = await db.execute(
        select(Budget)
        .options(selectinload(Budget.application))
        .where(Budget.uuid == budget_uuid)
    )
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget '{budget_uuid}' not found",
        )

    app_id_str = ""
    app_name = None
    if budget.application:
        app_id_str = budget.application.app_id
        app_name = budget.application.name

    limit = float(budget.hard_limit_usd)
    spent = float(budget.current_spend_usd)
    remaining = max(0, limit - spent)
    usage_pct = (spent / limit * 100) if limit > 0 else 0

    return BudgetResponse(
        uuid=str(budget.uuid),
        app_id=app_id_str,
        app_name=app_name,
        limit_usd=limit,
        spent_usd=spent,
        remaining_usd=remaining,
        usage_percent=round(usage_pct, 1),
        period=budget.period.value if budget.period else "monthly",
        is_exceeded=spent >= limit,
    )


@router.patch("/{budget_uuid}", response_model=BudgetResponse)
async def update_budget(
    budget_uuid: str,
    request: UpdateBudgetRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update a budget's limit.

    Can only update the limit, not the scope or other advanced options.
    """
    result = await db.execute(
        select(Budget)
        .options(selectinload(Budget.application))
        .where(Budget.uuid == budget_uuid)
    )
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget '{budget_uuid}' not found",
        )

    if request.limit_usd is not None:
        budget.hard_limit_usd = request.limit_usd
        budget.soft_limit_usd = request.limit_usd  # keep in sync

    await db.commit()
    await db.refresh(budget)

    app_id_str = ""
    app_name = None
    if budget.application:
        app_id_str = budget.application.app_id
        app_name = budget.application.name

    limit = float(budget.hard_limit_usd)
    spent = float(budget.current_spend_usd)
    remaining = max(0, limit - spent)
    usage_pct = (spent / limit * 100) if limit > 0 else 0

    return BudgetResponse(
        uuid=str(budget.uuid),
        app_id=app_id_str,
        app_name=app_name,
        limit_usd=limit,
        spent_usd=spent,
        remaining_usd=remaining,
        usage_percent=round(usage_pct, 1),
        period=budget.period.value if budget.period else "monthly",
        is_exceeded=spent >= limit,
    )


@router.delete("/{budget_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_uuid: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a budget."""
    result = await db.execute(select(Budget).where(Budget.uuid == budget_uuid))
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget '{budget_uuid}' not found",
        )

    await db.delete(budget)
    await db.commit()


@router.post("/{budget_uuid}/reset", response_model=BudgetResponse)
async def reset_budget(
    budget_uuid: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Reset a budget's spent amount to 0.

    Useful for manual reset at start of billing period.
    """
    result = await db.execute(
        select(Budget)
        .options(selectinload(Budget.application))
        .where(Budget.uuid == budget_uuid)
    )
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget '{budget_uuid}' not found",
        )

    budget.current_spend_usd = 0.0
    await db.commit()
    await db.refresh(budget)

    app_id_str = ""
    app_name = None
    if budget.application:
        app_id_str = budget.application.app_id
        app_name = budget.application.name

    return BudgetResponse(
        uuid=str(budget.uuid),
        app_id=app_id_str,
        app_name=app_name,
        limit_usd=float(budget.hard_limit_usd),
        spent_usd=0.0,
        remaining_usd=float(budget.hard_limit_usd),
        usage_percent=0.0,
        period=budget.period.value if budget.period else "monthly",
        is_exceeded=False,
    )
