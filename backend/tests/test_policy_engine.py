"""Tests for PolicyEngine in gateway.engines.policy."""

import pytest
from datetime import datetime

from backend.application.engines.policy import (
    PolicyEngine,
    PolicyRule,
    PolicyDecision,
)
from backend.core.contracts import UsageContract, Environment, ActionType
from backend.core.auth import AppCredentials


@pytest.fixture
def mock_contract():
    """Create a mock UsageContract for testing."""
    return UsageContract(
        app_id="test-app",
        environment=Environment.PRODUCTION,
        feature="chat",
        action=ActionType.GENERATE,
    )


@pytest.fixture
def mock_credentials():
    """Create mock AppCredentials for testing."""
    return AppCredentials(
        app_id="test-app",
        api_key_id=1,
        api_key_prefix="gw_test_key",
        owner="test-team",
        environment="production",
        created_at=datetime.now(),
        allowed_models=[],  # Empty = all allowed
    )


class TestPolicyEngine:
    """Tests for PolicyEngine class."""

    def test_init_empty(self):
        """Engine should start with no rules."""
        engine = PolicyEngine()
        assert engine.rules == []
        assert engine.is_loaded is False

    def test_init_with_rules(self):
        """Engine can be initialized with rules."""
        rules = [
            PolicyRule(name="rule1"),
            PolicyRule(name="rule2"),
        ]
        engine = PolicyEngine(rules=rules)

        assert len(engine.rules) == 2
        assert engine.is_loaded is True

    def test_rules_property_setter(self):
        """Rules can be set via property."""
        engine = PolicyEngine()
        rules = [PolicyRule(name="new-rule")]

        engine.rules = rules

        assert engine.rules == rules
        assert engine.is_loaded is True


