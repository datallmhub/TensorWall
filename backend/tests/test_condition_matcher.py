"""Tests for ConditionMatcher and related classes in gateway.core.base."""

from backend.core.base import (
    ConditionMatcher,
    ConditionMatchResult,
    ConditionContext,
    match_conditions,
)


class TestConditionMatcher:
    """Tests for ConditionMatcher static methods."""

    # -------------------------------------------------------------------------
    # matches_environment tests
    # -------------------------------------------------------------------------

    def test_matches_environment_no_restrictions(self):
        """Environment should match when no restrictions are set."""
        ok, reason = ConditionMatcher.matches_environment("production")
        assert ok is True
        assert reason is None

    def test_matches_environment_in_allowed_list(self):
        """Environment should match when in allowed list."""
        ok, reason = ConditionMatcher.matches_environment(
            "production", allowed=["staging", "production"]
        )
        assert ok is True
        assert reason is None

    def test_matches_environment_not_in_allowed_list(self):
        """Environment should not match when not in allowed list."""
        ok, reason = ConditionMatcher.matches_environment(
            "development", allowed=["staging", "production"]
        )
        assert ok is False
        assert "development" in reason
        assert "not in allowed" in reason

    def test_matches_environment_in_denied_list(self):
        """Environment should not match when in denied list."""
        ok, reason = ConditionMatcher.matches_environment("production", denied=["production"])
        assert ok is False
        assert "denied" in reason

    def test_matches_environment_denied_takes_priority(self):
        """Denied list should take priority over allowed list."""
        ok, reason = ConditionMatcher.matches_environment(
            "production", allowed=["production"], denied=["production"]
        )
        assert ok is False
        assert "denied" in reason

    # -------------------------------------------------------------------------
    # matches_model tests
    # -------------------------------------------------------------------------

    def test_matches_model_no_restrictions(self):
        """Model should match when no restrictions are set."""
        ok, reason = ConditionMatcher.matches_model("gpt-4o")
        assert ok is True
        assert reason is None

    def test_matches_model_exact_match_in_allowed(self):
        """Model should match exactly when in allowed list."""
        ok, reason = ConditionMatcher.matches_model("gpt-4o", allowed=["gpt-4o", "gpt-4o-mini"])
        assert ok is True
        assert reason is None

    def test_matches_model_not_in_allowed(self):
        """Model should not match when not in allowed list."""
        ok, reason = ConditionMatcher.matches_model(
            "claude-3-opus", allowed=["gpt-4o", "gpt-4o-mini"]
        )
        assert ok is False
        assert "not in allowed" in reason

    def test_matches_model_prefix_pattern_match(self):
        """Model should match prefix pattern (gpt-*)."""
        ok, reason = ConditionMatcher.matches_model("gpt-4o-mini", allowed=["gpt-*"])
        assert ok is True
        assert reason is None

    def test_matches_model_prefix_pattern_no_match(self):
        """Model should not match non-matching prefix pattern."""
        ok, reason = ConditionMatcher.matches_model("claude-3-opus", allowed=["gpt-*"])
        assert ok is False

    def test_matches_model_denied_exact(self):
        """Model should not match when in denied list."""
        ok, reason = ConditionMatcher.matches_model("gpt-4o", denied=["gpt-4o"])
        assert ok is False
        assert "blocked" in reason

    def test_matches_model_denied_pattern(self):
        """Model should not match when matching denied pattern."""
        ok, reason = ConditionMatcher.matches_model("gpt-4o-mini", denied=["gpt-*"])
        assert ok is False
        assert "blocked" in reason

    def test_matches_model_denied_takes_priority(self):
        """Denied should take priority over allowed."""
        ok, reason = ConditionMatcher.matches_model("gpt-4o", allowed=["gpt-4o"], denied=["gpt-4o"])
        assert ok is False

    # -------------------------------------------------------------------------
    # matches_feature tests
    # -------------------------------------------------------------------------

    def test_matches_feature_no_restrictions(self):
        """Feature should match when no restrictions are set."""
        ok, reason = ConditionMatcher.matches_feature("chat")
        assert ok is True
        assert reason is None

    def test_matches_feature_no_feature_specified(self):
        """No feature should always match (no restriction)."""
        ok, reason = ConditionMatcher.matches_feature(None, allowed=["chat", "completion"])
        assert ok is True
        assert reason is None

    def test_matches_feature_in_allowed(self):
        """Feature should match when in allowed list."""
        ok, reason = ConditionMatcher.matches_feature("chat", allowed=["chat", "completion"])
        assert ok is True
        assert reason is None

    def test_matches_feature_not_in_allowed(self):
        """Feature should not match when not in allowed list."""
        ok, reason = ConditionMatcher.matches_feature("embedding", allowed=["chat", "completion"])
        assert ok is False
        assert "not allowed" in reason

    # -------------------------------------------------------------------------
    # matches_tokens tests
    # -------------------------------------------------------------------------

    def test_matches_tokens_no_limits(self):
        """Tokens should match when no limits are set."""
        ok, reason = ConditionMatcher.matches_tokens(input_tokens=1000, output_tokens=500)
        assert ok is True
        assert reason is None

    def test_matches_tokens_within_input_limit(self):
        """Tokens should match when within input limit."""
        ok, reason = ConditionMatcher.matches_tokens(input_tokens=1000, max_input=2000)
        assert ok is True
        assert reason is None

    def test_matches_tokens_exceeds_input_limit(self):
        """Tokens should not match when exceeding input limit."""
        ok, reason = ConditionMatcher.matches_tokens(input_tokens=3000, max_input=2000)
        assert ok is False
        assert "Input tokens" in reason
        assert "3000" in reason

    def test_matches_tokens_within_output_limit(self):
        """Tokens should match when within output limit."""
        ok, reason = ConditionMatcher.matches_tokens(output_tokens=500, max_output=1000)
        assert ok is True
        assert reason is None

    def test_matches_tokens_exceeds_output_limit(self):
        """Tokens should not match when exceeding output limit."""
        ok, reason = ConditionMatcher.matches_tokens(output_tokens=1500, max_output=1000)
        assert ok is False
        assert "Output tokens" in reason

    def test_matches_tokens_within_total_limit(self):
        """Tokens should match when total is within limit."""
        ok, reason = ConditionMatcher.matches_tokens(
            input_tokens=1000, output_tokens=500, max_total=2000
        )
        assert ok is True
        assert reason is None

    def test_matches_tokens_exceeds_total_limit(self):
        """Tokens should not match when total exceeds limit."""
        ok, reason = ConditionMatcher.matches_tokens(
            input_tokens=1000, output_tokens=1500, max_total=2000
        )
        assert ok is False
        assert "Total tokens" in reason
        assert "2500" in reason

    # -------------------------------------------------------------------------
    # matches_time tests
    # -------------------------------------------------------------------------

    def test_matches_time_no_restrictions(self):
        """Time should match when no restrictions are set."""
        ok, reason = ConditionMatcher.matches_time()
        assert ok is True
        assert reason is None

    def test_matches_time_within_allowed_hours(self):
        """Time should match when within allowed hours."""
        ok, reason = ConditionMatcher.matches_time(allowed_hours=(9, 17), current_hour=12)
        assert ok is True
        assert reason is None

    def test_matches_time_outside_allowed_hours(self):
        """Time should not match when outside allowed hours."""
        ok, reason = ConditionMatcher.matches_time(allowed_hours=(9, 17), current_hour=20)
        assert ok is False
        assert "outside allowed hours" in reason

    def test_matches_time_overnight_range_inside(self):
        """Time should match overnight range (e.g., 22-6) when inside."""
        ok, reason = ConditionMatcher.matches_time(allowed_hours=(22, 6), current_hour=23)
        assert ok is True
        assert reason is None

        ok, reason = ConditionMatcher.matches_time(allowed_hours=(22, 6), current_hour=3)
        assert ok is True
        assert reason is None

    def test_matches_time_overnight_range_outside(self):
        """Time should not match overnight range when outside."""
        ok, reason = ConditionMatcher.matches_time(allowed_hours=(22, 6), current_hour=12)
        assert ok is False

    # -------------------------------------------------------------------------
    # matches_app tests
    # -------------------------------------------------------------------------

    def test_matches_app_no_restrictions(self):
        """App should match when no restrictions are set."""
        ok, reason = ConditionMatcher.matches_app("my-app")
        assert ok is True
        assert reason is None

    def test_matches_app_in_allowed(self):
        """App should match when in allowed list."""
        ok, reason = ConditionMatcher.matches_app("my-app", allowed=["my-app", "other-app"])
        assert ok is True
        assert reason is None

    def test_matches_app_not_in_allowed(self):
        """App should not match when not in allowed list."""
        ok, reason = ConditionMatcher.matches_app("unknown-app", allowed=["my-app", "other-app"])
        assert ok is False
        assert "not in allowed" in reason

    def test_matches_app_wildcard(self):
        """App should match with wildcard '*'."""
        ok, reason = ConditionMatcher.matches_app("any-app", allowed=["*"])
        assert ok is True
        assert reason is None


