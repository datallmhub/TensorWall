"""Policy repository."""

from typing import Optional
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PolicyRule, PolicyAction, RuleType


class PolicyRepository:
    """Repository for Policy Rule CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        conditions: dict,
        action: PolicyAction = PolicyAction.ALLOW,
        application_id: Optional[int] = None,
        user_email: Optional[str] = None,
        description: Optional[str] = None,
        rule_type: RuleType = RuleType.GENERAL,
        priority: int = 0,
    ) -> PolicyRule:
        """Create a new policy rule."""
        rule = PolicyRule(
            name=name,
            description=description,
            application_id=application_id,
            user_email=user_email,
            rule_type=rule_type,
            conditions=conditions,
            action=action,
            priority=priority,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def get_by_id(self, id: int) -> Optional[PolicyRule]:
        """Get policy rule by ID (internal use only)."""
        result = await self.session.execute(
            select(PolicyRule).where(PolicyRule.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_uuid(self, uuid: UUID) -> Optional[PolicyRule]:
        """Get policy rule by UUID (public API use)."""
        result = await self.session.execute(
            select(PolicyRule).where(PolicyRule.uuid == uuid)
        )
        return result.scalar_one_or_none()

    async def list_for_application(
        self,
        application_id: int,
        enabled_only: bool = True,
    ) -> list[PolicyRule]:
        """
        List all policy rules applicable to an application.
        Includes global rules (application_id is NULL) and app-specific rules.
        """
        query = select(PolicyRule).where(
            or_(
                PolicyRule.application_id == application_id,
                PolicyRule.application_id.is_(None),  # Global rules
            )
        )
        if enabled_only:
            query = query.where(PolicyRule.is_enabled.is_(True))

        # Order by priority (higher first), then by specificity (app-specific first)
        query = query.order_by(
            PolicyRule.priority.desc(),
            PolicyRule.application_id.desc().nulls_last(),
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_global_rules(
        self,
        enabled_only: bool = True,
    ) -> list[PolicyRule]:
        """List all global policy rules."""
        query = select(PolicyRule).where(PolicyRule.application_id.is_(None))
        if enabled_only:
            query = query.where(PolicyRule.is_enabled.is_(True))
        query = query.order_by(PolicyRule.priority.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_application(
        self,
        application_id: int,
        enabled_only: bool = True,
    ) -> list[PolicyRule]:
        """List policy rules specific to an application (excludes global)."""
        query = select(PolicyRule).where(PolicyRule.application_id == application_id)
        if enabled_only:
            query = query.where(PolicyRule.is_enabled.is_(True))
        query = query.order_by(PolicyRule.priority.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        conditions: Optional[dict] = None,
        action: Optional[PolicyAction] = None,
        priority: Optional[int] = None,
        is_enabled: Optional[bool] = None,
    ) -> Optional[PolicyRule]:
        """Update a policy rule."""
        rule = await self.get_by_id(id)
        if not rule:
            return None

        if name is not None:
            rule.name = name
        if description is not None:
            rule.description = description
        if conditions is not None:
            rule.conditions = conditions
        if action is not None:
            rule.action = action
        if priority is not None:
            rule.priority = priority
        if is_enabled is not None:
            rule.is_enabled = is_enabled

        await self.session.flush()
        return rule

    async def delete(self, id: int) -> bool:
        """Delete a policy rule."""
        rule = await self.get_by_id(id)
        if not rule:
            return False

        await self.session.delete(rule)
        await self.session.flush()
        return True

    async def enable(self, id: int) -> bool:
        """Enable a policy rule."""
        rule = await self.get_by_id(id)
        if not rule:
            return False

        rule.is_enabled = True
        await self.session.flush()
        return True

    async def disable(self, id: int) -> bool:
        """Disable a policy rule."""
        rule = await self.get_by_id(id)
        if not rule:
            return False

        rule.is_enabled = False
        await self.session.flush()
        return True
