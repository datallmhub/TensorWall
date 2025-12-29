"""Tests for PolicySimulator in gateway.core.dry_run."""

import pytest

from backend.core.dry_run import (
    DryRunMode,
    PolicyImpact,
    DryRunResult,
    PolicySimulator,
)
from backend.core.decisions import DecisionChain


class TestDryRunMode:
    """Tests for DryRunMode enum."""

    def test_modes_exist(self):
        """All expected modes should exist."""
        assert DryRunMode.FULL == "full"
        assert DryRunMode.POLICIES_ONLY == "policies_only"
        assert DryRunMode.BUDGET_ONLY == "budget_only"
        assert DryRunMode.SECURITY_ONLY == "security_only"


class TestPolicyImpact:
    """Tests for PolicyImpact model."""

    def test_create_policy_impact(self):
        """Should create PolicyImpact with required fields."""
        impact = PolicyImpact(
            policy_id="policy-1",
            policy_name="Test Policy",
            would_match=True,
            action="deny",
            reason="Token limit exceeded",
            priority=10,
        )

        assert impact.policy_id == "policy-1"
        assert impact.policy_name == "Test Policy"
        assert impact.would_match is True
        assert impact.action == "deny"
        assert impact.priority == 10

    def test_policy_impact_with_conditions(self):
        """Should store matched and failed conditions."""
        impact = PolicyImpact(
            policy_id="policy-1",
            policy_name="Test Policy",
            would_match=True,
            action="deny",
            reason="Multiple conditions",
            priority=10,
            conditions_matched=["environment=production", "model=gpt-4o"],
            conditions_failed=["max_tokens: exceeded limit"],
        )

        assert len(impact.conditions_matched) == 2
        assert len(impact.conditions_failed) == 1


class TestDryRunResult:
    """Tests for DryRunResult model."""

    def test_create_dry_run_result(self):
        """Should create DryRunResult with required fields."""
        result = DryRunResult(
            request_id="req-123",
            app_id="test-app",
            model="gpt-4o",
            environment="production",
            mode=DryRunMode.FULL,
            would_be_allowed=True,
            decision_chain=DecisionChain(request_id="req-123"),
        )

        assert result.request_id == "req-123"
        assert result.app_id == "test-app"
        assert result.model == "gpt-4o"
        assert result.would_be_allowed is True

    def test_to_summary(self):
        """to_summary should return compact representation."""
        result = DryRunResult(
            request_id="req-123",
            app_id="test-app",
            model="gpt-4o",
            environment="production",
            mode=DryRunMode.POLICIES_ONLY,
            would_be_allowed=False,
            blocking_reason="Token limit exceeded",
            decision_chain=DecisionChain(request_id="req-123"),
            policies_evaluated=[
                PolicyImpact(
                    policy_id="p1",
                    policy_name="Policy 1",
                    would_match=True,
                    action="deny",
                    reason="test",
                    priority=1,
                )
            ],
            policies_that_would_block=[
                PolicyImpact(
                    policy_id="p1",
                    policy_name="Policy 1",
                    would_match=True,
                    action="deny",
                    reason="test",
                    priority=1,
                )
            ],
            recommendations=["Reduce max_tokens"],
        )

        summary = result.to_summary()

        assert summary["would_be_allowed"] is False
        assert summary["blocking_reason"] == "Token limit exceeded"
        assert summary["policies_evaluated"] == 1
        assert summary["policies_blocking"] == 1
        assert "Reduce max_tokens" in summary["recommendations"]


class TestPolicySimulator:
    """Tests for PolicySimulator class."""

    def test_init(self):
        """Simulator should initialize correctly."""
        simulator = PolicySimulator()
        assert simulator.is_loaded is False
        assert simulator.policies == []

    def test_get_default_value(self):
        """_get_default_value should return empty list."""
        simulator = PolicySimulator()
        assert simulator._get_default_value() == []


