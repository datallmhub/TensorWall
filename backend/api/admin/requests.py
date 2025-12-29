"""
Request Logs API -

Provides visibility into recent gateway requests for debugging and observability.
This is essential for understanding gateway behavior and troubleshooting.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.db.models import LLMRequestTrace
from backend.core.jwt import get_current_user_id

router = APIRouter(prefix="/requests")


# ============================================================================
# Response Models
# ============================================================================


class RequestLogItem(BaseModel):
    """Single request log entry."""

    id: int
    request_id: str | None
    timestamp: datetime
    app_id: str | None
    feature: str | None
    environment: str | None
    model: str | None
    provider: str | None
    decision: str | None
    status: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    latency_ms: int | None
    error: str | None

    class Config:
        from_attributes = True


class RequestLogList(BaseModel):
    """Paginated list of request logs."""

    items: list[RequestLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class RequestDetail(BaseModel):
    """Detailed view of a single request."""

    id: int
    request_id: str | None
    timestamp: datetime
    app_id: str | None
    feature: str | None
    environment: str | None
    model: str | None
    provider: str | None
    decision: str | None
    decision_reasons: list[str] | None
    status: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    latency_ms: int | None
    error: str | None

    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=RequestLogList)
async def list_request_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=10, le=100, description="Items per page"),
    app_id: Optional[str] = Query(None, description="Filter by application"),
    model: Optional[str] = Query(None, description="Filter by model"),
    decision_filter: Optional[str] = Query(
        None, alias="decision", description="Filter by decision (allow/warn/block)"
    ),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status (success/pending/error)"
    ),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List recent request logs."""
    query = select(LLMRequestTrace)

    # Apply filters
    if app_id:
        query = query.where(LLMRequestTrace.app_id == app_id)
    if model:
        query = query.where(LLMRequestTrace.model == model)
    if decision_filter:
        query = query.where(LLMRequestTrace.decision == decision_filter)
    if status_filter:
        query = query.where(LLMRequestTrace.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(LLMRequestTrace.timestamp_start)).offset(offset).limit(page_size)

    result = await db.execute(query)
    traces = result.scalars().all()

    items = [
        RequestLogItem(
            id=t.id,
            request_id=t.request_id,
            timestamp=t.timestamp_start,
            app_id=t.app_id,
            feature=t.feature,
            environment=t.environment,
            model=t.model,
            provider=t.provider,
            decision=t.decision.value if t.decision else None,
            status=t.status.value if t.status else None,
            input_tokens=t.input_tokens,
            output_tokens=t.output_tokens,
            cost_usd=float(t.cost_usd) if t.cost_usd else None,
            latency_ms=t.latency_ms,
            error=t.error_message,
        )
        for t in traces
    ]

    total_pages = (total + page_size - 1) // page_size

    return RequestLogList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stats/summary")
async def get_request_stats(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get summary statistics for requests."""
    from backend.db.models import TraceDecision

    total_result = await db.execute(select(func.count(LLMRequestTrace.id)))
    total_requests = total_result.scalar_one()

    allowed_result = await db.execute(
        select(func.count(LLMRequestTrace.id)).where(
            LLMRequestTrace.decision == TraceDecision.ALLOW
        )
    )
    allowed_requests = allowed_result.scalar_one()

    warned_result = await db.execute(
        select(func.count(LLMRequestTrace.id)).where(LLMRequestTrace.decision == TraceDecision.WARN)
    )
    warned_requests = warned_result.scalar_one()

    blocked_result = await db.execute(
        select(func.count(LLMRequestTrace.id)).where(
            LLMRequestTrace.decision == TraceDecision.BLOCK
        )
    )
    blocked_requests = blocked_result.scalar_one()

    apps_result = await db.execute(select(func.count(func.distinct(LLMRequestTrace.app_id))))
    unique_apps = apps_result.scalar_one()

    models_result = await db.execute(select(func.count(func.distinct(LLMRequestTrace.model))))
    unique_models = models_result.scalar_one()

    block_rate = round(blocked_requests / total_requests * 100, 1) if total_requests > 0 else 0

    return {
        "total_requests": total_requests,
        "allowed_requests": allowed_requests,
        "warned_requests": warned_requests,
        "blocked_requests": blocked_requests,
        "block_rate": block_rate,
        "unique_apps": unique_apps,
        "unique_models": unique_models,
    }


@router.get("/filters/values")
async def get_filter_values(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get unique values for filter dropdowns."""
    from backend.db.models import Application, LLMModel

    # Get apps from applications table
    apps_result = await db.execute(
        select(Application.app_id).where(Application.is_active.is_(True)).order_by(Application.app_id)
    )
    apps = [row[0] for row in apps_result.fetchall()]

    # Get models from llm_models table
    models_result = await db.execute(
        select(LLMModel.model_id).where(LLMModel.is_enabled.is_(True)).order_by(LLMModel.model_id)
    )
    models = [row[0] for row in models_result.fetchall()]

    # Decisions are fixed enum values (policy engine decision)
    decisions = ["allow", "warn", "block"]

    # Statuses are fixed enum values (technical request status - without 'blocked' which is redundant with decision)
    statuses = ["success", "pending", "error"]

    return {
        "apps": apps,
        "models": models,
        "decisions": decisions,
        "statuses": statuses,
    }


@router.get("/{request_id}", response_model=RequestDetail)
async def get_request_detail(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get detailed view of a specific request."""
    result = await db.execute(
        select(LLMRequestTrace).where(LLMRequestTrace.request_id == request_id)
    )
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Request {request_id} not found"
        )

    return RequestDetail(
        id=trace.id,
        request_id=trace.request_id,
        timestamp=trace.timestamp_start,
        app_id=trace.app_id,
        feature=trace.feature,
        environment=trace.environment,
        model=trace.model,
        provider=trace.provider,
        decision=trace.decision.value if trace.decision else None,
        decision_reasons=trace.decision_reasons,
        status=trace.status.value if trace.status else None,
        input_tokens=trace.input_tokens,
        output_tokens=trace.output_tokens,
        cost_usd=float(trace.cost_usd) if trace.cost_usd else None,
        latency_ms=trace.latency_ms,
        error=trace.error_message,
    )
