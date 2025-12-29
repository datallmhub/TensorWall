"""
Base classes and mixins for gateway components.

Provides reusable patterns to reduce code duplication across the codebase.
"""

from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic
import logging

__all__ = [
    # Base classes
    "AsyncLoadableEntity",
    # Condition matching
    "ConditionMatcher",
    "ConditionMatchResult",
    "ConditionContext",
    "match_conditions",
]

logger = logging.getLogger(__name__)


# =============================================================================
# AsyncLoadableEntity - Base class for DB-backed lazy loading
# =============================================================================

T = TypeVar("T")


class AsyncLoadableEntity(ABC, Generic[T]):
    """
    Base class for entities that load data from database asynchronously.

    Provides:
    - Lazy loading with ensure_loaded()
    - Cache invalidation
    - Error handling with fallback

    Usage:
        class PolicyEngine(AsyncLoadableEntity[list[PolicyRule]]):
            async def _load_from_db(self) -> list[PolicyRule]:
                async with get_db_context() as db:
                    ...
                    return rules
    """

    def __init__(self):
        self._data: Optional[T] = None
        self._loaded: bool = False
        self._load_error: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        """Check if data has been loaded."""
        return self._loaded

    @property
    def data(self) -> Optional[T]:
        """Get loaded data (may be None if not loaded)."""
        return self._data

    async def ensure_loaded(self) -> None:
        """Ensure data is loaded from database. Safe to call multiple times."""
        if not self._loaded:
            await self.reload()

    async def reload(self) -> None:
        """Force reload data from database."""
        try:
            self._data = await self._load_from_db()
            self._loaded = True
            self._load_error = None
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"Failed to load {self.__class__.__name__} from DB: {e}")
            # Set default value on error
            self._data = self._get_default_value()
            self._loaded = True  # Mark as loaded to avoid retry loops

    def invalidate(self) -> None:
        """Invalidate cached data, forcing reload on next access."""
        self._loaded = False
        self._data = None
        self._load_error = None

    @abstractmethod
    async def _load_from_db(self) -> T:
        """Load data from database. Implement in subclass."""
        raise NotImplementedError

    def _get_default_value(self) -> T:
        """Get default value when loading fails. Override in subclass."""
        return None  # type: ignore


# =============================================================================
# ConditionMatcher - Unified condition matching logic
# =============================================================================


