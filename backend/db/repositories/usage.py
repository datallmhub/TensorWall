"""Usage repository."""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UsageRecord, Environment


class UsageRepository:
    """Repository for Usage Record operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        request_id: str,
        app_id: str,
        environment: Environment,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: int,
        feature: Optional[str] = None,
    ) -> UsageRecord:
        """Record a usage event."""
        usage = UsageRecord(
            request_id=request_id,
            app_id=app_id,
            feature=feature,
            environment=environment,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
        self.session.add(usage)
        await self.session.flush()
        return usage

    async def get_by_request_id(self, request_id: str) -> Optional[UsageRecord]:
        """Get usage record by request ID."""
        result = await self.session.execute(
            select(UsageRecord).where(UsageRecord.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def list_by_app(
        self,
        app_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UsageRecord]:
        """List usage records for an application."""
        query = select(UsageRecord).where(UsageRecord.app_id == app_id)

        if from_date:
            query = query.where(UsageRecord.created_at >= from_date)
        if to_date:
            query = query.where(UsageRecord.created_at <= to_date)

        query = query.order_by(UsageRecord.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_all(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100000,
    ) -> list[UsageRecord]:
        """List all usage records across all apps (for SLO calculations)."""
        query = select(UsageRecord)

        if from_date:
            query = query.where(UsageRecord.created_at >= from_date)
        if to_date:
            query = query.where(UsageRecord.created_at <= to_date)

        query = query.order_by(UsageRecord.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_cost(
        self,
        app_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> float:
        """Get total cost for an application."""
        query = select(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0)).where(
            UsageRecord.app_id == app_id
        )

        if from_date:
            query = query.where(UsageRecord.created_at >= from_date)
        if to_date:
            query = query.where(UsageRecord.created_at <= to_date)
        if feature:
            query = query.where(UsageRecord.feature == feature)
        if environment:
            query = query.where(UsageRecord.environment == environment)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_total_tokens(
        self,
        app_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        """Get total tokens for an application."""
        query = select(
            func.coalesce(func.sum(UsageRecord.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0).label("output_tokens"),
        ).where(UsageRecord.app_id == app_id)

        if from_date:
            query = query.where(UsageRecord.created_at >= from_date)
        if to_date:
            query = query.where(UsageRecord.created_at <= to_date)

        result = await self.session.execute(query)
        row = result.one()
        return {
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "total_tokens": row.input_tokens + row.output_tokens,
        }

    async def get_stats_by_model(
        self,
        app_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[dict]:
        """Get usage statistics grouped by model."""
        query = select(
            UsageRecord.model,
            func.count(UsageRecord.id).label("request_count"),
            func.sum(UsageRecord.input_tokens).label("input_tokens"),
            func.sum(UsageRecord.output_tokens).label("output_tokens"),
            func.sum(UsageRecord.cost_usd).label("total_cost"),
            func.avg(UsageRecord.latency_ms).label("avg_latency_ms"),
        ).where(UsageRecord.app_id == app_id)

        if from_date:
            query = query.where(UsageRecord.created_at >= from_date)
        if to_date:
            query = query.where(UsageRecord.created_at <= to_date)

        query = query.group_by(UsageRecord.model)

        result = await self.session.execute(query)
        return [
            {
                "model": row.model,
                "request_count": row.request_count,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "total_cost": float(row.total_cost) if row.total_cost else 0.0,
                "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms else 0.0,
            }
            for row in result.all()
        ]

    async def get_stats_by_feature(
        self,
        app_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[dict]:
        """Get usage statistics grouped by feature."""
        query = select(
            UsageRecord.feature,
            func.count(UsageRecord.id).label("request_count"),
            func.sum(UsageRecord.cost_usd).label("total_cost"),
            func.avg(UsageRecord.latency_ms).label("avg_latency_ms"),
        ).where(UsageRecord.app_id == app_id)

        if from_date:
            query = query.where(UsageRecord.created_at >= from_date)
        if to_date:
            query = query.where(UsageRecord.created_at <= to_date)

        query = query.group_by(UsageRecord.feature)

        result = await self.session.execute(query)
        return [
            {
                "feature": row.feature or "unknown",
                "request_count": row.request_count,
                "total_cost": float(row.total_cost) if row.total_cost else 0.0,
                "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms else 0.0,
            }
            for row in result.all()
        ]

    async def get_daily_stats(
        self,
        app_id: str,
        days: int = 30,
    ) -> list[dict]:
        """Get daily usage statistics."""
        from_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                func.date(UsageRecord.created_at).label("date"),
                func.count(UsageRecord.id).label("request_count"),
                func.sum(UsageRecord.cost_usd).label("total_cost"),
                func.sum(UsageRecord.input_tokens).label("input_tokens"),
                func.sum(UsageRecord.output_tokens).label("output_tokens"),
            )
            .where(
                UsageRecord.app_id == app_id,
                UsageRecord.created_at >= from_date,
            )
            .group_by(func.date(UsageRecord.created_at))
            .order_by(func.date(UsageRecord.created_at))
        )

        result = await self.session.execute(query)
        return [
            {
                "date": str(row.date),
                "request_count": row.request_count,
                "total_cost": float(row.total_cost) if row.total_cost else 0.0,
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
            }
            for row in result.all()
        ]