class TestConditionMatchResult:
    """Tests for ConditionMatchResult class."""

    def test_initial_state(self):
        """Result should start with matches=True."""
        result = ConditionMatchResult()
        assert result.matches is True
        assert result.reason is None
        assert result.matched_conditions == []
        assert result.failed_conditions == []

    def test_add_match(self):
        """Adding a match should track the condition."""
        result = ConditionMatchResult()
        result.add_match("environment=production")
        assert result.matches is True
        assert "environment=production" in result.matched_conditions

    def test_add_failure(self):
        """Adding a failure should set matches=False and track reason."""
        result = ConditionMatchResult()
        result.add_failure("model", "Model not allowed")
        assert result.matches is False
        assert result.reason == "Model not allowed"
        assert "model: Model not allowed" in result.failed_conditions

    def test_bool_conversion(self):
        """Result should be truthy when matches, falsy otherwise."""
        result = ConditionMatchResult()
        assert bool(result) is True

        result.add_failure("test", "failed")
        assert bool(result) is False


class TestConditionContext:
    """Tests for ConditionContext class."""

    def test_default_values(self):
        """Context should have sensible defaults."""
        context = ConditionContext()
        assert context.model == ""
        assert context.environment == ""
        assert context.feature is None
        assert context.app_id == ""
        assert context.input_tokens is None
        assert context.output_tokens is None
        assert context.max_tokens is None
        assert context.current_hour is None

    def test_custom_values(self):
        """Context should accept custom values."""
        context = ConditionContext(
            model="gpt-4o",
            environment="production",
            feature="chat",
            app_id="my-app",
            input_tokens=1000,
            output_tokens=500,
            max_tokens=2000,
            current_hour=14,
        )
        assert context.model == "gpt-4o"
        assert context.environment == "production"
        assert context.feature == "chat"
        assert context.app_id == "my-app"
        assert context.input_tokens == 1000
        assert context.output_tokens == 500
        assert context.max_tokens == 2000
        assert context.current_hour == 14