class ConditionMatcher:
    """
    Unified condition matching logic for policies and features.

    Centralizes all the condition checking that was duplicated across:
    - PolicyEngine._rule_matches()
    - PolicyService._check_conditions()
    - FeatureEngine.check_feature() (partial)
    - PolicySimulator.evaluate_policy()

    Usage:
        matcher = ConditionMatcher()
        result = matcher.match_all(conditions, context)
        if result.matches:
            print(f"Matched: {result.reason}")
    """

    @staticmethod
    def matches_environment(
        environment: str,
        allowed: Optional[list[str]] = None,
        denied: Optional[list[str]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if environment matches restrictions.

        Returns:
            (matches, reason) - matches=True means condition is satisfied
        """
        if denied and environment in denied:
            return False, f"Environment '{environment}' is denied"

        if allowed and environment not in allowed:
            return False, f"Environment '{environment}' not in allowed: {allowed}"

        return True, None

    @staticmethod
    def matches_model(
        model: str,
        allowed: Optional[list[str]] = None,
        denied: Optional[list[str]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if model matches restrictions.

        Supports:
        - Exact match: "gpt-4o"
        - Prefix match: "gpt-*" or "claude-*"

        Returns:
            (matches, reason) - matches=True means condition is satisfied
        """
        # Check denied list first
        if denied:
            for pattern in denied:
                if ConditionMatcher._model_matches_pattern(model, pattern):
                    return False, f"Model '{model}' is blocked"

        # Check allowed list
        if allowed:
            for pattern in allowed:
                if ConditionMatcher._model_matches_pattern(model, pattern):
                    return True, None
            return False, f"Model '{model}' not in allowed: {allowed}"

        return True, None

    @staticmethod
    def _model_matches_pattern(model: str, pattern: str) -> bool:
        """Check if model matches a pattern (exact or prefix with *)."""
        if pattern.endswith("*"):
            return model.startswith(pattern[:-1])
        return model == pattern

    @staticmethod
    def matches_feature(
        feature: Optional[str],
        allowed: Optional[list[str]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if feature matches restrictions.

        Returns:
            (matches, reason) - matches=True means condition is satisfied
        """
        if not allowed:
            return True, None

        if not feature:
            return True, None  # No feature specified = no restriction

        if feature not in allowed:
            return False, f"Feature '{feature}' not allowed"

        return True, None

    @staticmethod
    def matches_tokens(
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        max_input: Optional[int] = None,
        max_output: Optional[int] = None,
        max_total: Optional[int] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if token counts are within limits.

        Returns:
            (matches, reason) - matches=True means within limits
        """
        if max_input and input_tokens and input_tokens > max_input:
            return False, f"Input tokens ({input_tokens}) exceeds limit ({max_input})"

        if max_output and output_tokens and output_tokens > max_output:
            return False, f"Output tokens ({output_tokens}) exceeds limit ({max_output})"

        if max_total:
            total = (input_tokens or 0) + (output_tokens or 0)
            if total > max_total:
                return False, f"Total tokens ({total}) exceeds limit ({max_total})"

        return True, None

    @staticmethod
    def matches_time(
        allowed_hours: Optional[tuple[int, int]] = None,
        current_hour: Optional[int] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if current time is within allowed hours.

        Args:
            allowed_hours: (start_hour, end_hour) in 24h format
            current_hour: Current hour (0-23). If None, uses current time.

        Returns:
            (matches, reason) - matches=True means within allowed hours
        """
        if not allowed_hours:
            return True, None

        if current_hour is None:
            from datetime import datetime

            current_hour = datetime.now().hour

        start, end = allowed_hours

        # Handle overnight ranges (e.g., 22-6)
        if start <= end:
            in_range = start <= current_hour < end
        else:
            in_range = current_hour >= start or current_hour < end

        if not in_range:
            return False, f"Current hour ({current_hour}) outside allowed hours ({start}-{end})"

        return True, None

    @staticmethod
    def matches_app(
        app_id: str,
        allowed: Optional[list[str]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if app_id matches restrictions.

        Supports:
        - Exact match
        - Wildcard "*" for all apps

        Returns:
            (matches, reason) - matches=True means condition is satisfied
        """
        if not allowed:
            return True, None

        if "*" in allowed or app_id in allowed:
            return True, None

        return False, f"App '{app_id}' not in allowed list"


class ConditionMatchResult:
    """Result of condition matching."""

    def __init__(self, matches: bool = True, reason: Optional[str] = None):
        self.matches = matches
        self.reason = reason
        self.matched_conditions: list[str] = []
        self.failed_conditions: list[str] = []

    def add_match(self, condition: str) -> None:
        """Record a matched condition."""
        self.matched_conditions.append(condition)

    def add_failure(self, condition: str, reason: str) -> None:
        """Record a failed condition."""
        self.failed_conditions.append(f"{condition}: {reason}")
        self.matches = False
        if not self.reason:
            self.reason = reason

    def __bool__(self) -> bool:
        return self.matches


class ConditionContext:
    """Context for condition matching."""

    def __init__(
        self,
        model: str = "",
        environment: str = "",
        feature: Optional[str] = None,
        app_id: str = "",
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        current_hour: Optional[int] = None,
    ):
        self.model = model
        self.environment = environment
        self.feature = feature
        self.app_id = app_id
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.max_tokens = max_tokens
        self.current_hour = current_hour


def _check_environment_condition(
    conditions: dict, context: ConditionContext, result: ConditionMatchResult
) -> None:
    """Check environment condition and update result."""
    if "environments" not in conditions and "allowed_environments" not in conditions:
        return

    allowed = conditions.get("environments") or conditions.get("allowed_environments")
    denied = conditions.get("denied_environments")
    ok, reason = ConditionMatcher.matches_environment(
        context.environment, allowed=allowed, denied=denied
    )

    if ok:
        result.add_match(f"environment={context.environment}")
    else:
        result.add_failure("environment", reason or "Environment not allowed")


def _check_model_condition(
    conditions: dict, context: ConditionContext, result: ConditionMatchResult
) -> None:
    """Check model condition and update result."""
    if (
        "models" not in conditions
        and "allowed_models" not in conditions
        and "blocked_models" not in conditions
    ):
        return

    allowed = conditions.get("models") or conditions.get("allowed_models")
    denied = conditions.get("blocked_models")
    ok, reason = ConditionMatcher.matches_model(context.model, allowed=allowed, denied=denied)

    if ok:
        result.add_match(f"model={context.model}")
    else:
        result.add_failure("model", reason or "Model not allowed")


def _check_feature_condition(
    conditions: dict, context: ConditionContext, result: ConditionMatchResult
) -> None:
    """Check feature condition and update result."""
    if "features" not in conditions:
        return

    ok, reason = ConditionMatcher.matches_feature(context.feature, allowed=conditions["features"])

    if ok:
        result.add_match(f"feature={context.feature}")
    else:
        result.add_failure("feature", reason or "Feature not allowed")


def _check_token_condition(
    conditions: dict, context: ConditionContext, result: ConditionMatchResult
) -> None:
    """Check token limits condition and update result."""
    max_input = conditions.get("max_context_tokens") or conditions.get("max_input_tokens")
    max_output = conditions.get("max_tokens") or conditions.get("max_output_tokens")

    if not max_input and not max_output:
        return

    ok, reason = ConditionMatcher.matches_tokens(
        input_tokens=context.input_tokens,
        output_tokens=context.output_tokens or context.max_tokens,
        max_input=max_input,
        max_output=max_output,
    )

    if ok:
        result.add_match("tokens within limits")
    else:
        result.add_failure("tokens", reason or "Token limit exceeded")


def _check_time_condition(
    conditions: dict, context: ConditionContext, result: ConditionMatchResult
) -> None:
    """Check time condition and update result."""
    if "allowed_hours" not in conditions:
        return

    hours = conditions["allowed_hours"]
    if not isinstance(hours, (list, tuple)) or len(hours) != 2:
        return

    ok, reason = ConditionMatcher.matches_time(
        allowed_hours=(hours[0], hours[1]),
        current_hour=context.current_hour,
    )

    if ok:
        result.add_match("time within allowed hours")
    else:
        result.add_failure("time", reason or "Outside allowed hours")


def _check_app_condition(
    conditions: dict, context: ConditionContext, result: ConditionMatchResult
) -> None:
    """Check app_id condition and update result."""
    if "app_id" not in conditions:
        return

    ok, reason = ConditionMatcher.matches_app(context.app_id, allowed=[conditions["app_id"]])

    if ok:
        result.add_match(f"app_id={context.app_id}")
    else:
        result.add_failure("app_id", reason or "App not allowed")


def match_conditions(conditions: dict, context: ConditionContext) -> ConditionMatchResult:
    """
    Match all conditions against a context.

    This is the main entry point for unified condition matching.

    Args:
        conditions: Dict of condition name -> value(s)
            Supported conditions:
            - environments: list[str]
            - allowed_models / blocked_models: list[str]
            - features: list[str]
            - max_tokens / max_context_tokens: int
            - allowed_hours: tuple[int, int]
            - app_id: str or "*"

        context: ConditionContext with request details

    Returns:
        ConditionMatchResult with match status and details
    """
    result = ConditionMatchResult()

    _check_environment_condition(conditions, context, result)
    _check_model_condition(conditions, context, result)
    _check_feature_condition(conditions, context, result)
    _check_token_condition(conditions, context, result)
    _check_time_condition(conditions, context, result)
    _check_app_condition(conditions, context, result)

    return result
