"""Budget repository."""

from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Budget, BudgetPeriod, BudgetScope, Environment


class BudgetRepository:
    """Repository for Budget CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Create Methods
    # =========================================================================

    async def create(
        self,
        soft_limit_usd: float,
        hard_limit_usd: float,
        scope: BudgetScope = BudgetScope.APPLICATION,
        application_id: Optional[int] = None,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        org_id: Optional[str] = None,
        period: BudgetPeriod = BudgetPeriod.MONTHLY,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> Budget:
        """Create a new budget with specified scope."""
        budget = Budget(
            scope=scope,
            application_id=application_id,
            user_id=user_id,
            user_email=user_email,
            org_id=org_id,
            feature=feature,
            environment=environment,
            soft_limit_usd=soft_limit_usd,
            hard_limit_usd=hard_limit_usd,
            period=period,
            current_spend_usd=0.0,
            period_start=datetime.utcnow(),
        )
        self.session.add(budget)
        await self.session.flush()
        return budget

    async def create_app_budget(
        self,
        application_id: int,
        soft_limit_usd: float,
        hard_limit_usd: float,
        period: BudgetPeriod = BudgetPeriod.MONTHLY,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> Budget:
        """Create a budget scoped to an application."""
        return await self.create(
            scope=BudgetScope.APPLICATION,
            application_id=application_id,
            soft_limit_usd=soft_limit_usd,
            hard_limit_usd=hard_limit_usd,
            period=period,
            feature=feature,
            environment=environment,
        )

    async def create_user_budget(
        self,
        user_email: str,
        soft_limit_usd: float,
        hard_limit_usd: float,
        period: BudgetPeriod = BudgetPeriod.MONTHLY,
        user_id: Optional[int] = None,
        application_id: Optional[int] = None,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> Budget:
        """Create a budget scoped to a user."""
        return await self.create(
            scope=BudgetScope.USER,
            user_id=user_id,
            user_email=user_email,
            application_id=application_id,
            soft_limit_usd=soft_limit_usd,
            hard_limit_usd=hard_limit_usd,
            period=period,
            feature=feature,
            environment=environment,
        )

    async def create_org_budget(
        self,
        org_id: str,
        soft_limit_usd: float,
        hard_limit_usd: float,
        period: BudgetPeriod = BudgetPeriod.MONTHLY,
        application_id: Optional[int] = None,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> Budget:
        """Create a budget scoped to an organization."""
        return await self.create(
            scope=BudgetScope.ORGANIZATION,
            org_id=org_id,
            application_id=application_id,
            soft_limit_usd=soft_limit_usd,
            hard_limit_usd=hard_limit_usd,
            period=period,
            feature=feature,
            environment=environment,
        )

    # =========================================================================
    # Read Methods
    # =========================================================================

    async def get_by_id(self, id: int) -> Optional[Budget]:
        """Get budget by ID (internal use only)."""
        result = await self.session.execute(select(Budget).where(Budget.id == id))
        return result.scalar_one_or_none()

    async def get_by_uuid(self, uuid: UUID) -> Optional[Budget]:
        """Get budget by UUID (public API use)."""
        result = await self.session.execute(select(Budget).where(Budget.uuid == uuid))
        return result.scalar_one_or_none()

    async def get_for_request(
        self,
        application_id: int,
        user_email: Optional[str] = None,
        org_id: Optional[str] = None,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> list[Budget]:
        """
        Get all applicable budgets for a request.
        Returns budgets in priority order: user > org > app (most specific first).
        All matching budgets must be checked for enforcement.
        """
        budgets = []

        # 1. Check user-specific budgets (highest priority)
        if user_email:
            user_budgets = await self._get_user_budgets_for_request(
                user_email, application_id, feature, environment
            )
            budgets.extend(user_budgets)

        # 2. Check org-specific budgets
        if org_id:
            org_budgets = await self._get_org_budgets_for_request(
                org_id, application_id, feature, environment
            )
            budgets.extend(org_budgets)

        # 3. Check app-level budgets
        app_budgets = await self._get_app_budgets_for_request(
            application_id, feature, environment
        )
        budgets.extend(app_budgets)

        return budgets

    async def _get_user_budgets_for_request(
        self,
        user_email: str,
        application_id: Optional[int] = None,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> list[Budget]:
        """Get user budgets matching the request context."""
        budgets = []

        # User + App + Feature + Env specific
        if application_id and feature and environment:
            result = await self.session.execute(
                select(Budget).where(
                    Budget.scope == BudgetScope.USER,
                    Budget.user_email == user_email,
                    Budget.application_id == application_id,
                    Budget.feature == feature,
                    Budget.environment == environment,
                    Budget.is_active.is_(True),
                )
            )
            budget = result.scalar_one_or_none()
            if budget:
                budgets.append(budget)

        # User + App specific (no feature/env filter)
        if application_id:
            result = await self.session.execute(
                select(Budget).where(
                    Budget.scope == BudgetScope.USER,
                    Budget.user_email == user_email,
                    Budget.application_id == application_id,
                    Budget.feature.is_(None),
                    Budget.environment.is_(None),
                    Budget.is_active.is_(True),
                )
            )
            budget = result.scalar_one_or_none()
            if budget:
                budgets.append(budget)

        # User global budget (no app filter)
        result = await self.session.execute(
            select(Budget).where(
                Budget.scope == BudgetScope.USER,
                Budget.user_email == user_email,
                Budget.application_id.is_(None),
                Budget.is_active.is_(True),
            )
        )
        budget = result.scalar_one_or_none()
        if budget:
            budgets.append(budget)

        return budgets

    async def _get_org_budgets_for_request(
        self,
        org_id: str,
        application_id: Optional[int] = None,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> list[Budget]:
        """Get org budgets matching the request context."""
        budgets = []

        # Org + App specific
        if application_id:
            result = await self.session.execute(
                select(Budget).where(
                    Budget.scope == BudgetScope.ORGANIZATION,
                    Budget.org_id == org_id,
                    Budget.application_id == application_id,
                    Budget.is_active.is_(True),
                )
            )
            budget = result.scalar_one_or_none()
            if budget:
                budgets.append(budget)

        # Org global budget
        result = await self.session.execute(
            select(Budget).where(
                Budget.scope == BudgetScope.ORGANIZATION,
                Budget.org_id == org_id,
                Budget.application_id.is_(None),
                Budget.is_active.is_(True),
            )
        )
        budget = result.scalar_one_or_none()
        if budget:
            budgets.append(budget)

        return budgets

    async def _get_app_budgets_for_request(
        self,
        application_id: int,
        feature: Optional[str] = None,
        environment: Optional[Environment] = None,
    ) -> list[Budget]:
        """Get app budgets matching the request context (original logic)."""
        budgets = []

        # Try feature + environment specific
        if feature and environment:
            result = await self.session.execute(
                select(Budget).where(
                    Budget.scope == BudgetScope.APPLICATION,
                    Budget.application_id == application_id,
                    Budget.feature == feature,
                    Budget.environment == environment,
                    Budget.is_active.is_(True),
                )
            )
            budget = result.scalar_one_or_none()
            if budget:
                budgets.append(budget)

        # Try feature specific
        if feature:
            result = await self.session.execute(
                select(Budget).where(
                    Budget.scope == BudgetScope.APPLICATION,
                    Budget.application_id == application_id,
                    Budget.feature == feature,
                    Budget.environment.is_(None),
                    Budget.is_active.is_(True),
                )
            )
            budget = result.scalar_one_or_none()
            if budget:
                budgets.append(budget)

        # Try environment specific
        if environment:
            result = await self.session.execute(
                select(Budget).where(
                    Budget.scope == BudgetScope.APPLICATION,
                    Budget.application_id == application_id,
                    Budget.feature.is_(None),
                    Budget.environment == environment,
                    Budget.is_active.is_(True),
                )
            )
            budget = result.scalar_one_or_none()
            if budget:
                budgets.append(budget)

        # Fall back to app-level budget
        result = await self.session.execute(
            select(Budget).where(
                Budget.scope == BudgetScope.APPLICATION,
                Budget.application_id == application_id,
                Budget.feature.is_(None),
                Budget.environment.is_(None),
                Budget.is_active.is_(True),
            )
        )
        budget = result.scalar_one_or_none()
        if budget:
            budgets.append(budget)

        return budgets

    # =========================================================================
    # List Methods
    # =========================================================================

    async def list_by_application(
        self,
        application_id: int,
        active_only: bool = True,
    ) -> list[Budget]:
        """List all budgets for an application (any scope)."""
        query = select(Budget).where(Budget.application_id == application_id)
        if active_only:
            query = query.where(Budget.is_active.is_(True))
        query = query.order_by(Budget.scope, Budget.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_email: str,
        active_only: bool = True,
    ) -> list[Budget]:
        """List all budgets for a user."""
        query = select(Budget).where(
            Budget.scope == BudgetScope.USER,
            Budget.user_email == user_email,
        )
        if active_only:
            query = query.where(Budget.is_active.is_(True))
        query = query.order_by(Budget.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_org(
        self,
        org_id: str,
        active_only: bool = True,
    ) -> list[Budget]:
        """List all budgets for an organization."""
        query = select(Budget).where(
            Budget.scope == BudgetScope.ORGANIZATION,
            Budget.org_id == org_id,
        )
        if active_only:
            query = query.where(Budget.is_active.is_(True))
        query = query.order_by(Budget.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_all(
        self,
        scope: Optional[BudgetScope] = None,
        active_only: bool = True,
        limit: int = 1000,
    ) -> list[Budget]:
        """List all budgets with optional scope filter."""
        query = select(Budget)
        if scope:
            query = query.where(Budget.scope == scope)
        if active_only:
            query = query.where(Budget.is_active.is_(True))
        query = query.order_by(Budget.scope, Budget.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # Update Methods
    # =========================================================================

    async def update(
        self,
        id: int,
        soft_limit_usd: Optional[float] = None,
        hard_limit_usd: Optional[float] = None,
        period: Optional[BudgetPeriod] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Budget]:
        """Update a budget."""
        budget = await self.get_by_id(id)
        if not budget:
            return None

        if soft_limit_usd is not None:
            budget.soft_limit_usd = soft_limit_usd
        if hard_limit_usd is not None:
            budget.hard_limit_usd = hard_limit_usd
        if period is not None:
            budget.period = period
        if is_active is not None:
            budget.is_active = is_active

        await self.session.flush()
        return budget

    async def record_usage(
        self,
        id: int,
        cost_usd: float,
    ) -> Optional[Budget]:
        """Record usage against a budget."""
        budget = await self.get_by_id(id)
        if not budget:
            return None

        # Check if period needs reset
        await self._check_period_reset(budget)

        budget.current_spend_usd += cost_usd
        await self.session.flush()
        return budget

    async def record_usage_for_request(
        self,
        budgets: list[Budget],
        cost_usd: float,
    ) -> None:
        """Record usage against all applicable budgets for a request."""
        for budget in budgets:
            await self._check_period_reset(budget)
            budget.current_spend_usd += cost_usd
        await self.session.flush()

    async def reset_budget(self, id: int) -> Optional[Budget]:
        """Manually reset a budget's current spend."""
        budget = await self.get_by_id(id)
        if not budget:
            return None

        budget.current_spend_usd = 0.0
        budget.period_start = datetime.utcnow()
        await self.session.flush()
        return budget

    async def _check_period_reset(self, budget: Budget) -> None:
        """Check and reset budget if period has elapsed."""
        now = datetime.utcnow()
        elapsed = now - budget.period_start

        should_reset = False
        if budget.period == BudgetPeriod.HOURLY and elapsed > timedelta(hours=1):
            should_reset = True
        elif budget.period == BudgetPeriod.DAILY and elapsed > timedelta(days=1):
            should_reset = True
        elif budget.period == BudgetPeriod.WEEKLY and elapsed > timedelta(weeks=1):
            should_reset = True
        elif budget.period == BudgetPeriod.MONTHLY and elapsed > timedelta(days=30):
            should_reset = True

        if should_reset:
            budget.current_spend_usd = 0.0
            budget.period_start = now

    # =========================================================================
    # Delete Methods
    # =========================================================================

    async def delete(self, id: int) -> bool:
        """Delete a budget."""
        budget = await self.get_by_id(id)
        if not budget:
            return False

        await self.session.delete(budget)
        await self.session.flush()
        return True
