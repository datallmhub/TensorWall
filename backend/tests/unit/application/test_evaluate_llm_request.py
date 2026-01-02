"""Tests unitaires hexagonaux pour EvaluateLLMRequestUseCase.

Ces tests démontrent l'architecture hexagonale en:
- Utilisant des mocks pour tous les ports (dépendances)
- Testant uniquement la logique d'orchestration du use case
- Ne dépendant d'aucune infrastructure (DB, réseau, etc.)
"""

import pytest
from unittest.mock import AsyncMock

from backend.application.use_cases.evaluate_llm_request import (
    EvaluateLLMRequestUseCase,
    LLMRequestCommand,
    RequestOutcome,
)
from backend.domain.policy import PolicyEvaluator
from backend.domain.budget import BudgetChecker
from backend.domain.models import (
    PolicyRule,
    PolicyAction,
    Budget,
    BudgetPeriod,
    ChatResponse,
)
from backend.ports.llm_provider import LLMProviderPort
from backend.ports.policy_repository import PolicyRepositoryPort
from backend.ports.budget_repository import BudgetRepositoryPort
from backend.adapters.audit import InMemoryAuditAdapter


# =============================================================================
# Mock Implementations
# =============================================================================


class MockPolicyRepository(PolicyRepositoryPort):
    """Mock du repository de policies."""

    def __init__(self, rules: list[PolicyRule] | None = None):
        self._rules = rules or []

    async def get_active_rules(
        self,
        org_id: str | None = None,
        app_id: str | None = None,
        environment: str | None = None,
    ) -> list[PolicyRule]:
        return self._rules

    async def get_rule_by_id(self, rule_id: str) -> PolicyRule | None:
        return next((r for r in self._rules if r.id == rule_id), None)

    async def create_rule(self, rule: PolicyRule) -> PolicyRule:
        self._rules.append(rule)
        return rule

    async def update_rule(self, rule: PolicyRule) -> PolicyRule:
        return rule

    async def delete_rule(self, rule_id: str) -> bool:
        return True


class MockBudgetRepository(BudgetRepositoryPort):
    """Mock du repository de budgets."""

    def __init__(self, budgets: list[Budget] | None = None):
        self._budgets = budgets or []

    async def get_budgets_for_app(
        self,
        app_id: str,
        org_id: str | None = None,
    ) -> list[Budget]:
        return [b for b in self._budgets if b.app_id == app_id]

    async def get_budget_by_id(self, budget_id: str) -> Budget | None:
        return next((b for b in self._budgets if b.id == budget_id), None)

    async def create_budget(self, budget: Budget) -> Budget:
        self._budgets.append(budget)
        return budget

    async def update_budget(self, budget: Budget) -> Budget:
        return budget

    async def record_usage(self, budget_id: str, amount_usd: float) -> Budget:
        budget = await self.get_budget_by_id(budget_id)
        if budget:
            budget.spent_usd += amount_usd
        return budget

    async def delete_budget(self, budget_id: str) -> bool:
        return True


class MockLLMProvider(LLMProviderPort):
    """Mock du provider LLM."""

    def __init__(
        self, response: ChatResponse | None = None, error: Exception | None = None
    ):
        self._response = response or ChatResponse(
            id="mock-response-id",
            model="mock-model",
            content="This is a mock response",
            input_tokens=10,
            output_tokens=5,
            finish_reason="stop",
        )
        self._error = error

    @property
    def name(self) -> str:
        return "mock"

    def supports_model(self, model: str) -> bool:
        return True

    async def chat(self, request, api_key: str) -> ChatResponse:
        if self._error:
            raise self._error
        return self._response

    async def chat_stream(self, request, api_key: str):
        yield '{"choices": [{"delta": {"content": "mock"}}]}'


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def policy_evaluator():
    """Policy evaluator du domain."""
    return PolicyEvaluator()


@pytest.fixture
def budget_checker():
    """Budget checker du domain."""
    return BudgetChecker()


