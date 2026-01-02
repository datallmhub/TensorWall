from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict


class BudgetPeriod(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class BudgetLimit(BaseModel):
    """Configuration d'un budget."""

    app_id: str
    feature: Optional[str] = None  # None = all features
    environment: Optional[str] = None  # None = all environments

    # Limits
    soft_limit_usd: float  # Warning threshold
    hard_limit_usd: float  # Blocking threshold
    period: BudgetPeriod = BudgetPeriod.MONTHLY

    # Tracking
    current_spend_usd: float = 0.0
    period_start: datetime = datetime.now()


class BudgetCheckResult(BaseModel):
    allowed: bool
    warning: Optional[str] = None
    current_spend_usd: float
    remaining_usd: float
    limit_usd: float
    usage_percent: float


class BudgetEngine:
    """
    Moteur de gestion des budgets.
    Tracks usage and enforces limits.
    """

    def __init__(self):
        # In-memory storage (TODO: move to Redis/DB)
        self.budgets: dict[str, BudgetLimit] = {}
        self.usage: dict[str, float] = defaultdict(float)  # key -> spend

    def set_budget(self, budget: BudgetLimit) -> None:
        """Configure a budget limit."""
        key = self._budget_key(budget.app_id, budget.feature, budget.environment)
        self.budgets[key] = budget

    def check_budget(
        self,
        app_id: str,
        feature: Optional[str] = None,
        environment: Optional[str] = None,
        estimated_cost_usd: float = 0.0,
    ) -> BudgetCheckResult:
        """Check if request is within budget."""

        key = self._budget_key(app_id, feature, environment)
        budget = self.budgets.get(key)

        # Also check app-level budget if feature-specific not found
        if not budget and feature:
            key = self._budget_key(app_id, None, environment)
            budget = self.budgets.get(key)

        if not budget:
            # No budget configured = unlimited
            return BudgetCheckResult(
                allowed=True,
                current_spend_usd=0,
                remaining_usd=float("inf"),
                limit_usd=float("inf"),
                usage_percent=0,
            )

        # Reset if period expired
        self._check_period_reset(budget)

        current_spend = budget.current_spend_usd
        projected_spend = current_spend + estimated_cost_usd
        remaining = budget.hard_limit_usd - current_spend
        usage_percent = (current_spend / budget.hard_limit_usd) * 100

        # Hard limit check
        if projected_spend > budget.hard_limit_usd:
            return BudgetCheckResult(
                allowed=False,
                warning=f"Budget exceeded: ${current_spend:.2f} / ${budget.hard_limit_usd:.2f}",
                current_spend_usd=current_spend,
                remaining_usd=remaining,
                limit_usd=budget.hard_limit_usd,
                usage_percent=usage_percent,
            )

        # Soft limit warning
        warning = None
        if current_spend >= budget.soft_limit_usd:
            warning = f"Approaching budget limit: ${current_spend:.2f} / ${budget.hard_limit_usd:.2f} ({usage_percent:.1f}%)"

        return BudgetCheckResult(
            allowed=True,
            warning=warning,
            current_spend_usd=current_spend,
            remaining_usd=remaining,
            limit_usd=budget.hard_limit_usd,
            usage_percent=usage_percent,
        )

    def record_usage(
        self,
        app_id: str,
        feature: Optional[str],
        environment: Optional[str],
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Record token usage and return cost."""

        cost = self.estimate_cost(model, input_tokens, output_tokens)

        # Update budget
        key = self._budget_key(app_id, feature, environment)
        if key in self.budgets:
            self.budgets[key].current_spend_usd += cost

        # Also update app-level
        app_key = self._budget_key(app_id, None, environment)
        if app_key in self.budgets:
            self.budgets[app_key].current_spend_usd += cost

        return cost

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD (sync version using cached pricing)."""
        from backend.application.services.pricing_service import estimate_cost_sync

        return estimate_cost_sync(model, input_tokens, output_tokens)

    def _budget_key(
        self, app_id: str, feature: Optional[str], environment: Optional[str]
    ) -> str:
        return f"{app_id}:{feature or '*'}:{environment or '*'}"

    def _check_period_reset(self, budget: BudgetLimit) -> None:
        """Reset budget if period has elapsed."""
        now = datetime.now()
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


# Singleton
budget_engine = BudgetEngine()


# =============================================================================
# Budget Forecast & Pre-validation
# =============================================================================


class BudgetForecast(BaseModel):
    """Prévision budgétaire."""

    app_id: str
    environment: Optional[str] = None

    # Current state
    current_spend_usd: float
    hard_limit_usd: float
    remaining_usd: float

    # Request estimate
    estimated_request_cost_usd: float
    would_exceed_budget: bool

    # Projections
    daily_average_usd: float
    projected_end_of_period_usd: float
    projected_overage_usd: float
    days_until_exhaustion: Optional[int] = None

    # Recommendations
    can_proceed: bool
    recommendation: str
    risk_level: str  # low, medium, high, critical


class BudgetForecaster:
    """
    Budget forecasting and pre-validation.

    Features:
    - Estimate cost BEFORE making LLM call
    - Project end-of-period spend
    - Calculate days until budget exhaustion
    - Provide actionable recommendations
    """

    def __init__(self, engine: BudgetEngine):
        self.engine = engine
        # Historical usage for projections (app_id -> list of (date, cost))
        self._history: dict[str, list[tuple[datetime, float]]] = defaultdict(list)

    def estimate_request_cost(
        self,
        model: str,
        input_tokens: int,
        max_output_tokens: int,
    ) -> float:
        """
        Estimate cost for a request BEFORE execution.

        Uses max_output_tokens for worst-case estimation.
        """
        return self.engine.estimate_cost(model, input_tokens, max_output_tokens)

    def forecast(
        self,
        app_id: str,
        feature: Optional[str],
        environment: Optional[str],
        model: str,
        input_tokens: int,
        max_output_tokens: int,
    ) -> BudgetForecast:
        """
        Generate comprehensive budget forecast for a request.
        """
        # Get current budget state
        budget_result = self.engine.check_budget(
            app_id=app_id,
            feature=feature,
            environment=environment,
            estimated_cost_usd=0,
        )

        # Estimate request cost
        estimated_cost = self.estimate_request_cost(
            model, input_tokens, max_output_tokens
        )

        # Check if this request would exceed budget
        would_exceed = (
            budget_result.current_spend_usd + estimated_cost > budget_result.limit_usd
        )

        # Calculate daily average from history
        history = self._history.get(f"{app_id}:{environment or '*'}", [])
        if history:
            # Last 30 days
            cutoff = datetime.now() - timedelta(days=30)
            recent = [(d, c) for d, c in history if d > cutoff]
            if recent:
                total_cost = sum(c for _, c in recent)
                days = max(1, (datetime.now() - recent[0][0]).days)
                daily_average = total_cost / days
            else:
                daily_average = 0.0
        else:
            # Estimate from current spend
            daily_average = budget_result.current_spend_usd / 15  # Assume mid-month

        # Project end of period
        remaining_days = 30 - datetime.now().day  # Simplified: assume monthly
        projected_additional = daily_average * remaining_days
        projected_total = budget_result.current_spend_usd + projected_additional

        # Calculate overage
        projected_overage = max(0, projected_total - budget_result.limit_usd)

        # Days until exhaustion
        days_until_exhaustion = None
        if daily_average > 0:
            days_until_exhaustion = int(budget_result.remaining_usd / daily_average)

        # Determine risk level
        usage_percent = budget_result.usage_percent
        if usage_percent >= 95 or would_exceed:
            risk_level = "critical"
        elif usage_percent >= 80 or projected_overage > 0:
            risk_level = "high"
        elif usage_percent >= 60:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Generate recommendation
        if would_exceed:
            can_proceed = False
            recommendation = (
                f"Request blocked: estimated cost ${estimated_cost:.4f} "
                f"would exceed remaining budget ${budget_result.remaining_usd:.2f}"
            )
        elif risk_level == "critical":
            can_proceed = True
            recommendation = (
                f"Warning: budget nearly exhausted ({usage_percent:.1f}% used). "
                f"Only ${budget_result.remaining_usd:.2f} remaining."
            )
        elif risk_level == "high":
            can_proceed = True
            if projected_overage > 0:
                recommendation = (
                    f"Alert: projected to exceed budget by ${projected_overage:.2f} "
                    f"at current usage rate."
                )
            else:
                recommendation = (
                    f"Caution: {usage_percent:.1f}% of budget used. "
                    f"${budget_result.remaining_usd:.2f} remaining."
                )
        elif risk_level == "medium":
            can_proceed = True
            recommendation = f"On track: {usage_percent:.1f}% of budget used."
        else:
            can_proceed = True
            recommendation = f"Healthy: {usage_percent:.1f}% of budget used."

        return BudgetForecast(
            app_id=app_id,
            environment=environment,
            current_spend_usd=budget_result.current_spend_usd,
            hard_limit_usd=budget_result.limit_usd,
            remaining_usd=budget_result.remaining_usd,
            estimated_request_cost_usd=estimated_cost,
            would_exceed_budget=would_exceed,
            daily_average_usd=daily_average,
            projected_end_of_period_usd=projected_total,
            projected_overage_usd=projected_overage,
            days_until_exhaustion=days_until_exhaustion,
            can_proceed=can_proceed,
            recommendation=recommendation,
            risk_level=risk_level,
        )

    def record_for_forecast(
        self,
        app_id: str,
        environment: Optional[str],
        cost_usd: float,
    ) -> None:
        """Record usage for forecasting."""
        key = f"{app_id}:{environment or '*'}"
        self._history[key].append((datetime.now(), cost_usd))

        # Keep only last 90 days
        cutoff = datetime.now() - timedelta(days=90)
        self._history[key] = [(d, c) for d, c in self._history[key] if d > cutoff]

    def pre_validate_request(
        self,
        app_id: str,
        feature: Optional[str],
        environment: Optional[str],
        model: str,
        input_tokens: int,
        max_output_tokens: int,
        block_on_forecast_exceeded: bool = False,
    ) -> tuple[bool, BudgetForecast]:
        """
        Pre-validate a request against budget.

        Args:
            block_on_forecast_exceeded: If True, also block if forecast shows overage

        Returns:
            (can_proceed, forecast)
        """
        forecast = self.forecast(
            app_id=app_id,
            feature=feature,
            environment=environment,
            model=model,
            input_tokens=input_tokens,
            max_output_tokens=max_output_tokens,
        )

        can_proceed = forecast.can_proceed
        if block_on_forecast_exceeded and forecast.projected_overage_usd > 0:
            can_proceed = False

        return can_proceed, forecast


# Singleton
budget_forecaster = BudgetForecaster(budget_engine)


def pre_validate_budget(
    app_id: str,
    model: str,
    input_tokens: int,
    max_output_tokens: int,
    feature: Optional[str] = None,
    environment: Optional[str] = None,
) -> tuple[bool, BudgetForecast]:
    """
    Pre-validate request against budget before making LLM call.

    Returns:
        (allowed, forecast)
    """
    return budget_forecaster.pre_validate_request(
        app_id=app_id,
        feature=feature,
        environment=environment,
        model=model,
        input_tokens=input_tokens,
        max_output_tokens=max_output_tokens,
    )
