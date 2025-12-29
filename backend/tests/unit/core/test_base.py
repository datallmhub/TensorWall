"""Unit tests for Base classes and mixins."""

import pytest
from typing import List

from backend.core.base import (
    AsyncLoadableEntity,
    ConditionMatcher,
    ConditionMatchResult,
    ConditionContext,
    match_conditions,
)


class SampleEntity(AsyncLoadableEntity[List[str]]):
    """Sample implementation of AsyncLoadableEntity for testing."""

    def __init__(self, data_to_return: List[str] = None, should_fail: bool = False):
        super().__init__()
        self._data_to_return = data_to_return or ["item1", "item2"]
        self._should_fail = should_fail

    async def _load_from_db(self) -> List[str]:
        if self._should_fail:
            raise Exception("Database error")
        return self._data_to_return

    def _get_default_value(self) -> List[str]:
        return []


class TestAsyncLoadableEntity:
    """Tests for AsyncLoadableEntity base class."""

    def test_init(self):
        """Test initialization."""
        entity = SampleEntity()

        assert entity._data is None
        assert entity._loaded is False
        assert entity._load_error is None

    def test_is_loaded_property(self):
        """Test is_loaded property."""
        entity = SampleEntity()

        assert entity.is_loaded is False

    def test_data_property(self):
        """Test data property when not loaded."""
        entity = SampleEntity()

        assert entity.data is None

    @pytest.mark.asyncio
    async def test_ensure_loaded(self):
        """Test ensure_loaded loads data."""
        entity = SampleEntity(data_to_return=["a", "b", "c"])

        await entity.ensure_loaded()

        assert entity.is_loaded is True
        assert entity.data == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_ensure_loaded_multiple_calls(self):
        """Test ensure_loaded only loads once."""
        entity = SampleEntity()

        await entity.ensure_loaded()
        await entity.ensure_loaded()
        await entity.ensure_loaded()

        assert entity.is_loaded is True

    @pytest.mark.asyncio
    async def test_reload(self):
        """Test reload forces new data load."""
        entity = SampleEntity(data_to_return=["x", "y"])

        await entity.reload()

        assert entity.is_loaded is True
        assert entity.data == ["x", "y"]

    @pytest.mark.asyncio
    async def test_reload_on_error(self):
        """Test reload handles errors gracefully."""
        entity = SampleEntity(should_fail=True)

        await entity.reload()

        assert entity.is_loaded is True
        assert entity.data == []  # Default value
        assert entity._load_error is not None

    def test_invalidate(self):
        """Test invalidate clears data."""
        entity = SampleEntity()
        entity._loaded = True
        entity._data = ["test"]

        entity.invalidate()

        assert entity.is_loaded is False
        assert entity.data is None
        assert entity._load_error is None


class TestConditionMatchResult:
    """Tests for ConditionMatchResult model."""

    def test_create_match(self):
        """Test creating a matching result."""
        result = ConditionMatchResult(
            matches=True,
            reason="All conditions matched",
        )

        assert result.matches is True
        assert result.reason == "All conditions matched"

    def test_create_no_match(self):
        """Test creating a non-matching result."""
        result = ConditionMatchResult(
            matches=False,
            reason="Environment mismatch",
        )
        result.failed_conditions.append("environment")

        assert result.matches is False
        assert "environment" in result.failed_conditions

    def test_add_match(self):
        """Test adding matched conditions."""
        result = ConditionMatchResult(matches=True)
        result.add_match("environment")
        result.add_match("model")

        assert "environment" in result.matched_conditions
        assert "model" in result.matched_conditions

    def test_add_failure(self):
        """Test adding failed conditions."""
        result = ConditionMatchResult(matches=False)
        result.add_failure("budget", "Budget exceeded")

        assert any("budget" in fc for fc in result.failed_conditions)


class TestConditionContext:
    """Tests for ConditionContext model."""

    def test_create_minimal(self):
        """Test creating context with minimal fields."""
        context = ConditionContext(
            app_id="test-app",
            environment="development",
        )

        assert context.app_id == "test-app"
        assert context.environment == "development"

    def test_create_full(self):
        """Test creating context with all fields."""
        context = ConditionContext(
            app_id="test-app",
            environment="production",
            feature="chat",
            model="gpt-4",
            max_tokens=1000,
            input_tokens=500,
            output_tokens=500,
            current_hour=14,
        )

        assert context.model == "gpt-4"
        assert context.max_tokens == 1000