@pytest.fixture
def mock_policy_repository():
    """Repository sans règles."""
    return MockPolicyRepository([])


@pytest.fixture
def mock_budget_repository():
    """Repository avec un budget généreux."""
    return MockBudgetRepository(
        [
            Budget(
                id="budget-1",
                app_id="test-app",
                limit_usd=1000.0,
                spent_usd=0.0,
                period=BudgetPeriod.MONTHLY,
            )
        ]
    )


@pytest.fixture
def mock_llm_provider():
    """Provider LLM mock."""
    return MockLLMProvider()


@pytest.fixture
def audit_adapter():
    """Audit adapter en mémoire."""
    return InMemoryAuditAdapter()


@pytest.fixture
def use_case(
    policy_evaluator,
    budget_checker,
    mock_policy_repository,
    mock_budget_repository,
    mock_llm_provider,
    audit_adapter,
):
    """Use case assemblé avec toutes les dépendances."""
    return EvaluateLLMRequestUseCase(
        policy_evaluator=policy_evaluator,
        budget_checker=budget_checker,
        policy_repository=mock_policy_repository,
        budget_repository=mock_budget_repository,
        llm_provider=mock_llm_provider,
        audit_log=audit_adapter,
    )


@pytest.fixture
def basic_command():
    """Commande de base pour les tests."""
    return LLMRequestCommand(
        request_id="test-request-123",
        app_id="test-app",
        org_id="test-org",
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
        environment="development",
        api_key="test-api-key",
    )


# =============================================================================
# Tests: Flow Principal
# =============================================================================