class TestPolicySimulatorEvaluatePolicy:
    """Tests for PolicySimulator.evaluate_policy method."""

    def test_evaluate_policy_no_conditions(self):
        """Policy with no conditions should match."""
        simulator = PolicySimulator()
        policy = {
            "id": "policy-1",
            "name": "Catch-All",
            "conditions": {},
            "action": "allow",
            "priority": 0,
        }

        impact = simulator.evaluate_policy(
            policy,
            model="gpt-4o",
            environment="production",
            max_tokens=1000,
            app_id="test-app",
        )

        assert impact.would_match is True
        assert impact.action == "allow"

    def test_evaluate_policy_model_condition_match(self):
        """Policy should match when model condition matches."""
        simulator = PolicySimulator()
        policy = {
            "id": "policy-1",
            "name": "GPT Policy",
            "conditions": {"models": ["gpt-4o", "gpt-4o-mini"]},
            "action": "allow",
            "priority": 10,
        }

        impact = simulator.evaluate_policy(
            policy,
            model="gpt-4o",
            environment="production",
            max_tokens=1000,
            app_id="test-app",
        )

        assert impact.would_match is True
        assert "model=gpt-4o" in impact.conditions_matched

    def test_evaluate_policy_model_condition_no_match(self):
        """Policy should not match when model condition fails."""
        simulator = PolicySimulator()
        policy = {
            "id": "policy-1",
            "name": "GPT Policy",
            "conditions": {"models": ["gpt-4o-mini"]},
            "action": "deny",
            "priority": 10,
        }

        impact = simulator.evaluate_policy(
            policy,
            model="claude-3-opus",
            environment="production",
            max_tokens=1000,
            app_id="test-app",
        )

        assert impact.would_match is False
        assert len(impact.conditions_failed) > 0

    def test_evaluate_policy_environment_condition_match(self):
        """Policy should match when environment matches."""
        simulator = PolicySimulator()
        policy = {
            "id": "policy-1",
            "name": "Prod Policy",
            "conditions": {"environments": ["production"]},
            "action": "warn",
            "priority": 5,
        }

        impact = simulator.evaluate_policy(
            policy,
            model="gpt-4o",
            environment="production",
            max_tokens=1000,
            app_id="test-app",
        )

        assert impact.would_match is True

    def test_evaluate_policy_environment_condition_no_match(self):
        """Policy should not match when environment doesn't match."""
        simulator = PolicySimulator()
        policy = {
            "id": "policy-1",
            "name": "Prod Only",
            "conditions": {"environments": ["production"]},
            "action": "deny",
            "priority": 10,
        }

        impact = simulator.evaluate_policy(
            policy,
            model="gpt-4o",
            environment="development",
            max_tokens=1000,
            app_id="test-app",
        )

        assert impact.would_match is False

    def test_evaluate_policy_max_tokens_condition(self):
        """Policy should check max_tokens condition."""
        simulator = PolicySimulator()
        policy = {
            "id": "policy-1",
            "name": "Token Limit",
            "conditions": {"max_tokens": 500},
            "action": "deny",
            "priority": 10,
        }

        # Over limit - policy MATCHES (restriction applies)
        impact = simulator.evaluate_policy(
            policy,
            model="gpt-4o",
            environment="production",
            max_tokens=1000,
            app_id="test-app",
        )

        assert impact.would_match is True
        # When over limit, the condition is matched (policy applies)
        assert "max_tokens=1000 > 500" in impact.conditions_matched

        # Under limit - policy does NOT match (restriction doesn't apply)
        impact_under = simulator.evaluate_policy(
            policy,
            model="gpt-4o",
            environment="production",
            max_tokens=200,
            app_id="test-app",
        )

        assert impact_under.would_match is False
        assert len(impact_under.conditions_failed) > 0

    def test_evaluate_policy_multiple_conditions_all_match(self):
        """All conditions must match for policy to match."""
        simulator = PolicySimulator()
        policy = {
            "id": "policy-1",
            "name": "Strict Policy",
            "conditions": {
                "models": ["gpt-4o"],
                "environments": ["production"],
            },
            "action": "allow",
            "priority": 10,
        }

        impact = simulator.evaluate_policy(
            policy,
            model="gpt-4o",
            environment="production",
            max_tokens=1000,
            app_id="test-app",
        )

        assert impact.would_match is True
        assert len(impact.conditions_matched) >= 2

    def test_evaluate_policy_multiple_conditions_one_fails(self):
        """Policy should not match if any condition fails."""
        simulator = PolicySimulator()
        policy = {
            "id": "policy-1",
            "name": "Strict Policy",
            "conditions": {
                "models": ["gpt-4o"],
                "environments": ["production"],
            },
            "action": "deny",
            "priority": 10,
        }

        impact = simulator.evaluate_policy(
            policy,
            model="gpt-4o",
            environment="development",  # Wrong environment
            max_tokens=1000,
            app_id="test-app",
        )

        assert impact.would_match is False


class TestPolicySimulatorAsync:
    """Tests for async methods of PolicySimulator."""

    @pytest.mark.asyncio
    async def test_ensure_loaded(self):
        """ensure_loaded should load policies."""
        simulator = PolicySimulator()

        # Manually set policies (simulating DB load)
        simulator._data = [{"id": "p1", "name": "Policy 1"}]
        simulator._loaded = True

        await simulator.ensure_loaded()

        assert simulator.is_loaded is True
        assert len(simulator.policies) == 1

    @pytest.mark.asyncio
    async def test_invalidate_clears_data(self):
        """invalidate should clear loaded data."""
        simulator = PolicySimulator()
        simulator._data = [{"id": "p1"}]
        simulator._loaded = True

        simulator.invalidate()

        assert simulator.is_loaded is False
        assert simulator.policies == []
