"""Audit repository."""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import AuditLog, AuditEventType


class AuditRepository:
    """Repository for Audit Log operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        event_type: AuditEventType,
        request_id: Optional[str] = None,
        app_id: Optional[str] = None,
        feature: Optional[str] = None,
        environment: Optional[str] = None,
        owner: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        policy_decision: Optional[str] = None,
        policy_reason: Optional[str] = None,
        budget_allowed: Optional[bool] = None,
        security_issues: Optional[list[str]] = None,
        blocked: bool = False,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """Log an audit event."""
        audit_log = AuditLog(
            event_type=event_type,
            request_id=request_id,
            app_id=app_id,
            feature=feature,
            environment=environment,
            owner=owner,
            model=model,
            provider=provider,
            policy_decision=policy_decision,
            policy_reason=policy_reason,
            budget_allowed=budget_allowed,
            security_issues=security_issues,
            blocked=blocked,
            error=error,
            metadata=metadata,
            timestamp=datetime.utcnow(),
        )
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log

    async def get_by_id(self, id: int) -> Optional[AuditLog]:
        """Get audit log by ID."""
        result = await self.session.execute(select(AuditLog).where(AuditLog.id == id))
        return result.scalar_one_or_none()

    async def get_by_request_id(self, request_id: str) -> list[AuditLog]:
        """Get all audit logs for a request."""
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.request_id == request_id)
            .order_by(AuditLog.timestamp.asc())
        )
        return list(result.scalars().all())

    async def list_by_app(
        self,
        app_id: str,
        event_type: Optional[AuditEventType] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs for an application."""
        query = select(AuditLog).where(AuditLog.app_id == app_id)

        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        if from_date:
            query = query.where(AuditLog.timestamp >= from_date)
        if to_date:
            query = query.where(AuditLog.timestamp <= to_date)

        query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_blocked(
        self,
        app_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """List blocked requests."""
        query = select(AuditLog).where(AuditLog.blocked.is_(True))

        if app_id:
            query = query.where(AuditLog.app_id == app_id)
        if from_date:
            query = query.where(AuditLog.timestamp >= from_date)

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_errors(
        self,
        app_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """List error events."""
        query = select(AuditLog).where(AuditLog.event_type == AuditEventType.ERROR)

        if app_id:
            query = query.where(AuditLog.app_id == app_id)
        if from_date:
            query = query.where(AuditLog.timestamp >= from_date)

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_app(
        self,
        app_id: str,
        event_type: Optional[AuditEventType] = None,
        from_date: Optional[datetime] = None,
    ) -> int:
        """Count audit logs for an application."""
        from sqlalchemy import func

        query = select(func.count(AuditLog.id)).where(AuditLog.app_id == app_id)

        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        if from_date:
            query = query.where(AuditLog.timestamp >= from_date)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_errors(
        self,
        from_date: Optional[datetime] = None,
    ) -> int:
        """Count all error events (for SLO calculations)."""
        from sqlalchemy import func

        query = select(func.count(AuditLog.id)).where(
            AuditLog.event_type == AuditEventType.ERROR
        )

        if from_date:
            query = query.where(AuditLog.timestamp >= from_date)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def cleanup_old_logs(self, retention_days: int) -> int:
        """Delete audit logs older than retention period. Returns count deleted."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        result = await self.session.execute(
            delete(AuditLog).where(AuditLog.timestamp < cutoff)
        )
        await self.session.flush()
        return result.rowcount
