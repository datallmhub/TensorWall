"""Evaluate LLM Request Use Case.

Architecture Hexagonale: Use Case qui orchestre les appels domain et ports
pour évaluer et exécuter une requête LLM.

Fonctionnalités:
- Évaluation des policies
- Vérification des budgets
- Appel LLM (sync et streaming)
- Audit logging
- Métriques (optionnel)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator
import time

from backend.domain.policy import PolicyEvaluator, PolicyDecision
from backend.domain.budget import BudgetChecker, BudgetStatus
from backend.domain.models import (
    PolicyAction,
    ChatMessage,
    ChatRequest as DomainChatRequest,
    ChatResponse as DomainChatResponse,
)
from backend.ports.llm_provider import LLMProviderPort
from backend.ports.policy_repository import PolicyRepositoryPort
from backend.ports.budget_repository import BudgetRepositoryPort
from backend.ports.audit_log import AuditLogPort, AuditEntry
from backend.ports.metrics import MetricsPort, RequestMetrics, DecisionMetrics
from backend.ports.abuse_detector import AbuseDetectorPort
from backend.ports.feature_registry import FeatureRegistryPort, FeatureAction
from backend.ports.request_tracing import RequestTracingPort, TraceStep
from backend.ports.encryption import EncryptionPort
from backend.ports.observability import ObservabilityPort


class RequestOutcome(str, Enum):
    """Résultat possible d'une requête."""

    ALLOWED = "allowed"
    DENIED_POLICY = "denied_policy"
    DENIED_BUDGET = "denied_budget"
    DENIED_ABUSE = "denied_abuse"
    DENIED_FEATURE = "denied_feature"
    ERROR = "error"
    DRY_RUN = "dry_run"


@dataclass
class LLMRequestCommand:
    """Command pour évaluer une requête LLM."""

    request_id: str
    app_id: str
    org_id: str | None
    model: str
    messages: list[dict[str, str]]
    environment: str = "development"
    feature: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False
    dry_run: bool = False
    api_key: str | None = None