class TestEvaluateLLMRequestUseCase:
    """Tests du use case d'évaluation des requêtes LLM."""

    @pytest.mark.asyncio
    async def test_allowed_request(self, use_case, basic_command):
        """Vérifie qu'une requête valide est autorisée."""
        result = await use_case.execute(basic_command)

        assert result.outcome == RequestOutcome.ALLOWED
        assert result.response is not None
        assert result.response.content == "This is a mock response"
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_policy_blocks_request(
        self, policy_evaluator, budget_checker, basic_command, audit_adapter
    ):
        """Vérifie qu'une policy DENY bloque la requête."""
        blocking_rule = PolicyRule(
            id="block-gpt4",
            name="Block GPT-4",
            action=PolicyAction.DENY,
            priority=100,
            conditions={"model": "gpt-4"},
            enabled=True,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([blocking_rule]),
            budget_repository=MockBudgetRepository([]),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        result = await use_case.execute(basic_command)

        assert result.outcome == RequestOutcome.DENIED_POLICY
        assert result.response is None
        assert result.error_message is not None
        assert (
            "policy" in result.error_message.lower()
            or "Block GPT-4" in result.error_message
        )

    @pytest.mark.asyncio
    async def test_policy_warn_allows_request(
        self, policy_evaluator, budget_checker, basic_command, audit_adapter
    ):
        """Vérifie qu'une policy WARN permet la requête avec un warning."""
        warn_rule = PolicyRule(
            id="warn-gpt4",
            name="Warn on GPT-4",
            action=PolicyAction.WARN,
            priority=100,
            conditions={"model": "gpt-4"},
            enabled=True,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([warn_rule]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        result = await use_case.execute(basic_command)

        # WARN should allow the request
        assert result.outcome == RequestOutcome.ALLOWED
        assert result.response is not None

    @pytest.mark.asyncio
    async def test_budget_exceeded_blocks_request(
        self, policy_evaluator, budget_checker, basic_command, audit_adapter
    ):
        """Vérifie qu'un budget épuisé bloque la requête."""
        exhausted_budget = Budget(
            id="budget-exhausted",
            app_id="test-app",
            limit_usd=10.0,
            spent_usd=10.0,  # 100% utilisé
            period=BudgetPeriod.MONTHLY,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository([exhausted_budget]),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        result = await use_case.execute(basic_command)

        assert result.outcome == RequestOutcome.DENIED_BUDGET
        assert result.response is None
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_dry_run_does_not_call_llm(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que dry_run retourne sans appeler le LLM."""
        llm_mock = MockLLMProvider(error=Exception("Should not be called"))

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=llm_mock,
            audit_log=audit_adapter,
        )

        command = LLMRequestCommand(
            request_id="dry-run-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            dry_run=True,
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.DRY_RUN
        assert result.dry_run_result is not None
        assert result.dry_run_result["would_be_allowed"] is True
        assert "estimated_cost_usd" in result.dry_run_result

    @pytest.mark.asyncio
    async def test_missing_api_key_still_works(self, use_case):
        """Vérifie qu'une requête sans API key fonctionne (mode permissif avec mocks)."""
        command = LLMRequestCommand(
            request_id="no-key-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key=None,
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ALLOWED

    @pytest.mark.asyncio
    async def test_llm_error_returns_error_outcome(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie qu'une erreur LLM retourne ERROR."""
        llm_mock = MockLLMProvider(error=Exception("LLM service unavailable"))

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=llm_mock,
            audit_log=audit_adapter,
        )

        command = LLMRequestCommand(
            request_id="error-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ERROR
        assert "LLM service unavailable" in result.error_message


# =============================================================================
# Tests: Audit Logging
# =============================================================================


class TestAuditLogging:
    """Tests de l'enregistrement des audits."""

    @pytest.mark.asyncio
    async def test_allowed_request_is_logged(
        self, use_case, basic_command, audit_adapter
    ):
        """Vérifie qu'une requête autorisée est loguée."""
        await use_case.execute(basic_command)

        assert len(audit_adapter.entries) >= 1
        entry = audit_adapter.entries[0]
        assert entry.request_id == "test-request-123"
        assert entry.app_id == "test-app"
        assert entry.outcome == "allowed"

    @pytest.mark.asyncio
    async def test_denied_request_is_logged(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Vérifie qu'une requête refusée est loguée."""
        audit_adapter = InMemoryAuditAdapter()

        blocking_rule = PolicyRule(
            id="block-all",
            name="Block All",
            action=PolicyAction.DENY,
            priority=100,
            conditions={},
            enabled=True,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([blocking_rule]),
            budget_repository=MockBudgetRepository([]),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        await use_case.execute(basic_command)

        assert len(audit_adapter.entries) >= 1
        entry = audit_adapter.entries[0]
        assert entry.outcome == "denied_policy"


# =============================================================================
# Tests: Policy Evaluation
# =============================================================================


class TestPolicyEvaluation:
    """Tests de l'évaluation des policies."""

    @pytest.mark.asyncio
    async def test_policy_with_model_condition(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie qu'une condition sur le modèle fonctionne."""
        allow_gpt35 = PolicyRule(
            id="allow-gpt35",
            name="Allow GPT-3.5 only",
            action=PolicyAction.ALLOW,
            priority=100,
            conditions={"model": "gpt-3.5-turbo"},
            enabled=True,
        )

        deny_all = PolicyRule(
            id="deny-all",
            name="Deny all others",
            action=PolicyAction.DENY,
            priority=50,
            conditions={},
            enabled=True,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([allow_gpt35, deny_all]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        command_gpt4 = LLMRequestCommand(
            request_id="test-gpt4",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command_gpt4)
        assert result.outcome == RequestOutcome.DENIED_POLICY

    @pytest.mark.asyncio
    async def test_policy_with_models_list_condition(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie qu'une condition avec liste de modèles fonctionne."""
        deny_phi2 = PolicyRule(
            id="deny-phi2",
            name="Deny phi-2",
            action=PolicyAction.DENY,
            priority=100,
            conditions={"models": ["lmstudio/phi-2"]},
            enabled=True,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([deny_phi2]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        # phi-2 should be blocked
        command_phi2 = LLMRequestCommand(
            request_id="test-phi2",
            app_id="test-app",
            org_id="test-org",
            model="lmstudio/phi-2",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command_phi2)
        assert result.outcome == RequestOutcome.DENIED_POLICY

        # Other models should pass
        command_qwen = LLMRequestCommand(
            request_id="test-qwen",
            app_id="test-app",
            org_id="test-org",
            model="lmstudio/qwen/qwen2.5-vl-7b",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result_qwen = await use_case.execute(command_qwen)
        assert result_qwen.outcome == RequestOutcome.ALLOWED

    @pytest.mark.asyncio
    async def test_policy_priority_order(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que les policies sont évaluées par priorité."""
        high_priority_gpt4 = PolicyRule(
            id="high-allow-gpt4",
            name="High Priority Allow GPT-4",
            action=PolicyAction.ALLOW,
            priority=100,
            conditions={"model": "gpt-4"},
            enabled=True,
        )

        low_priority_gpt35 = PolicyRule(
            id="low-deny-gpt35",
            name="Low Priority Deny GPT-3.5",
            action=PolicyAction.DENY,
            priority=10,
            conditions={"model": "gpt-3.5-turbo"},
            enabled=True,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository(
                [low_priority_gpt35, high_priority_gpt4]
            ),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        command_gpt4 = LLMRequestCommand(
            request_id="test-priority-gpt4",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command_gpt4)
        assert result.outcome == RequestOutcome.ALLOWED

        command_gpt35 = LLMRequestCommand(
            request_id="test-priority-gpt35",
            app_id="test-app",
            org_id="test-org",
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result_gpt35 = await use_case.execute(command_gpt35)
        assert result_gpt35.outcome == RequestOutcome.DENIED_POLICY


# =============================================================================
# Tests: Budget Checking
# =============================================================================


class TestBudgetChecking:
    """Tests de la vérification des budgets."""

    @pytest.mark.asyncio
    async def test_budget_warning_threshold(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que le budget proche de la limite génère un warning."""
        almost_exhausted = Budget(
            id="budget-warning",
            app_id="test-app",
            limit_usd=100.0,
            spent_usd=90.0,
            period=BudgetPeriod.MONTHLY,
        )

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository([almost_exhausted]),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        command = LLMRequestCommand(
            request_id="test-warning",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ALLOWED
        assert result.budget_status is not None
        assert result.budget_status.usage_percent >= 90

    @pytest.mark.asyncio
    async def test_no_budget_allows_request(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie qu'une app sans budget est autorisée."""
        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository([]),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
        )

        command = LLMRequestCommand(
            request_id="test-no-budget",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ALLOWED


# =============================================================================
# Tests: Result Metadata
# =============================================================================


class TestResultMetadata:
    """Tests des métadonnées du résultat."""

    @pytest.mark.asyncio
    async def test_result_contains_token_counts(self, use_case, basic_command):
        """Vérifie que le résultat contient les compteurs de tokens."""
        result = await use_case.execute(basic_command)

        assert result.outcome == RequestOutcome.ALLOWED
        assert result.metadata.get("input_tokens") == 10
        assert result.metadata.get("output_tokens") == 5

    @pytest.mark.asyncio
    async def test_result_contains_model_info(self, use_case, basic_command):
        """Vérifie que le résultat contient les infos du modèle."""
        result = await use_case.execute(basic_command)

        assert result.metadata.get("model") == "mock-model"


# =============================================================================
# Tests: Request Tracing
# =============================================================================


class TestRequestTracing:
    """Tests du traçage des requêtes."""

    @pytest.mark.asyncio
    async def test_tracing_creates_trace_on_request(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie qu'une trace est créée pour chaque requête."""
        from backend.adapters.tracing import InMemoryRequestTracingAdapter

        tracer = InMemoryRequestTracingAdapter()

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
            request_tracer=tracer,
        )

        command = LLMRequestCommand(
            request_id="trace-test-123",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ALLOWED

        trace = await tracer.get_trace_by_request_id("trace-test-123")
        assert trace is not None
        assert trace.app_id == "test-app"
        assert trace.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_tracing_records_spans(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que les spans sont enregistrés pour chaque étape."""
        from backend.adapters.tracing import InMemoryRequestTracingAdapter
        from backend.ports.request_tracing import TraceStatus

        tracer = InMemoryRequestTracingAdapter()

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
            request_tracer=tracer,
        )

        command = LLMRequestCommand(
            request_id="span-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        await use_case.execute(command)

        trace = await tracer.get_trace_by_request_id("span-test")
        assert trace is not None
        assert trace.status == TraceStatus.COMPLETED
        assert len(trace.spans) >= 2

    @pytest.mark.asyncio
    async def test_tracing_fails_trace_on_error(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que la trace est marquée comme échouée en cas d'erreur."""
        from backend.adapters.tracing import InMemoryRequestTracingAdapter
        from backend.ports.request_tracing import TraceStatus

        tracer = InMemoryRequestTracingAdapter()

        failing_provider = MockLLMProvider()
        failing_provider.chat = AsyncMock(side_effect=Exception("LLM Error"))

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=failing_provider,
            audit_log=audit_adapter,
            request_tracer=tracer,
        )

        command = LLMRequestCommand(
            request_id="error-trace-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ERROR

        trace = await tracer.get_trace_by_request_id("error-trace-test")
        assert trace is not None
        assert trace.status == TraceStatus.FAILED


# =============================================================================
# Tests: Encryption
# =============================================================================


class TestEncryption:
    """Tests du déchiffrement des API keys."""

    @pytest.mark.asyncio
    async def test_encryption_decrypts_encrypted_api_key(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que les API keys chiffrées sont déchiffrées avant l'appel LLM."""
        from backend.adapters.encryption import InMemoryEncryptionAdapter

        encryption = InMemoryEncryptionAdapter()

        encrypted = await encryption.encrypt_api_key("real-api-key-123")

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
            encryption=encryption,
        )

        command = LLMRequestCommand(
            request_id="decrypt-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key=f"enc:{encrypted}",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ALLOWED

    @pytest.mark.asyncio
    async def test_encryption_passes_plain_api_key(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que les API keys non chiffrées passent directement."""
        from backend.adapters.encryption import InMemoryEncryptionAdapter

        encryption = InMemoryEncryptionAdapter()

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
            encryption=encryption,
        )

        command = LLMRequestCommand(
            request_id="plain-key-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="plain-api-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ALLOWED

    @pytest.mark.asyncio
    async def test_encryption_fails_on_invalid_encrypted_key(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que le déchiffrement échoue pour une clé invalide."""
        from backend.adapters.encryption import InMemoryEncryptionAdapter

        encryption = InMemoryEncryptionAdapter()

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
            encryption=encryption,
        )

        command = LLMRequestCommand(
            request_id="invalid-encrypt-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="enc:invalid-encrypted-data",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ERROR
        assert "decrypt" in result.error_message.lower()


# =============================================================================
# Tests: Observability
# =============================================================================


class TestObservability:
    """Tests de l'observabilité."""

    @pytest.mark.asyncio
    async def test_observability_records_successful_request(
        self, policy_evaluator, budget_checker, audit_adapter
    ):
        """Vérifie que les métriques d'observabilité sont enregistrées pour une requête réussie."""
        from backend.adapters.observability import InMemoryObservabilityAdapter
        from backend.ports.observability import CostFilters

        observability = InMemoryObservabilityAdapter()

        use_case = EvaluateLLMRequestUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            llm_provider=MockLLMProvider(),
            audit_log=audit_adapter,
            observability=observability,
        )

        command = LLMRequestCommand(
            request_id="observability-test",
            app_id="test-app",
            org_id="test-org",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == RequestOutcome.ALLOWED

        filters = CostFilters(app_id="test-app")
        breakdown = await observability.get_cost_breakdown(filters)

        assert breakdown.total_cost_usd > 0
        assert "test-app" in breakdown.by_app
