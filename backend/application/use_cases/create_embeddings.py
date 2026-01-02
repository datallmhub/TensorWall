"""Create Embeddings Use Case.

Architecture Hexagonale: Use Case qui orchestre les appels domain et ports
pour créer des embeddings.

Fonctionnalités:
- Évaluation des policies
- Vérification des budgets
- Appel au provider d'embedding
- Métriques (optionnel)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time

from backend.domain.policy import PolicyEvaluator, PolicyDecision
from backend.domain.budget import BudgetChecker, BudgetStatus
from backend.domain.models import (
    PolicyAction,
    EmbeddingRequest as DomainEmbeddingRequest,
    EmbeddingResponse as DomainEmbeddingResponse,
)
from backend.ports.embedding_provider import EmbeddingProviderPort
from backend.ports.policy_repository import PolicyRepositoryPort
from backend.ports.budget_repository import BudgetRepositoryPort
from backend.ports.metrics import MetricsPort, RequestMetrics, DecisionMetrics


class EmbeddingOutcome(str, Enum):
    """Résultat possible d'une requête d'embedding."""

    SUCCESS = "success"
    DENIED_POLICY = "denied_policy"
    DENIED_BUDGET = "denied_budget"
    ERROR = "error"


@dataclass
class EmbeddingCommand:
    """Command pour créer des embeddings."""

    request_id: str
    app_id: str
    org_id: str | None
    model: str
    inputs: list[str]
    encoding_format: str = "float"
    environment: str = "development"
    feature: str = "embeddings"
    api_key: str | None = None


@dataclass
class EmbeddingResult:
    """Résultat de la création d'embeddings."""

    request_id: str
    outcome: EmbeddingOutcome
    response: DomainEmbeddingResponse | None = None
    policy_decision: PolicyDecision | None = None
    budget_status: BudgetStatus | None = None
    error_message: str | None = None
    cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class CreateEmbeddingsUseCase:
    """Use Case: Créer des embeddings.

    Ce use case orchestre:
    1. L'évaluation des policies
    2. La vérification des budgets
    3. L'appel au provider d'embedding
    """

    # Coût approximatif par 1K tokens pour les embeddings
    EMBEDDING_COST_PER_1K = 0.0001  # $0.0001 per 1K tokens

    def __init__(
        self,
        policy_evaluator: PolicyEvaluator,
        budget_checker: BudgetChecker,
        policy_repository: PolicyRepositoryPort,
        budget_repository: BudgetRepositoryPort,
        embedding_provider: EmbeddingProviderPort,
        metrics: MetricsPort | None = None,
    ):
        self.policy_evaluator = policy_evaluator
        self.budget_checker = budget_checker
        self.policy_repository = policy_repository
        self.budget_repository = budget_repository
        self.embedding_provider = embedding_provider
        self.metrics = metrics

    async def execute(self, command: EmbeddingCommand) -> EmbeddingResult:
        """Exécute le use case."""
        try:
            # 1. Récupérer les règles de policy
            rules = await self.policy_repository.get_active_rules(
                org_id=command.org_id,
                app_id=command.app_id,
                environment=command.environment,
            )

            # 2. Évaluer les policies
            policy_context = {
                "model": command.model,
                "environment": command.environment,
                "feature": command.feature,
                "app_id": command.app_id,
            }
            policy_decision = self.policy_evaluator.evaluate(rules, policy_context)

            # 3. Vérifier si la policy refuse
            if policy_decision.action == PolicyAction.DENY:
                self._record_decision_metrics(command, "deny", "policy")
                return EmbeddingResult(
                    request_id=command.request_id,
                    outcome=EmbeddingOutcome.DENIED_POLICY,
                    policy_decision=policy_decision,
                    error_message="; ".join(policy_decision.reasons)
                    or "Denied by policy",
                )

            # 4. Récupérer les budgets
            budgets = await self.budget_repository.get_budgets_for_app(
                app_id=command.app_id,
                org_id=command.org_id,
            )

            # 5. Estimer le coût
            estimated_tokens = sum(len(text.split()) * 1.3 for text in command.inputs)
            estimated_cost = (estimated_tokens / 1000) * self.EMBEDDING_COST_PER_1K

            # 6. Vérifier le budget
            budget_status = self.budget_checker.check(budgets, estimated_cost)

            if not budget_status.allowed:
                self._record_decision_metrics(command, "deny", "budget")
                return EmbeddingResult(
                    request_id=command.request_id,
                    outcome=EmbeddingOutcome.DENIED_BUDGET,
                    policy_decision=policy_decision,
                    budget_status=budget_status,
                    error_message="; ".join(budget_status.reasons) or "Budget exceeded",
                )

            # 7. Vérifier l'API key
            if not command.api_key:
                return EmbeddingResult(
                    request_id=command.request_id,
                    outcome=EmbeddingOutcome.ERROR,
                    error_message="API key required for embedding call",
                )

            # 8. Appeler le provider
            domain_request = DomainEmbeddingRequest(
                model=command.model,
                input=command.inputs,
                encoding_format=command.encoding_format,
            )

            start_time = time.time()
            if self.metrics:
                self.metrics.request_started(command.app_id)

            response = await self.embedding_provider.embed(
                domain_request, command.api_key
            )

            latency_seconds = time.time() - start_time

            # 9. Calculer le coût réel
            actual_cost = (response.total_tokens / 1000) * self.EMBEDDING_COST_PER_1K

            # 10. Enregistrer les métriques
            self._record_request_metrics(
                command=command,
                status="success",
                latency_seconds=latency_seconds,
                total_tokens=response.total_tokens,
                cost_usd=actual_cost,
            )
            self._record_decision_metrics(command, "allow", "policy")
            if self.metrics:
                self.metrics.request_finished(command.app_id)

            return EmbeddingResult(
                request_id=command.request_id,
                outcome=EmbeddingOutcome.SUCCESS,
                response=response,
                policy_decision=policy_decision,
                budget_status=budget_status,
                cost_usd=actual_cost,
                metadata={
                    "total_tokens": response.total_tokens,
                    "model": response.model,
                    "num_embeddings": len(response.data),
                    "latency_seconds": latency_seconds,
                },
            )

        except Exception as e:
            self._record_request_metrics(command, status="error", latency_seconds=0)
            if self.metrics:
                self.metrics.record_error(command.app_id, type(e).__name__)
            return EmbeddingResult(
                request_id=command.request_id,
                outcome=EmbeddingOutcome.ERROR,
                error_message=str(e),
            )

    def _record_request_metrics(
        self,
        command: EmbeddingCommand,
        status: str,
        latency_seconds: float,
        total_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Enregistre les métriques d'une requête d'embedding."""
        if not self.metrics:
            return

        metrics = RequestMetrics(
            app_id=command.app_id,
            model=command.model,
            status=status,
            latency_seconds=latency_seconds,
            feature=command.feature,
            environment=command.environment,
            input_tokens=total_tokens,  # For embeddings, total_tokens is input
            output_tokens=0,  # Embeddings don't have output tokens
            cost_usd=cost_usd,
        )
        self.metrics.record_request(metrics)

    def _record_decision_metrics(
        self,
        command: EmbeddingCommand,
        decision: str,
        source: str,
    ) -> None:
        """Enregistre les métriques d'une décision."""
        if not self.metrics:
            return

        metrics = DecisionMetrics(
            app_id=command.app_id,
            decision=decision,
            source=source,
        )
        self.metrics.record_decision(metrics)