class TestMatchConditions:
    """Tests for match_conditions function."""

    def test_empty_conditions(self):
        """Empty conditions should always match."""
        context = ConditionContext(model="gpt-4o", environment="production")
        result = match_conditions({}, context)
        assert result.matches is True

    def test_environment_condition(self):
        """Environment condition should be checked."""
        context = ConditionContext(model="gpt-4o", environment="production")

        result = match_conditions({"environments": ["production"]}, context)
        assert result.matches is True
        assert "environment=production" in result.matched_conditions

        result = match_conditions({"environments": ["staging"]}, context)
        assert result.matches is False

    def test_model_condition(self):
        """Model condition should be checked."""
        context = ConditionContext(model="gpt-4o", environment="production")

        result = match_conditions({"models": ["gpt-4o", "gpt-4o-mini"]}, context)
        assert result.matches is True

        result = match_conditions({"blocked_models": ["gpt-*"]}, context)
        assert result.matches is False

    def test_feature_condition(self):
        """Feature condition should be checked."""
        context = ConditionContext(model="gpt-4o", environment="production", feature="chat")

        result = match_conditions({"features": ["chat", "completion"]}, context)
        assert result.matches is True

        result = match_conditions({"features": ["embedding"]}, context)
        assert result.matches is False

    def test_token_condition(self):
        """Token limits should be checked."""
        context = ConditionContext(model="gpt-4o", environment="production", max_tokens=2000)

        result = match_conditions({"max_tokens": 4000}, context)
        assert result.matches is True

        result = match_conditions({"max_tokens": 1000}, context)
        assert result.matches is False

    def test_time_condition(self):
        """Time condition should be checked."""
        context = ConditionContext(model="gpt-4o", environment="production", current_hour=14)

        result = match_conditions({"allowed_hours": [9, 17]}, context)
        assert result.matches is True

        result = match_conditions({"allowed_hours": [18, 22]}, context)
        assert result.matches is False

    def test_app_condition(self):
        """App condition should be checked."""
        context = ConditionContext(model="gpt-4o", environment="production", app_id="my-app")

        result = match_conditions({"app_id": "my-app"}, context)
        assert result.matches is True

        result = match_conditions({"app_id": "other-app"}, context)
        assert result.matches is False

    def test_multiple_conditions_all_pass(self):
        """All conditions must pass for overall match."""
        context = ConditionContext(
            model="gpt-4o",
            environment="production",
            feature="chat",
            app_id="my-app",
        )

        result = match_conditions(
            {
                "environments": ["production"],
                "models": ["gpt-*"],
                "features": ["chat"],
            },
            context,
        )
        assert result.matches is True
        assert len(result.matched_conditions) == 3

    def test_multiple_conditions_one_fails(self):
        """If any condition fails, overall match should fail."""
        context = ConditionContext(
            model="gpt-4o",
            environment="development",  # Not in allowed list
            feature="chat",
        )

        result = match_conditions(
            {
                "environments": ["production"],  # Will fail
                "models": ["gpt-*"],  # Would pass
            },
            context,
        )
        assert result.matches is False
        assert len(result.failed_conditions) == 1

    def test_alternative_condition_keys(self):
        """Alternative condition keys should work."""
        context = ConditionContext(model="gpt-4o", environment="production")

        # allowed_environments instead of environments
        result = match_conditions({"allowed_environments": ["production"]}, context)
        assert result.matches is True

        # allowed_models instead of models
        result = match_conditions({"allowed_models": ["gpt-4o"]}, context)
        assert result.matches is True
