"""Integration tests for Hexagonal Architecture use cases.

These tests verify the integration between:
- Use Cases (EvaluateLLMRequestUseCase, CreateEmbeddingsUseCase)
- Domain Layer (PolicyEvaluator, BudgetChecker)
- Adapters (Mock implementations for testing)

Note: HTTP endpoint tests are in the regular e2e tests.
These tests focus on the hexagonal architecture integration.
"""

import pytest

from backend.domain.policy import PolicyEvaluator
from backend.domain.budget import BudgetChecker
from backend.domain.models import (
    PolicyRule,
    Budget,
    PolicyAction,
    BudgetPeriod,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingData,
)
from backend.application.use_cases.evaluate_llm_request import (
    EvaluateLLMRequestUseCase,
    LLMRequestCommand,
    RequestOutcome,
)
from backend.application.use_cases.create_embeddings import (
    CreateEmbeddingsUseCase,
    EmbeddingCommand,
    EmbeddingOutcome,
)
from backend.ports.llm_provider import LLMProviderPort
from backend.ports.embedding_provider import EmbeddingProviderPort
from backend.ports.policy_repository import PolicyRepositoryPort
from backend.ports.budget_repository import BudgetRepositoryPort
from backend.adapters.audit import InMemoryAuditAdapter
from backend.adapters.prometheus import InMemoryMetricsAdapter


# =============================================================================
# Mock Implementations
# =============================================================================


class MockPolicyRepository(PolicyRepositoryPort):
    """Mock policy repository for testing."""

    def __init__(self, rules: list[PolicyRule] = None):
        self._rules = rules or []

    async def get_active_rules(
        self, org_id: str, app_id: str, environment: str | None = None
    ) -> list[PolicyRule]:
        return [r for r in self._rules if r.enabled]

    async def get_rule_by_id(self, rule_id: str) -> PolicyRule | None:
        return next((r for r in self._rules if r.id == rule_id), None)

    async def create_rule(self, rule: PolicyRule) -> PolicyRule:
        self._rules.append(rule)
        return rule

    async def update_rule(self, rule: PolicyRule) -> PolicyRule:
        return rule

    async def delete_rule(self, rule_id: str) -> bool:
        self._rules = [r for r in self._rules if r.id != rule_id]
        return True


class MockBudgetRepository(BudgetRepositoryPort):
    """Mock budget repository for testing."""

    def __init__(self, budgets: list[Budget] = None):
        self._budgets = budgets or []

    async def get_budgets_for_app(
        self, app_id: str, org_id: str | None = None
    ) -> list[Budget]:
        return [b for b in self._budgets if b.app_id == app_id or not b.app_id]

    async def get_budget_by_id(self, budget_id: str) -> Budget | None:
        return next((b for b in self._budgets if b.id == budget_id), None)

    async def create_budget(self, budget: Budget) -> Budget:
        self._budgets.append(budget)
        return budget

    async def update_budget(self, budget: Budget) -> Budget:
        return budget

    async def delete_budget(self, budget_id: str) -> bool:
        self._budgets = [b for b in self._budgets if b.id != budget_id]
        return True

    async def record_usage(self, budget_id: str, amount_usd: float) -> Budget:
        for b in self._budgets:
            if b.id == budget_id:
                b.spent_usd += amount_usd
                return b
        # Return a dummy budget if not found (shouldn't happen in tests)
        return Budget(id=budget_id, limit_usd=0, spent_usd=amount_usd)


class MockLLMProvider(LLMProviderPort):
    """Mock LLM provider for testing."""

    def __init__(self, response: ChatResponse = None, error: Exception = None):
        self._response = response or ChatResponse(
            id="mock-123",
            model="mock-gpt-4",
            content="Hello! I'm a mock response.",
            finish_reason="stop",
            input_tokens=10,
            output_tokens=8,
        )
        self._error = error

    @property
    def name(self) -> str:
        return "mock"

    def supports_model(self, model: str) -> bool:
        return True

    async def chat(self, request: ChatRequest, api_key: str) -> ChatResponse:
        if self._error:
            raise self._error
        return self._response

    async def chat_stream(self, request: ChatRequest, api_key: str):
        """Streaming mock implementation."""
        if self._error:
            raise self._error
        yield self._response.content


