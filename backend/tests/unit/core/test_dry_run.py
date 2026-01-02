"""Unit tests for Dry Run / Policy Simulation module."""

from backend.core.dry_run import (
    DryRunMode,
    PolicyImpact,
    DryRunResult,
    PolicySimulator,
)
from backend.core.decisions import DecisionChain


class TestDryRunMode:
    """Tests for DryRunMode enum."""

    def test_valid_modes(self):
        """Test all valid modes."""
        assert DryRunMode.FULL == "full"
        assert DryRunMode.POLICIES_ONLY == "policies_only"
        assert DryRunMode.BUDGET_ONLY == "budget_only"
        assert DryRunMode.SECURITY_ONLY == "security_only"


class TestPolicyImpact:
    """Tests for PolicyImpact model."""

    def test_create_minimal(self):
        """Test creating PolicyImpact with minimal fields."""
        impact = PolicyImpact(
            policy_id="policy-1",
            policy_name="Test Policy",
            would_match=True,
            action="deny",
            reason="Token limit exceeded",
            priority=1,
        )

        assert impact.policy_id == "policy-1"
        assert impact.would_match is True
        assert impact.action == "deny"
        assert impact.conditions_matched == []
        assert impact.conditions_failed == []

    def test_create_full(self):
        """Test creating PolicyImpact with all fields."""
        impact = PolicyImpact(
            policy_id="policy-1",
            policy_name="Test Policy",
            would_match=True,
            action="deny",
            reason="Token limit exceeded",
            priority=10,
            conditions_matched=["model == gpt-4", "environment == production"],
            conditions_failed=["budget < 100"],
        )

        assert len(impact.conditions_matched) == 2
        assert len(impact.conditions_failed) == 1


class TestDryRunResult:
    """Tests for DryRunResult model."""

    def test_create_minimal(self):
        """Test creating DryRunResult with minimal fields."""
        chain = DecisionChain(request_id="test-123")

        result = DryRunResult(
            request_id="test-123",
            app_id="test-app",
            model="gpt-4",
            environment="development",
            mode=DryRunMode.FULL,
            would_be_allowed=True,
            decision_chain=chain,
        )

        assert result.request_id == "test-123"
        assert result.would_be_allowed is True
        assert result.blocking_reason is None
        assert result.policies_evaluated == []

    def test_create_blocked(self):
        """Test creating blocked DryRunResult."""
        chain = DecisionChain(request_id="test-123")

        result = DryRunResult(
            request_id="test-123",
            app_id="test-app",
            model="gpt-4",
            environment="production",
            mode=DryRunMode.POLICIES_ONLY,
            would_be_allowed=False,
            blocking_reason="Token limit exceeded",
            decision_chain=chain,
            policies_that_would_block=[
                PolicyImpact(
                    policy_id="p-1",
                    policy_name="Token Limit",
                    would_match=True,
                    action="deny",
                    reason="Max tokens exceeded",
                    priority=1,
                )
            ],
        )

        assert result.would_be_allowed is False
        assert len(result.policies_that_would_block) == 1

    def test_to_summary(self):
        """Test to_summary method."""
        chain = DecisionChain(request_id="test-123")

        result = DryRunResult(
            request_id="test-123",
            app_id="test-app",
            model="gpt-4",
            environment="development",
            mode=DryRunMode.FULL,
            would_be_allowed=True,
            decision_chain=chain,
            policies_evaluated=[
                PolicyImpact(
                    policy_id="p-1",
                    policy_name="P1",
                    would_match=False,
                    action="allow",
                    reason="",
                    priority=1,
                ),
                PolicyImpact(
                    policy_id="p-2",
                    policy_name="P2",
                    would_match=True,
                    action="warn",
                    reason="",
                    priority=2,
                ),
            ],
            policies_that_would_warn=[
                PolicyImpact(
                    policy_id="p-2",
                    policy_name="P2",
                    would_match=True,
                    action="warn",
                    reason="",
                    priority=2,
                ),
            ],
            recommendations=["Consider increasing token limit"],
        )

        summary = result.to_summary()

        assert summary["would_be_allowed"] is True
        assert summary["policies_evaluated"] == 2
        assert summary["policies_blocking"] == 0
        assert summary["policies_warning"] == 1
        assert len(summary["recommendations"]) == 1


class TestDryRunResultWithBudget:
    """Tests for DryRunResult with budget info."""

    def test_with_budget_impact(self):
        """Test DryRunResult with budget impact."""
        chain = DecisionChain(request_id="test-123")

        result = DryRunResult(
            request_id="test-123",
            app_id="test-app",
            model="gpt-4",
            environment="development",
            mode=DryRunMode.BUDGET_ONLY,
            would_be_allowed=True,
            decision_chain=chain,
            budget_impact={
                "current_spend": 50.0,
                "limit": 100.0,
                "estimated_cost": 0.05,
                "would_exceed": False,
            },
        )

        assert result.budget_impact is not None
        assert result.budget_impact["current_spend"] == 50.0

    def test_with_security_findings(self):
        """Test DryRunResult with security findings."""
        chain = DecisionChain(request_id="test-123")

        result = DryRunResult(
            request_id="test-123",
            app_id="test-app",
            model="gpt-4",
            environment="development",
            mode=DryRunMode.SECURITY_ONLY,
            would_be_allowed=True,
            decision_chain=chain,
            security_findings=[
                {"type": "pii_detected", "confidence": 0.85},
                {"type": "prompt_injection", "confidence": 0.3},
            ],
        )

        assert len(result.security_findings) == 2


class TestPolicySimulator:
    """Tests for PolicySimulator."""

    def test_init(self):
        """Test PolicySimulator initialization."""
        simulator = PolicySimulator()

        assert simulator is not None

    def test_inherits_from_async_loadable(self):
        """Test that PolicySimulator inherits from AsyncLoadableEntity."""

        simulator = PolicySimulator()

        # Should have inherited methods
        assert hasattr(simulator, "_data")
        assert hasattr(simulator, "_loaded")