class TestPolicyEngineEvaluate:
    """Tests for PolicyEngine.evaluate method."""

    def test_evaluate_no_rules_allows(self, mock_contract, mock_credentials):
        """No rules should allow the request."""
        engine = PolicyEngine(rules=[])

        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o")

        assert result.decision == PolicyDecision.ALLOW
        assert result.reason is None
        assert result.warnings == []

    def test_evaluate_disabled_rule_ignored(self, mock_contract, mock_credentials):
        """Disabled rules should be ignored."""
        rules = [
            PolicyRule(
                name="disabled-rule",
                enabled=False,
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)

        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o")

        assert result.decision == PolicyDecision.ALLOW
        assert "disabled-rule" not in result.matched_rules

    def test_evaluate_rule_environment_filter(self, mock_contract, mock_credentials):
        """Rule should only match specified environments."""
        rules = [
            PolicyRule(
                name="staging-only",
                environments=[Environment.STAGING],
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)

        # Production contract should not match staging-only rule
        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o")

        assert result.decision == PolicyDecision.ALLOW
        assert "staging-only" not in result.matched_rules

    def test_evaluate_rule_environment_matches(self, mock_credentials):
        """Rule should match when environment matches."""
        rules = [
            PolicyRule(
                name="prod-limit",
                environments=[Environment.PRODUCTION],
                max_tokens=100,
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)
        contract = UsageContract(
            app_id="test-app",
            environment=Environment.PRODUCTION,
            feature="chat",
            action=ActionType.GENERATE,
        )

        # Request exceeds max_tokens
        result = engine.evaluate(contract, mock_credentials, "gpt-4o", max_tokens=200)

        assert result.decision == PolicyDecision.DENY
        assert "prod-limit" in result.matched_rules

    def test_evaluate_token_limit_deny(self, mock_contract, mock_credentials):
        """Should deny when token limit exceeded with DENY action."""
        rules = [
            PolicyRule(
                name="token-limit",
                max_tokens=1000,
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)

        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o", max_tokens=2000)

        assert result.decision == PolicyDecision.DENY
        assert "token-limit" in result.matched_rules
        assert "2000" in result.reason
        assert "1000" in result.reason

    def test_evaluate_token_limit_warn(self, mock_contract, mock_credentials):
        """Should warn when token limit exceeded with WARN action."""
        rules = [
            PolicyRule(
                name="soft-limit",
                max_tokens=1000,
                action=PolicyDecision.WARN,
            )
        ]
        engine = PolicyEngine(rules=rules)

        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o", max_tokens=2000)

        assert result.decision == PolicyDecision.ALLOW
        assert len(result.warnings) > 0
        assert "2000" in result.warnings[0]

    def test_evaluate_token_limit_under_limit(self, mock_contract, mock_credentials):
        """Should allow when under token limit."""
        rules = [
            PolicyRule(
                name="token-limit",
                max_tokens=1000,
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)

        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o", max_tokens=500)

        assert result.decision == PolicyDecision.ALLOW

    def test_evaluate_model_whitelist_allowed(self, mock_contract, mock_credentials):
        """Should allow model in whitelist."""
        rules = [
            PolicyRule(
                name="model-whitelist",
                models=["gpt-4o", "gpt-4o-mini"],
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)

        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o")

        assert result.decision == PolicyDecision.ALLOW

    def test_evaluate_model_whitelist_denied(self, mock_contract, mock_credentials):
        """Should deny model not in whitelist."""
        rules = [
            PolicyRule(
                name="model-whitelist",
                models=["gpt-4o-mini"],
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)

        result = engine.evaluate(mock_contract, mock_credentials, "claude-3-opus")

        assert result.decision == PolicyDecision.DENY
        assert "not in allowed" in result.reason

    def test_evaluate_model_pattern_matching(self, mock_contract, mock_credentials):
        """Should support pattern matching for models."""
        rules = [
            PolicyRule(
                name="gpt-only",
                models=["gpt-*"],
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)

        # gpt-4o should match gpt-*
        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o")
        assert result.decision == PolicyDecision.ALLOW

        # claude should not match gpt-*
        result = engine.evaluate(mock_contract, mock_credentials, "claude-3-opus")
        assert result.decision == PolicyDecision.DENY

    def test_evaluate_feature_filter(self, mock_credentials):
        """Rule should only match specified features."""
        rules = [
            PolicyRule(
                name="chat-only",
                features=["chat"],
                max_tokens=100,
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)

        # Chat feature should match
        chat_contract = UsageContract(
            app_id="test-app",
            environment=Environment.PRODUCTION,
            feature="chat",
            action=ActionType.GENERATE,
        )
        result = engine.evaluate(chat_contract, mock_credentials, "gpt-4o", max_tokens=200)
        assert result.decision == PolicyDecision.DENY

        # Embedding feature should not match
        embed_contract = UsageContract(
            app_id="test-app",
            environment=Environment.PRODUCTION,
            feature="embedding",
            action=ActionType.EMBED,
        )
        result = engine.evaluate(embed_contract, mock_credentials, "gpt-4o", max_tokens=200)
        assert result.decision == PolicyDecision.ALLOW

    def test_evaluate_app_filter(self, mock_credentials):
        """Rule should only match specified apps."""
        rules = [
            PolicyRule(
                name="app-specific",
                apps=["other-app"],
                action=PolicyDecision.DENY,
            )
        ]
        engine = PolicyEngine(rules=rules)
        contract = UsageContract(
            app_id="test-app",
            environment=Environment.PRODUCTION,
            feature="chat",
            action=ActionType.GENERATE,
        )

        result = engine.evaluate(contract, mock_credentials, "gpt-4o")

        # Should not match because app_id doesn't match
        assert result.decision == PolicyDecision.ALLOW

    def test_evaluate_credentials_model_restriction(self, mock_contract):
        """Should enforce model restrictions from credentials."""
        engine = PolicyEngine(rules=[])
        credentials = AppCredentials(
            app_id="test-app",
            api_key_id=1,
            api_key_prefix="gw_test_key",
            owner="test-team",
            environment="production",
            created_at=datetime.now(),
            allowed_models=["gpt-4o-mini"],  # Only mini allowed
        )

        result = engine.evaluate(mock_contract, credentials, "gpt-4o")

        assert result.decision == PolicyDecision.DENY
        assert "not allowed" in result.reason
        assert "test-app" in result.reason

    def test_evaluate_multiple_rules_first_deny_wins(self, mock_contract, mock_credentials):
        """First matching DENY rule should terminate evaluation."""
        rules = [
            PolicyRule(
                name="deny-all",
                action=PolicyDecision.DENY,
                max_tokens=100,
            ),
            PolicyRule(
                name="would-allow",
                action=PolicyDecision.ALLOW,
            ),
        ]
        engine = PolicyEngine(rules=rules)

        result = engine.evaluate(mock_contract, mock_credentials, "gpt-4o", max_tokens=200)

        assert result.decision == PolicyDecision.DENY
        assert "deny-all" in result.matched_rules


class TestPolicyEngineRuleMatches:
    """Tests for PolicyEngine._rule_matches method."""

    def test_rule_matches_no_conditions(self):
        """Rule with no conditions should always match."""
        engine = PolicyEngine()
        rule = PolicyRule(name="catch-all")

        from backend.core.base import ConditionContext

        context = ConditionContext(
            model="gpt-4o",
            environment="production",
            app_id="test-app",
        )

        assert engine._rule_matches(rule, context) is True

    def test_rule_matches_environment_condition(self):
        """Rule should match only specified environments."""
        engine = PolicyEngine()
        rule = PolicyRule(name="staging-rule", environments=[Environment.STAGING])

        from backend.core.base import ConditionContext

        staging_ctx = ConditionContext(environment="staging")
        assert engine._rule_matches(rule, staging_ctx) is True

        prod_ctx = ConditionContext(environment="production")
        assert engine._rule_matches(rule, prod_ctx) is False

    def test_rule_matches_app_condition(self):
        """Rule should match only specified apps."""
        engine = PolicyEngine()
        rule = PolicyRule(name="app-rule", apps=["my-app", "other-app"])

        from backend.core.base import ConditionContext

        my_app_ctx = ConditionContext(app_id="my-app")
        assert engine._rule_matches(rule, my_app_ctx) is True

        unknown_ctx = ConditionContext(app_id="unknown-app")
        assert engine._rule_matches(rule, unknown_ctx) is False

    def test_rule_matches_feature_condition(self):
        """Rule should match only specified features."""
        engine = PolicyEngine()
        rule = PolicyRule(name="feature-rule", features=["chat", "completion"])

        from backend.core.base import ConditionContext

        chat_ctx = ConditionContext(feature="chat")
        assert engine._rule_matches(rule, chat_ctx) is True

        embed_ctx = ConditionContext(feature="embedding")
        assert engine._rule_matches(rule, embed_ctx) is False


class TestPolicyEngineAsync:
    """Tests for async methods of PolicyEngine."""

    @pytest.mark.asyncio
    async def test_evaluate_async_loads_first(self, mock_contract, mock_credentials):
        """evaluate_async should ensure data is loaded first."""
        rules = [PolicyRule(name="test-rule")]
        engine = PolicyEngine(rules=rules)

        result = await engine.evaluate_async(mock_contract, mock_credentials, "gpt-4o")

        assert result.decision == PolicyDecision.ALLOW
        assert engine.is_loaded is True

    @pytest.mark.asyncio
    async def test_get_default_value(self):
        """_get_default_value should return empty list."""
        engine = PolicyEngine()
        assert engine._get_default_value() == []