class TestConditionMatcher:
    """Tests for ConditionMatcher."""

    def test_matches_environment_any(self):
        """Test environment matching with no restrictions."""
        matches, reason = ConditionMatcher.matches_environment("production", None)
        assert matches is True
        assert reason is None

    def test_matches_environment_allowed(self):
        """Test environment matching with allowed list."""
        matches, reason = ConditionMatcher.matches_environment(
            "production",
            allowed=["production", "staging"],
        )
        assert matches is True

    def test_matches_environment_not_allowed(self):
        """Test environment not in allowed list."""
        matches, reason = ConditionMatcher.matches_environment(
            "development",
            allowed=["production", "staging"],
        )
        assert matches is False
        assert "not in allowed" in reason

    def test_matches_environment_denied(self):
        """Test environment in denied list."""
        matches, reason = ConditionMatcher.matches_environment(
            "sandbox",
            denied=["sandbox"],
        )
        assert matches is False
        assert "denied" in reason

    def test_matches_model_any(self):
        """Test model matching with no restrictions."""
        matches, reason = ConditionMatcher.matches_model("gpt-4", None)
        assert matches is True

    def test_matches_model_allowed(self):
        """Test model matching with allowed list."""
        matches, reason = ConditionMatcher.matches_model(
            "gpt-4",
            allowed=["gpt-4", "gpt-3.5-turbo"],
        )
        assert matches is True

    def test_matches_model_not_allowed(self):
        """Test model not in allowed list."""
        matches, reason = ConditionMatcher.matches_model(
            "claude-3",
            allowed=["gpt-4", "gpt-3.5-turbo"],
        )
        assert matches is False

    def test_matches_model_wildcard(self):
        """Test model matching with wildcard pattern."""
        matches, reason = ConditionMatcher.matches_model(
            "gpt-4-turbo",
            allowed=["gpt-*"],
        )
        assert matches is True

    def test_matches_model_denied(self):
        """Test model in denied list."""
        matches, reason = ConditionMatcher.matches_model(
            "gpt-4",
            denied=["gpt-4"],
        )
        assert matches is False

    def test_matches_feature_any(self):
        """Test feature matching with no restrictions."""
        matches, reason = ConditionMatcher.matches_feature("chat", None)
        assert matches is True

    def test_matches_feature_allowed(self):
        """Test feature matching with allowed list."""
        matches, reason = ConditionMatcher.matches_feature(
            "chat",
            allowed=["chat", "embeddings"],
        )
        assert matches is True

    def test_matches_feature_not_allowed(self):
        """Test feature not in allowed list."""
        matches, reason = ConditionMatcher.matches_feature(
            "images",
            allowed=["chat", "embeddings"],
        )
        assert matches is False

    def test_matches_app_any(self):
        """Test app matching with no restrictions."""
        matches, reason = ConditionMatcher.matches_app("any-app", None)
        assert matches is True

    def test_matches_app_allowed(self):
        """Test app matching with allowed list."""
        matches, reason = ConditionMatcher.matches_app(
            "app-1",
            allowed=["app-1", "app-2"],
        )
        assert matches is True

    def test_matches_app_not_allowed(self):
        """Test app not in allowed list."""
        matches, reason = ConditionMatcher.matches_app(
            "app-3",
            allowed=["app-1", "app-2"],
        )
        assert matches is False


class TestConditionMatcherTokens:
    """Tests for token matching in ConditionMatcher."""

    def test_matches_tokens_no_limit(self):
        """Test token matching with no limit."""
        matches, reason = ConditionMatcher.matches_tokens(
            input_tokens=1000,
            output_tokens=500,
            max_input=None,
            max_output=None,
            max_total=None,
        )
        assert matches is True

    def test_matches_tokens_within_limit(self):
        """Test token matching within limits."""
        matches, reason = ConditionMatcher.matches_tokens(
            input_tokens=100,
            output_tokens=100,
            max_input=1000,
            max_output=1000,
            max_total=2000,
        )
        assert matches is True

    def test_matches_tokens_exceeds_input(self):
        """Test token matching exceeding input limit."""
        matches, reason = ConditionMatcher.matches_tokens(
            input_tokens=2000,
            output_tokens=100,
            max_input=1000,
            max_output=1000,
            max_total=None,
        )
        assert matches is False


class TestMatchConditions:
    """Tests for match_conditions convenience function."""

    def test_match_empty_conditions(self):
        """Test matching with empty conditions."""
        context = ConditionContext(
            app_id="test",
            environment="development",
        )
        conditions = {}

        result = match_conditions(conditions, context)

        assert result.matches is True

    def test_match_environment_condition(self):
        """Test matching environment condition."""
        context = ConditionContext(
            app_id="test",
            environment="production",
        )
        conditions = {
            "environments": ["production", "staging"],
        }

        result = match_conditions(conditions, context)

        assert result.matches is True

    def test_fail_environment_condition(self):
        """Test failing environment condition."""
        context = ConditionContext(
            app_id="test",
            environment="development",
        )
        conditions = {
            "environments": ["production"],
        }

        result = match_conditions(conditions, context)

        assert result.matches is False