class MockEmbeddingProvider(EmbeddingProviderPort):
    """Mock embedding provider for testing."""

    def __init__(self, response: EmbeddingResponse = None, error: Exception = None):
        self._response = response or EmbeddingResponse(
            model="text-embedding-ada-002",
            data=[EmbeddingData(index=0, embedding=[0.1] * 1536)],
            total_tokens=5,
        )
        self._error = error

    @property
    def name(self) -> str:
        return "mock-embedding"

    def supports_model(self, model: str) -> bool:
        return True

    async def embed(self, request: EmbeddingRequest, api_key: str) -> EmbeddingResponse:
        if self._error:
            raise self._error
        return self._response


# =============================================================================
# Integration Tests: EvaluateLLMRequestUseCase
# =============================================================================


class TestEvaluateLLMRequestIntegration:
    """Integration tests for EvaluateLLMRequestUseCase."""

    @pytest.fixture
    def policy_evaluator(self):
        return PolicyEvaluator()

    @pytest.fixture
    def budget_checker(self):
        return BudgetChecker()

    @pytest.fixture
    def basic_command(self):
        return LLMRequestCommand(
            request_id="test-123",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            environment="development",
            api_key="sk-test-key",
        )

    @pytest.mark.asyncio
    async def test_full_flow_success(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Test successful request through full use case flow."""
        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=100.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=InMemoryAuditAdapter(),
            metrics=InMemoryMetricsAdapter(),
        )

        result = await use_case.execute(basic_command)

        assert result.outcome == RequestOutcome.ALLOWED
        assert result.response is not None
        assert result.response.content == "Hello! I'm a mock response."

    @pytest.mark.asyncio
    async def test_policy_blocks_request(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Test request blocked by policy."""
        blocking_rule = PolicyRule(
            id="block-gpt4",
            name="Block GPT-4",
            action=PolicyAction.DENY,
            priority=100,
            conditions={"model": "gpt-4o"},
            enabled=True,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([blocking_rule]),
            budget_repository=MockBudgetRepository([]),
            llm_provider=MockLLMProvider(),
        )

        result = await use_case.execute(basic_command)

        assert result.outcome == RequestOutcome.DENIED_POLICY
        assert result.response is None

    @pytest.mark.asyncio
    async def test_budget_blocks_request(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Test request blocked by exhausted budget."""
        exhausted_budget = Budget(
            id="exhausted",
            app_id="test-app",
            limit_usd=10.0,
            spent_usd=10.0,
            period=BudgetPeriod.MONTHLY,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository([exhausted_budget]),
            llm_provider=MockLLMProvider(),
        )

        result = await use_case.execute(basic_command)

        assert result.outcome == RequestOutcome.DENIED_BUDGET

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, policy_evaluator, budget_checker):
        """Test dry-run returns simulation without calling LLM."""
        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=100.0, spent_usd=50.0)]
            ),
            llm_provider=MockLLMProvider(),
        )

        command = LLMRequestCommand(
            request_id="dry-run-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            environment="development",
            dry_run=True,
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.DRY_RUN
        assert result.dry_run_result is not None
        assert result.dry_run_result["would_be_allowed"] is True

    @pytest.mark.asyncio
    async def test_metrics_recorded(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Test metrics are recorded during execution."""
        metrics = InMemoryMetricsAdapter()

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=100.0)]
            ),
            llm_provider=MockLLMProvider(),
            metrics=metrics,
        )

        await use_case.execute(basic_command)

        # Check metrics were recorded
        exported = metrics.export()
        assert "requests_count" in exported
        assert "decisions_count" in exported


# =============================================================================
# Integration Tests: CreateEmbeddingsUseCase
# =============================================================================


