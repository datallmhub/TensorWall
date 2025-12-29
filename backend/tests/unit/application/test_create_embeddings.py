"""Tests unitaires hexagonaux pour CreateEmbeddingsUseCase.

Ces tests démontrent l'architecture hexagonale en:
- Utilisant des mocks pour tous les ports (dépendances)
- Testant uniquement la logique d'orchestration du use case
- Ne dépendant d'aucune infrastructure (DB, réseau, etc.)
"""

import pytest

from backend.application.use_cases.create_embeddings import (
    CreateEmbeddingsUseCase,
    EmbeddingCommand,
    EmbeddingOutcome,
)
from backend.domain.policy import PolicyEvaluator
from backend.domain.budget import BudgetChecker
from backend.domain.models import (
    PolicyRule,
    PolicyAction,
    Budget,
    BudgetPeriod,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingData,
)
from backend.ports.embedding_provider import EmbeddingProviderPort
from backend.ports.policy_repository import PolicyRepositoryPort
from backend.ports.budget_repository import BudgetRepositoryPort
from backend.ports.metrics import MetricsPort, RequestMetrics, DecisionMetrics


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


class MockEmbeddingProvider(EmbeddingProviderPort):
    """Mock du provider d'embeddings."""

    def __init__(
        self,
        response: EmbeddingResponse | None = None,
        error: Exception | None = None,
    ):
        self._response = response or EmbeddingResponse(
            model="text-embedding-ada-002",
            data=[
                EmbeddingData(index=0, embedding=[0.1, 0.2, 0.3] * 512),
            ],
            total_tokens=10,
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
        # Ajuster le nombre d'embeddings selon les inputs
        if len(request.input) > 1:
            self._response = EmbeddingResponse(
                model=request.model,
                data=[
                    EmbeddingData(index=i, embedding=[0.1] * 1536)
                    for i in range(len(request.input))
                ],
                total_tokens=len(request.input) * 10,
            )
        return self._response


class MockMetrics(MetricsPort):
    """Mock du port de métriques."""

    def __init__(self):
        self.request_metrics: list[RequestMetrics] = []
        self.decision_metrics: list[DecisionMetrics] = []
        self.requests_started: list[str] = []
        self.requests_finished: list[str] = []
        self.errors: list[tuple[str, str]] = []
        self.security_blocks: list[tuple[str, str]] = []
        self.budget_updates: list = []

    def record_request(self, metrics: RequestMetrics) -> None:
        self.request_metrics.append(metrics)

    def record_decision(self, metrics: DecisionMetrics) -> None:
        self.decision_metrics.append(metrics)

    def request_started(self, app_id: str) -> None:
        self.requests_started.append(app_id)

    def request_finished(self, app_id: str) -> None:
        self.requests_finished.append(app_id)

    def record_error(self, app_id: str, error_type: str) -> None:
        self.errors.append((app_id, error_type))

    def record_security_block(self, app_id: str, reason: str) -> None:
        self.security_blocks.append((app_id, reason))

    def update_budget(self, metrics) -> None:
        self.budget_updates.append(metrics)

    def export(self) -> str:
        return ""


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
def mock_embedding_provider():
    """Provider d'embeddings mock."""
    return MockEmbeddingProvider()


@pytest.fixture
def use_case(
    policy_evaluator,
    budget_checker,
    mock_policy_repository,
    mock_budget_repository,
    mock_embedding_provider,
):
    """Use case assemblé avec toutes les dépendances."""
    return CreateEmbeddingsUseCase(
        policy_evaluator=policy_evaluator,
        budget_checker=budget_checker,
        policy_repository=mock_policy_repository,
        budget_repository=mock_budget_repository,
        embedding_provider=mock_embedding_provider,
    )


@pytest.fixture
def basic_command():
    """Commande de base pour les tests."""
    return EmbeddingCommand(
        request_id="embed-test-123",
        app_id="test-app",
        org_id="test-org",
        model="text-embedding-ada-002",
        inputs=["Hello world"],
        api_key="test-api-key",
    )


# =============================================================================
# Tests: Flow Principal
# =============================================================================


class TestCreateEmbeddingsUseCase:
    """Tests du use case de création d'embeddings."""

    @pytest.mark.asyncio
    async def test_successful_embedding(self, use_case, basic_command):
        """Vérifie qu'une requête valide génère des embeddings."""
        result = await use_case.execute(basic_command)

        assert result.outcome == EmbeddingOutcome.SUCCESS
        assert result.response is not None
        assert len(result.response.data) >= 1
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_multiple_inputs(self, use_case):
        """Vérifie le traitement de plusieurs inputs."""
        command = EmbeddingCommand(
            request_id="multi-embed-test",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["First text", "Second text", "Third text"],
            api_key="test-api-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == EmbeddingOutcome.SUCCESS
        assert len(result.response.data) == 3
        assert result.metadata.get("num_embeddings") == 3

    @pytest.mark.asyncio
    async def test_policy_blocks_request(self, policy_evaluator, budget_checker, basic_command):
        """Vérifie qu'une policy DENY bloque la requête."""
        blocking_rule = PolicyRule(
            id="block-embeddings",
            name="Block Embeddings",
            action=PolicyAction.DENY,
            priority=100,
            conditions={"feature": "embeddings"},
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
        assert result.response is None
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_budget_exceeded_blocks_request(
        self, policy_evaluator, budget_checker, basic_command
    ):
        """Vérifie qu'un budget épuisé bloque la requête."""
        exhausted_budget = Budget(
            id="budget-exhausted",
            app_id="test-app",
            limit_usd=0.001,  # Très petit budget
            spent_usd=0.001,  # Déjà épuisé
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
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_error(self, use_case):
        """Vérifie qu'une requête sans API key retourne une erreur."""
        command = EmbeddingCommand(
            request_id="no-key-test",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["Hello"],
            api_key=None,  # Pas de clé API
        )

        result = await use_case.execute(command)

        assert result.outcome == EmbeddingOutcome.ERROR
        assert "API key" in result.error_message

    @pytest.mark.asyncio
    async def test_provider_error_returns_error_outcome(self, policy_evaluator, budget_checker):
        """Vérifie qu'une erreur du provider retourne ERROR."""
        error_provider = MockEmbeddingProvider(error=Exception("Embedding service unavailable"))

        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            embedding_provider=error_provider,
        )

        command = EmbeddingCommand(
            request_id="error-test",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["Hello"],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == EmbeddingOutcome.ERROR
        assert "Embedding service unavailable" in result.error_message


# =============================================================================
# Tests: Cost Calculation
# =============================================================================


class TestCostCalculation:
    """Tests du calcul des coûts."""

    @pytest.mark.asyncio
    async def test_cost_is_calculated(self, use_case, basic_command):
        """Vérifie que le coût est calculé."""
        result = await use_case.execute(basic_command)

        assert result.outcome == EmbeddingOutcome.SUCCESS
        assert result.cost_usd > 0
        # Coût basé sur les tokens (10 tokens * 0.0001 / 1000)
        assert result.cost_usd == pytest.approx(0.000001, rel=0.1)

    @pytest.mark.asyncio
    async def test_cost_scales_with_tokens(self, policy_evaluator, budget_checker):
        """Vérifie que le coût augmente avec les tokens."""
        # Provider avec plus de tokens
        large_response = EmbeddingResponse(
            model="text-embedding-ada-002",
            data=[EmbeddingData(index=0, embedding=[0.1] * 1536)],
            total_tokens=1000,
        )
        provider = MockEmbeddingProvider(response=large_response)

        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            embedding_provider=provider,
        )

        command = EmbeddingCommand(
            request_id="cost-test",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["A long text that uses more tokens"],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        # 1000 tokens * 0.0001 / 1000 = 0.0001
        assert result.cost_usd == pytest.approx(0.0001, rel=0.01)


# =============================================================================
# Tests: Result Metadata
# =============================================================================


class TestResultMetadata:
    """Tests des métadonnées du résultat."""

    @pytest.mark.asyncio
    async def test_result_contains_token_count(self, use_case, basic_command):
        """Vérifie que le résultat contient le nombre de tokens."""
        result = await use_case.execute(basic_command)

        assert result.outcome == EmbeddingOutcome.SUCCESS
        assert result.metadata.get("total_tokens") == 10

    @pytest.mark.asyncio
    async def test_result_contains_model_info(self, use_case, basic_command):
        """Vérifie que le résultat contient les infos du modèle."""
        result = await use_case.execute(basic_command)

        assert result.metadata.get("model") == "text-embedding-ada-002"

    @pytest.mark.asyncio
    async def test_result_contains_embedding_count(self, use_case):
        """Vérifie que le résultat contient le nombre d'embeddings."""
        command = EmbeddingCommand(
            request_id="multi-embed",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["One", "Two"],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.metadata.get("num_embeddings") == 2


# =============================================================================
# Tests: Policy & Budget Status
# =============================================================================


class TestPolicyAndBudgetStatus:
    """Tests des statuts de policy et budget."""

    @pytest.mark.asyncio
    async def test_policy_decision_in_result(self, use_case, basic_command):
        """Vérifie que la décision de policy est dans le résultat."""
        result = await use_case.execute(basic_command)

        assert result.policy_decision is not None
        assert result.policy_decision.action == PolicyAction.ALLOW

    @pytest.mark.asyncio
    async def test_budget_status_in_result(self, use_case, basic_command):
        """Vérifie que le statut budget est dans le résultat."""
        result = await use_case.execute(basic_command)

        assert result.budget_status is not None
        assert result.budget_status.allowed is True
        assert result.budget_status.usage_percent >= 0

    @pytest.mark.asyncio
    async def test_no_budget_allows_request(self, policy_evaluator, budget_checker):
        """Vérifie qu'une app sans budget est autorisée."""
        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository([]),  # Pas de budget
            embedding_provider=MockEmbeddingProvider(),
        )

        command = EmbeddingCommand(
            request_id="no-budget-test",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["Hello"],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == EmbeddingOutcome.SUCCESS


# =============================================================================
# Tests: Metrics Integration
# =============================================================================


class TestMetricsIntegration:
    """Tests de l'intégration des métriques."""

    @pytest.fixture
    def mock_metrics(self):
        """Mock du port de métriques."""
        return MockMetrics()

    @pytest.fixture
    def use_case_with_metrics(
        self,
        policy_evaluator,
        budget_checker,
        mock_policy_repository,
        mock_budget_repository,
        mock_embedding_provider,
        mock_metrics,
    ):
        """Use case avec métriques."""
        return CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=mock_policy_repository,
            budget_repository=mock_budget_repository,
            embedding_provider=mock_embedding_provider,
            metrics=mock_metrics,
        )

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(
        self, use_case_with_metrics, mock_metrics, basic_command
    ):
        """Vérifie que les métriques sont enregistrées en cas de succès."""
        result = await use_case_with_metrics.execute(basic_command)

        assert result.outcome == EmbeddingOutcome.SUCCESS

        # Vérifie les métriques de requête
        assert len(mock_metrics.request_metrics) == 1
        req_metric = mock_metrics.request_metrics[0]
        assert req_metric.app_id == "test-app"
        assert req_metric.model == "text-embedding-ada-002"
        assert req_metric.status == "success"
        assert req_metric.latency_seconds > 0
        assert req_metric.input_tokens == 10
        assert req_metric.output_tokens == 0  # Embeddings n'ont pas d'output tokens

        # Vérifie les métriques de décision
        assert len(mock_metrics.decision_metrics) == 1
        dec_metric = mock_metrics.decision_metrics[0]
        assert dec_metric.app_id == "test-app"
        assert dec_metric.decision == "allow"
        assert dec_metric.source == "policy"

        # Vérifie request_started et request_finished
        assert len(mock_metrics.requests_started) == 1
        assert mock_metrics.requests_started[0] == "test-app"
        assert len(mock_metrics.requests_finished) == 1
        assert mock_metrics.requests_finished[0] == "test-app"

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_policy_denial(self, policy_evaluator, budget_checker):
        """Vérifie que les métriques sont enregistrées lors d'un refus par policy."""
        blocking_rule = PolicyRule(
            id="block-embeddings",
            name="Block Embeddings",
            action=PolicyAction.DENY,
            priority=100,
            conditions={"feature": "embeddings"},
            enabled=True,
        )

        mock_metrics = MockMetrics()
        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([blocking_rule]),
            budget_repository=MockBudgetRepository([]),
            embedding_provider=MockEmbeddingProvider(),
            metrics=mock_metrics,
        )

        command = EmbeddingCommand(
            request_id="policy-deny-test",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["Hello"],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == EmbeddingOutcome.DENIED_POLICY

        # Vérifie les métriques de décision
        assert len(mock_metrics.decision_metrics) == 1
        dec_metric = mock_metrics.decision_metrics[0]
        assert dec_metric.decision == "deny"
        assert dec_metric.source == "policy"

        # Pas de request_metrics car pas d'appel au provider
        assert len(mock_metrics.request_metrics) == 0

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_budget_denial(self, policy_evaluator, budget_checker):
        """Vérifie que les métriques sont enregistrées lors d'un refus par budget."""
        exhausted_budget = Budget(
            id="budget-exhausted",
            app_id="test-app",
            limit_usd=0.001,
            spent_usd=0.001,
            period=BudgetPeriod.MONTHLY,
        )

        mock_metrics = MockMetrics()
        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository([exhausted_budget]),
            embedding_provider=MockEmbeddingProvider(),
            metrics=mock_metrics,
        )

        command = EmbeddingCommand(
            request_id="budget-deny-test",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["Hello"],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == EmbeddingOutcome.DENIED_BUDGET

        # Vérifie les métriques de décision
        assert len(mock_metrics.decision_metrics) == 1
        dec_metric = mock_metrics.decision_metrics[0]
        assert dec_metric.decision == "deny"
        assert dec_metric.source == "budget"

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_error(self, policy_evaluator, budget_checker):
        """Vérifie que les métriques sont enregistrées en cas d'erreur."""
        error_provider = MockEmbeddingProvider(error=Exception("Provider error"))

        mock_metrics = MockMetrics()
        use_case = CreateEmbeddingsUseCase(
            policy_evaluator=policy_evaluator,
            budget_checker=budget_checker,
            policy_repository=MockPolicyRepository([]),
            budget_repository=MockBudgetRepository(
                [Budget(id="b1", app_id="test-app", limit_usd=1000.0)]
            ),
            embedding_provider=error_provider,
            metrics=mock_metrics,
        )

        command = EmbeddingCommand(
            request_id="error-test",
            app_id="test-app",
            org_id="test-org",
            model="text-embedding-ada-002",
            inputs=["Hello"],
            api_key="test-key",
        )

        result = await use_case.execute(command)

        assert result.outcome == EmbeddingOutcome.ERROR

        # Vérifie les métriques de requête avec status error
        assert len(mock_metrics.request_metrics) == 1
        req_metric = mock_metrics.request_metrics[0]
        assert req_metric.status == "error"

        # Vérifie record_error
        assert len(mock_metrics.errors) == 1
        assert mock_metrics.errors[0][0] == "test-app"
        assert mock_metrics.errors[0][1] == "Exception"

    @pytest.mark.asyncio
    async def test_metrics_optional(self, use_case, basic_command):
        """Vérifie que le use case fonctionne sans métriques."""
        # use_case fixture n'a pas de metrics
        result = await use_case.execute(basic_command)

        # Doit fonctionner normalement
        assert result.outcome == EmbeddingOutcome.SUCCESS

    @pytest.mark.asyncio
    async def test_latency_in_metadata(self, use_case_with_metrics, basic_command):
        """Vérifie que la latence est dans les métadonnées du résultat."""
        result = await use_case_with_metrics.execute(basic_command)

        assert result.outcome == EmbeddingOutcome.SUCCESS
        assert "latency_seconds" in result.metadata
        assert result.metadata["latency_seconds"] > 0