@dataclass
class LLMRequestResult:
    """Résultat de l'évaluation d'une requête LLM."""

    request_id: str
    outcome: RequestOutcome
    response: DomainChatResponse | None = None
    policy_decision: PolicyDecision | None = None
    budget_status: BudgetStatus | None = None
    error_message: str | None = None
    dry_run_result: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class EvaluateLLMRequestUseCase:
    """Use Case: Évaluer et exécuter une requête LLM.

    Ce use case orchestre:
    1. L'évaluation des policies (via PolicyEvaluator)
    2. La vérification des budgets (via BudgetChecker)
    3. L'appel au LLM (via LLMProviderPort)
    4. L'enregistrement de l'audit (via AuditLogPort)
    5. L'enregistrement des métriques (via MetricsPort)

    Architecture:
    - Dépend uniquement des Ports (interfaces), pas des implémentations
    - Utilise les classes Domain pour la logique métier pure
    - Orchestre les différentes étapes sans contenir de logique métier

    Modes supportés:
    - Requête synchrone (execute)
    - Requête streaming (execute_stream)
    - Dry-run (simulation sans appel LLM)
    """

    def __init__(
        self,
        policy_evaluator: PolicyEvaluator,
        budget_checker: BudgetChecker,
        policy_repository: PolicyRepositoryPort,
        budget_repository: BudgetRepositoryPort,
        llm_provider: LLMProviderPort,
        audit_log: AuditLogPort | None = None,
        metrics: MetricsPort | None = None,
        abuse_detector: AbuseDetectorPort | None = None,
        feature_registry: FeatureRegistryPort | None = None,
        request_tracer: RequestTracingPort | None = None,
        encryption: EncryptionPort | None = None,
        observability: ObservabilityPort | None = None,
    ):
        self.policy_evaluator = policy_evaluator
        self.budget_checker = budget_checker
        self.policy_repository = policy_repository
        self.budget_repository = budget_repository
        self.llm_provider = llm_provider
        self.audit_log = audit_log
        self.metrics = metrics
        self.abuse_detector = abuse_detector
        self.feature_registry = feature_registry
        self.request_tracer = request_tracer
        self.encryption = encryption
        self.observability = observability

    async def execute(self, command: LLMRequestCommand) -> LLMRequestResult:
        """Exécute le use case.

        Flow:
        1. Récupérer les règles de policy depuis le repository
        2. Évaluer les policies avec le contexte de la requête
        3. Si policy.action == DENY -> retourner DENIED_POLICY
        4. Récupérer les budgets depuis le repository
        5. Estimer le coût de la requête
        6. Vérifier le budget
        7. Si budget.allowed == False -> retourner DENIED_BUDGET
        8. Si dry_run -> retourner le résultat sans appeler le LLM
        9. Appeler le LLM via le provider
        10. Enregistrer l'audit
        11. Retourner le résultat
        """
        trace = None
        try:
            # 0. Create trace (si configuré)
            if self.request_tracer:
                trace = await self.request_tracer.create_trace(
                    request_id=command.request_id,
                    app_id=command.app_id,
                    org_id=command.org_id,
                    model=command.model,
                    context={
                        "environment": command.environment,
                        "feature": command.feature,
                        "dry_run": command.dry_run,
                    },
                )

            # 0a. Abuse detection (si configuré)
            if self.abuse_detector:
                await self._start_span(trace, TraceStep.ABUSE_CHECK.value)
                abuse_result = await self.abuse_detector.check_request(
                    app_id=command.app_id,
                    feature=command.feature or "default",
                    model=command.model,
                    messages=command.messages,
                    request_id=command.request_id,
                )
                await self._end_span(
                    trace,
                    TraceStep.ABUSE_CHECK.value,
                    "blocked" if abuse_result.blocked else "ok",
                )
                if abuse_result.blocked:
                    self._record_decision_metrics(command, "deny", "abuse")
                    error_msg = (
                        abuse_result.reason
                        or f"Blocked for abuse: {abuse_result.abuse_type.value if abuse_result.abuse_type else 'unknown'}"
                    )
                    await self._handle_blocked_request(
                        command, trace, RequestOutcome.DENIED_ABUSE, "abuse", error_msg
                    )
                    return LLMRequestResult(
                        request_id=command.request_id,
                        outcome=RequestOutcome.DENIED_ABUSE,
                        error_message=error_msg,
                        metadata={
                            "abuse_type": (
                                abuse_result.abuse_type.value
                                if abuse_result.abuse_type
                                else None
                            ),
                            "cooldown_seconds": abuse_result.cooldown_seconds,
                        },
                    )

            # 0b. Feature allowlist (si configuré)
            if self.feature_registry:
                await self._start_span(trace, TraceStep.FEATURE_CHECK.value)
                feature_result = await self.feature_registry.check_feature(
                    app_id=command.app_id,
                    feature_id=command.feature,
                    action=FeatureAction.CHAT,  # Default action for chat requests
                    model=command.model,
                    environment=command.environment,
                )
                await self._end_span(
                    trace,
                    TraceStep.FEATURE_CHECK.value,
                    "denied" if not feature_result.allowed else "ok",
                )
                if not feature_result.allowed:
                    self._record_decision_metrics(command, "deny", "feature")
                    await self._handle_blocked_request(
                        command,
                        trace,
                        RequestOutcome.DENIED_FEATURE,
                        "feature",
                        feature_result.reason,
                    )
                    return LLMRequestResult(
                        request_id=command.request_id,
                        outcome=RequestOutcome.DENIED_FEATURE,
                        error_message=feature_result.reason,
                        metadata={
                            "feature_decision": feature_result.decision.value,
                            "feature_id": feature_result.feature_id,
                        },
                    )

            # 1. Récupérer les règles de policy
            await self._start_span(trace, TraceStep.POLICY_EVALUATION.value)
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
            await self._end_span(
                trace,
                TraceStep.POLICY_EVALUATION.value,
                "denied" if policy_decision.action == PolicyAction.DENY else "ok",
            )

            # 3. Vérifier si la policy refuse la requête
            if policy_decision.action == PolicyAction.DENY:
                await self._log_decision(
                    command, RequestOutcome.DENIED_POLICY, policy_decision
                )
                self._record_decision_metrics(command, "deny", "policy")
                error_msg = "; ".join(policy_decision.reasons) or "Denied by policy"
                await self._handle_blocked_request(
                    command, trace, RequestOutcome.DENIED_POLICY, "policy", error_msg
                )
                return LLMRequestResult(
                    request_id=command.request_id,
                    outcome=RequestOutcome.DENIED_POLICY,
                    policy_decision=policy_decision,
                    error_message=error_msg,
                )

            # 4. Récupérer les budgets
            await self._start_span(trace, TraceStep.BUDGET_CHECK.value)
            budgets = await self.budget_repository.get_budgets_for_app(
                app_id=command.app_id,
                org_id=command.org_id,
            )

            # 5. Estimer le coût (approximatif avant l'appel)
            estimated_input_tokens = self._estimate_input_tokens(command.messages)
            estimated_output_tokens = command.max_tokens or 1000
            estimated_cost = self.budget_checker.estimate_cost(
                model=command.model,
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
            )

            # 6. Vérifier le budget
            budget_status = self.budget_checker.check(budgets, estimated_cost)
            await self._end_span(
                trace,
                TraceStep.BUDGET_CHECK.value,
                "denied" if not budget_status.allowed else "ok",
            )

            # 7. Vérifier si le budget refuse la requête
            if not budget_status.allowed:
                await self._log_decision(
                    command,
                    RequestOutcome.DENIED_BUDGET,
                    policy_decision,
                    budget_status,
                )
                self._record_decision_metrics(command, "deny", "budget")
                error_msg = "; ".join(budget_status.reasons) or "Budget exceeded"
                await self._handle_blocked_request(
                    command, trace, RequestOutcome.DENIED_BUDGET, "budget", error_msg
                )
                return LLMRequestResult(
                    request_id=command.request_id,
                    outcome=RequestOutcome.DENIED_BUDGET,
                    policy_decision=policy_decision,
                    budget_status=budget_status,
                    error_message=error_msg,
                )

            # 8. Mode dry run - retourner sans appeler le LLM
            if command.dry_run:
                # Complete trace for dry run
                if trace and self.request_tracer:
                    await self.request_tracer.complete_trace(
                        trace_id=trace.trace_id,
                        outcome="dry_run",
                        final_data={"estimated_cost_usd": estimated_cost},
                    )
                return LLMRequestResult(
                    request_id=command.request_id,
                    outcome=RequestOutcome.DRY_RUN,
                    policy_decision=policy_decision,
                    budget_status=budget_status,
                    dry_run_result={
                        "would_be_allowed": True,
                        "estimated_cost_usd": estimated_cost,
                        "policy_action": policy_decision.action.value,
                        "budget_remaining_usd": budget_status.remaining_usd,
                        "budget_usage_percent": budget_status.usage_percent,
                    },
                )

            # 9. Appeler le LLM
            # API key not required for mock or local providers (ollama, lmstudio)
            local_providers = ("mock", "ollama", "lmstudio")
            is_local_provider = self.llm_provider.name in local_providers
            if not command.api_key and not is_local_provider:
                await self._handle_blocked_request(
                    command,
                    trace,
                    RequestOutcome.ERROR,
                    "validation",
                    "API key required",
                )
                return LLMRequestResult(
                    request_id=command.request_id,
                    outcome=RequestOutcome.ERROR,
                    error_message="API key required for LLM call",
                )

            # 9a. Déchiffrer l'API key si nécessaire
            api_key = command.api_key
            if self.encryption and api_key.startswith("enc:"):
                await self._start_span(trace, "decrypt_api_key")
                try:
                    api_key = await self.encryption.decrypt_api_key(
                        api_key[4:]
                    )  # Remove "enc:" prefix
                    await self._end_span(trace, "decrypt_api_key", "ok")
                except Exception as e:
                    await self._end_span(
                        trace, "decrypt_api_key", "error", error=str(e)
                    )
                    await self._handle_blocked_request(
                        command,
                        trace,
                        RequestOutcome.ERROR,
                        "encryption",
                        f"Failed to decrypt API key: {e}",
                    )
                    return LLMRequestResult(
                        request_id=command.request_id,
                        outcome=RequestOutcome.ERROR,
                        error_message=f"Failed to decrypt API key: {e}",
                    )

            domain_request = DomainChatRequest(
                model=command.model,
                messages=[
                    ChatMessage(role=m["role"], content=m["content"])
                    for m in command.messages
                ],
                max_tokens=command.max_tokens,
                temperature=command.temperature,
                stream=command.stream,
            )

            start_time = time.time()
            if self.metrics:
                self.metrics.request_started(command.app_id)

            await self._start_span(trace, TraceStep.LLM_REQUEST.value)
            response = await self.llm_provider.chat(domain_request, api_key)
            await self._end_span(
                trace,
                TraceStep.LLM_REQUEST.value,
                "ok",
                {
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )

            latency_seconds = time.time() - start_time

            # 10. Enregistrer l'audit
            await self._log_decision(
                command,
                RequestOutcome.ALLOWED,
                policy_decision,
                budget_status,
                response,
            )

            # 11. Enregistrer les métriques
            self._record_request_metrics(
                command=command,
                status="success",
                latency_seconds=latency_seconds,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
            self._record_decision_metrics(command, "allow", "policy")
            if self.metrics:
                self.metrics.request_finished(command.app_id)

            # 12. Complete trace
            # Use "warned" outcome if policy decision is WARN
            trace_outcome = (
                "warned" if policy_decision.action == PolicyAction.WARN else "allowed"
            )
            await self._handle_successful_request(
                command, trace, response, trace_outcome
            )

            # 12a. Enregistrer les métriques d'observabilité
            actual_cost = self.budget_checker.estimate_cost(
                model=command.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

            if self.observability:
                await self.observability.record_request(
                    app_id=command.app_id,
                    org_id=command.org_id or "default",
                    model=command.model,
                    environment=command.environment,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_usd=actual_cost,
                    latency_ms=latency_seconds * 1000,
                    outcome="allowed",
                    feature=command.feature,
                )

            # 12b. Mettre à jour le budget avec le coût réel
            if budgets and actual_cost > 0:
                for budget in budgets:
                    await self.budget_repository.record_usage(
                        budget_id=budget.id,
                        amount_usd=actual_cost,
                    )

            # 13. Retourner le résultat
            return LLMRequestResult(
                request_id=command.request_id,
                outcome=RequestOutcome.ALLOWED,
                response=response,
                policy_decision=policy_decision,
                budget_status=budget_status,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "model": response.model,
                    "latency_seconds": latency_seconds,
                },
            )

        except Exception as e:
            self._record_request_metrics(command, status="error", latency_seconds=0)
            if self.metrics:
                self.metrics.record_error(command.app_id, type(e).__name__)
            # Fail trace for error
            if trace and self.request_tracer:
                await self.request_tracer.fail_trace(
                    trace_id=trace.trace_id,
                    error=str(e),
                    step="execute",
                )
            return LLMRequestResult(
                request_id=command.request_id,
                outcome=RequestOutcome.ERROR,
                error_message=str(e),
            )

    def _estimate_input_tokens(self, messages: list[dict[str, str]]) -> int:
        """Estime le nombre de tokens en entrée (approximation simple)."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        # Approximation: 4 caractères par token
        return max(10, total_chars // 4)

    async def _log_decision(
        self,
        command: LLMRequestCommand,
        outcome: RequestOutcome,
        policy_decision: PolicyDecision | None = None,
        budget_status: BudgetStatus | None = None,
        response: DomainChatResponse | None = None,
    ) -> None:
        """Enregistre la décision dans l'audit log."""
        if not self.audit_log:
            return

        entry = AuditEntry(
            event_type="llm_request",
            request_id=command.request_id,
            app_id=command.app_id,
            org_id=command.org_id,
            model=command.model,
            action=policy_decision.action.value if policy_decision else None,
            outcome=outcome.value,
            details={
                "environment": command.environment,
                "feature": command.feature,
                "policy_reasons": policy_decision.reasons if policy_decision else [],
                "budget_usage_percent": (
                    budget_status.usage_percent if budget_status else None
                ),
            },
            input_tokens=response.input_tokens if response else None,
            output_tokens=response.output_tokens if response else None,
        )

        await self.audit_log.log(entry)

    def _record_request_metrics(
        self,
        command: LLMRequestCommand,
        status: str,
        latency_seconds: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Enregistre les métriques d'une requête."""
        if not self.metrics:
            return

        metrics = RequestMetrics(
            app_id=command.app_id,
            model=command.model,
            status=status,
            latency_seconds=latency_seconds,
            feature=command.feature or "default",
            environment=command.environment,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
        self.metrics.record_request(metrics)

    def _record_decision_metrics(
        self,
        command: LLMRequestCommand,
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

    async def execute_stream(
        self,
        command: LLMRequestCommand,
    ) -> AsyncIterator[str] | LLMRequestResult:
        """Exécute le use case en mode streaming.

        Effectue les mêmes validations que execute() (policies, budget),
        mais retourne un AsyncIterator pour le streaming au lieu d'une réponse complète.

        Args:
            command: Commande de requête LLM

        Returns:
            AsyncIterator[str] si les validations passent et streaming commence
            LLMRequestResult si la requête est refusée ou erreur

        Usage:
            result = await use_case.execute_stream(command)
            if isinstance(result, LLMRequestResult):
                # Handle denial or error
            else:
                async for chunk in result:
                    # Handle streaming chunk
        """
        try:
            # 0a. Abuse detection (si configuré)
            if self.abuse_detector:
                abuse_result = await self.abuse_detector.check_request(
                    app_id=command.app_id,
                    feature=command.feature or "default",
                    model=command.model,
                    messages=command.messages,
                    request_id=command.request_id,
                )
                if abuse_result.blocked:
                    self._record_decision_metrics(command, "deny", "abuse")
                    return LLMRequestResult(
                        request_id=command.request_id,
                        outcome=RequestOutcome.DENIED_ABUSE,
                        error_message=abuse_result.reason
                        or f"Blocked for abuse: {abuse_result.abuse_type.value if abuse_result.abuse_type else 'unknown'}",
                        metadata={
                            "abuse_type": (
                                abuse_result.abuse_type.value
                                if abuse_result.abuse_type
                                else None
                            ),
                            "cooldown_seconds": abuse_result.cooldown_seconds,
                        },
                    )

            # 0b. Feature allowlist (si configuré)
            if self.feature_registry:
                feature_result = await self.feature_registry.check_feature(
                    app_id=command.app_id,
                    feature_id=command.feature,
                    action=FeatureAction.CHAT,
                    model=command.model,
                    environment=command.environment,
                )
                if not feature_result.allowed:
                    self._record_decision_metrics(command, "deny", "feature")
                    return LLMRequestResult(
                        request_id=command.request_id,
                        outcome=RequestOutcome.DENIED_FEATURE,
                        error_message=feature_result.reason,
                        metadata={
                            "feature_decision": feature_result.decision.value,
                            "feature_id": feature_result.feature_id,
                        },
                    )

            # 1-7: Mêmes validations que execute()
            rules = await self.policy_repository.get_active_rules(
                org_id=command.org_id,
                app_id=command.app_id,
                environment=command.environment,
            )

            policy_context = {
                "model": command.model,
                "environment": command.environment,
                "feature": command.feature,
                "app_id": command.app_id,
            }
            policy_decision = self.policy_evaluator.evaluate(rules, policy_context)

            if policy_decision.action == PolicyAction.DENY:
                await self._log_decision(
                    command, RequestOutcome.DENIED_POLICY, policy_decision
                )
                self._record_decision_metrics(command, "deny", "policy")
                return LLMRequestResult(
                    request_id=command.request_id,
                    outcome=RequestOutcome.DENIED_POLICY,
                    policy_decision=policy_decision,
                    error_message="; ".join(policy_decision.reasons)
                    or "Denied by policy",
                )

            budgets = await self.budget_repository.get_budgets_for_app(
                app_id=command.app_id,
                org_id=command.org_id,
            )

            estimated_input_tokens = self._estimate_input_tokens(command.messages)
            estimated_output_tokens = command.max_tokens or 1000
            estimated_cost = self.budget_checker.estimate_cost(
                model=command.model,
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
            )

            budget_status = self.budget_checker.check(budgets, estimated_cost)

            if not budget_status.allowed:
                await self._log_decision(
                    command,
                    RequestOutcome.DENIED_BUDGET,
                    policy_decision,
                    budget_status,
                )
                self._record_decision_metrics(command, "deny", "budget")
                return LLMRequestResult(
                    request_id=command.request_id,
                    outcome=RequestOutcome.DENIED_BUDGET,
                    policy_decision=policy_decision,
                    budget_status=budget_status,
                    error_message="; ".join(budget_status.reasons) or "Budget exceeded",
                )

            # API key not required for mock or local providers (ollama, lmstudio)
            local_providers = ("mock", "ollama", "lmstudio")
            is_local_provider = self.llm_provider.name in local_providers
            if not command.api_key and not is_local_provider:
                return LLMRequestResult(
                    request_id=command.request_id,
                    outcome=RequestOutcome.ERROR,
                    error_message="API key required for LLM call",
                )

            # Créer la requête domain
            domain_request = DomainChatRequest(
                model=command.model,
                messages=[
                    ChatMessage(role=m["role"], content=m["content"])
                    for m in command.messages
                ],
                max_tokens=command.max_tokens,
                temperature=command.temperature,
                stream=True,
            )

            # Enregistrer métriques de début
            if self.metrics:
                self.metrics.request_started(command.app_id)
            self._record_decision_metrics(command, "allow", "policy")

            # Retourner le stream wrapper avec cleanup
            return self._stream_with_metrics(
                command=command,
                domain_request=domain_request,
                policy_decision=policy_decision,
                budget_status=budget_status,
            )

        except Exception as e:
            self._record_request_metrics(command, status="error", latency_seconds=0)
            if self.metrics:
                self.metrics.record_error(command.app_id, type(e).__name__)
            return LLMRequestResult(
                request_id=command.request_id,
                outcome=RequestOutcome.ERROR,
                error_message=str(e),
            )

    async def _stream_with_metrics(
        self,
        command: LLMRequestCommand,
        domain_request: DomainChatRequest,
        policy_decision: PolicyDecision,
        budget_status: BudgetStatus,
    ) -> AsyncIterator[str]:
        """Wrapper de streaming avec enregistrement des métriques à la fin."""
        start_time = time.time()
        try:
            async for chunk in self.llm_provider.chat_stream(
                domain_request, command.api_key
            ):
                yield chunk

            # Enregistrer les métriques après streaming
            latency_seconds = time.time() - start_time
            self._record_request_metrics(
                command=command,
                status="success",
                latency_seconds=latency_seconds,
            )
        except Exception as e:
            latency_seconds = time.time() - start_time
            self._record_request_metrics(
                command=command,
                status="error",
                latency_seconds=latency_seconds,
            )
            if self.metrics:
                self.metrics.record_error(command.app_id, type(e).__name__)
            raise
        finally:
            if self.metrics:
                self.metrics.request_finished(command.app_id)

    async def _handle_blocked_request(
        self,
        command: LLMRequestCommand,
        trace,
        outcome: RequestOutcome,
        blocked_by: str,
        reason: str,
    ) -> None:
        """Handle a blocked request: fail trace."""
        # Fail the trace with correct outcome
        if trace and self.request_tracer:
            await self.request_tracer.fail_trace(
                trace_id=trace.trace_id,
                error=reason,
                step=blocked_by,
                outcome=outcome.value if outcome else "error",
            )

    async def _handle_successful_request(
        self,
        command: LLMRequestCommand,
        trace,
        response,
        outcome: str = "allowed",
    ) -> None:
        """Handle a successful request: complete trace."""
        # Complete the trace
        if trace and self.request_tracer:
            await self.request_tracer.complete_trace(
                trace_id=trace.trace_id,
                outcome=outcome,
                final_data={
                    "input_tokens": response.input_tokens if response else 0,
                    "output_tokens": response.output_tokens if response else 0,
                    "model": response.model if response else command.model,
                },
            )

    async def _start_span(self, trace, step: str, data: dict | None = None) -> None:
        """Start a trace span if tracer is configured."""
        if trace and self.request_tracer:
            await self.request_tracer.start_span(trace.trace_id, step, data)

    async def _end_span(
        self,
        trace,
        step: str,
        status: str = "ok",
        data: dict | None = None,
        error: str | None = None,
    ) -> None:
        """End a trace span if tracer is configured."""
        if trace and self.request_tracer:
            await self.request_tracer.end_span(
                trace.trace_id, step, status, data, error
            )