class TestCreateEmbeddingsIntegration:
    """Integration tests for CreateEmbeddingsUseCase."""

    @pytest.fixture
    def policy_evaluator(self):
        return PolicyEvaluator()

    @pytest.fixture
    def budget_checker(self):
        return BudgetChecker()

    @pytest.fixture
    def basic_command(self):
        return EmbeddingCommand(
            request_id="emb-123",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["Hello world"],
            api_key="sk-test-key",
        )

    @pytest.mark.asyncio
    async def test_full_flow_success(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Test successful embedding through full use case flow."""
        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=100.0)]
            ),
            embedding_provider=MockEmbeddingProvider(),
            metrics=InMemoryMetricsAdapter(),
        )

        result = await use_case.execute(basic_command)

        assert result.outcome == EmbeddingOutcome.SUCCESS
        assert result.response is not None
        assert len(result.response.data) == 1

    @pytest.mark.asyncio
    async def test_policy_blocks_embedding(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Test embedding blocked by policy."""
        blocking_rule = PolicyRule(
            id="block-embeddings",
            name="Block Embeddings",
            action=PolicyAction.DENY,
            priority=100,
            conditions={},
            enabled=True,
        )

        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([blocking_rule]),
            budget_repository=MockBudgetRepository([]),
            embedding_provider=MockEmbeddingProvider(),
        )

        result = await use_case.execute(basic_command)

        assert result.outcome == EmbeddingOutcome.DENIED_POLICY

    @pytest.mark.asyncio
    async def test_budget_blocks_embedding(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Test embedding blocked by exhausted budget."""
        exhausted_budget = Budget(
            id="exhausted",
            app_id="test-app",
            limit_usd=0.001,
            spent_usd=0.001,
            period=BudgetPeriod.MONTHLY,
        )

        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository([exhausted_budget]),
            embedding_provider=MockEmbeddingProvider(),
        )

        result = await use_case.execute(basic_command)

        assert result.outcome == EmbeddingOutcome.DENIED_BUDGET

    @pytest.mark.asyncio
    async def test_multiple_inputs(self, policy_evaluator, budget_checker):
        """Test embedding with multiple inputs."""
        multi_response = EmbeddingResponse(
            model="text-embedding-ada-002",
            data=[
                EmbeddingData(index=0, embedding=[0.1] * 1536),
                EmbeddingData(index=1, embedding=[0.2] * 1536),
                EmbeddingData(index=2, embedding=[0.3] * 1536),
            ],
            total_tokens=15,
        )

        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=100.0)]
            ),
            embedding_provider=MockEmbeddingProvider(response=multi_response),
        )

        command = EmbeddingCommand(
            request_id="multi-123",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["Hello", "World", "Test"],
            api_key="sk-test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == EmbeddingOutcome.SUCCESS
        assert len(result.response.data) == 3

    @pytest.mark.asyncio
    async def test_metrics_recorded(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Test metrics are recorded for embeddings."""
        metrics = InMemoryMetricsAdapter()

        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=100.0)]
            ),
            embedding_provider=MockEmbeddingProvider(),
            metrics=metrics,
        )

        await use_case.execute(basic_command)

        exported = metrics.export()
        assert "requests_count" in exported


# =============================================================================
# HTTP Endpoint Tests (using test client)
# =============================================================================


class TestChatEndpoint:
    """Tests for /v1/chat/completions endpoint."""

    @pytest.mark.asyncio
    async def test_chat_requires_authentication(self, client):
        """Verify endpoint requires authentication."""
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403]


class TestEmbeddingsEndpoint:
    """Tests for /v1/embeddings endpoint."""

    @pytest.mark.asyncio
    async def test_embeddings_requires_authentication(self, client):
        """Verify endpoint requires authentication."""
        response = await client.post(
            "/v1/embeddings",
            json={
                "model": "text-embedding-ada-002",
                "input": "Hello world",
            },
        )
        assert response.status_code in [401, 403]
