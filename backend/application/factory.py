"""Factory - Dependency Injection / Wiring.

Architecture Hexagonale: Le Factory assemble les dépendances pour créer
les Use Cases avec leurs ports concrets (adapters).

C'est ici que l'on "câble" l'application en connectant:
- Domain (logique pure)
- Ports (interfaces)
- Adapters (implémentations concrètes)
"""

from backend.domain.policy import PolicyEvaluator
from backend.domain.budget import BudgetChecker

from backend.adapters.llm import (
    OpenAIAdapter,
    AnthropicAdapter,
    OllamaAdapter,
    OpenAIEmbeddingAdapter,
)
from backend.core.config import settings
from backend.adapters.postgres import PolicyRepositoryAdapter, BudgetRepositoryAdapter
from backend.adapters.audit import InMemoryAuditAdapter
from backend.adapters.prometheus import InMemoryMetricsAdapter
from backend.adapters.tracing import PostgresRequestTracingAdapter

from backend.application.use_cases import (
    EvaluateLLMRequestUseCase,
    CreateEmbeddingsUseCase,
    ManagePoliciesUseCase,
    ManageBudgetsUseCase,
)

from backend.ports.llm_provider import LLMProviderPort
from backend.ports.embedding_provider import EmbeddingProviderPort
from backend.ports.audit_log import AuditLogPort
from backend.ports.metrics import MetricsPort
from backend.ports.request_tracing import RequestTracingPort


def get_llm_provider_for_model(model: str) -> LLMProviderPort:
    """Retourne le provider approprié pour un modèle donné.

    Args:
        model: Nom du modèle (ex: "gpt-4", "claude-3-opus", "lmstudio/qwen/qwen2.5-vl-7b")

    Returns:
        Le provider LLM approprié
    """
    # Mock provider only in test environment
    if settings.environment == "test":
        from backend.adapters.llm import MockAdapter

        mock_adapter = MockAdapter()
        if mock_adapter.supports_model(model):
            return mock_adapter

    # LM Studio models (explicit prefix)
    if model.startswith("lmstudio/"):
        lmstudio_url = getattr(
            settings, "lmstudio_api_url", "http://host.docker.internal:11434"
        )
        return OllamaAdapter(base_url=lmstudio_url)

    # Ollama (local models like qwen, llama, mistral, etc.)
    ollama_adapter = OllamaAdapter()
    if ollama_adapter.supports_model(model):
        return ollama_adapter

    # OpenAI
    openai_adapter = OpenAIAdapter()
    if openai_adapter.supports_model(model):
        return openai_adapter

    # Anthropic
    anthropic_adapter = AnthropicAdapter()
    if anthropic_adapter.supports_model(model):
        return anthropic_adapter

    # No provider found - raise error instead of falling back to mock
    raise ValueError(f"No provider found for model: {model}")


def create_evaluate_llm_request_use_case(
    model: str = "mock-gpt-4",
    audit_log: AuditLogPort | None = None,
    metrics: MetricsPort | None = None,
    request_tracing: RequestTracingPort | None = None,
    enable_audit: bool = False,
    enable_metrics: bool = False,
    enable_tracing: bool = True,
) -> EvaluateLLMRequestUseCase:
    """Factory pour créer le use case EvaluateLLMRequest.

    Cette factory assemble toutes les dépendances:
    - Domain: PolicyEvaluator, BudgetChecker
    - Adapters: LLM provider, repositories, audit, metrics, tracing

    Args:
        model: Le modèle LLM à utiliser (pour sélectionner le provider)
        audit_log: Instance optionnelle de AuditLogPort (override enable_audit)
        metrics: Instance optionnelle de MetricsPort (override enable_metrics)
        request_tracing: Instance optionnelle de RequestTracingPort (override enable_tracing)
        enable_audit: Si True et audit_log non fourni, crée InMemoryAuditAdapter
        enable_metrics: Si True et metrics non fourni, crée InMemoryMetricsAdapter
        enable_tracing: Si True et request_tracing non fourni, crée PostgresRequestTracingAdapter

    Returns:
        Instance du use case prête à l'emploi
    """
    # Domain (logique pure, pas de dépendances)
    policy_evaluator = PolicyEvaluator()
    budget_checker = BudgetChecker()

    # Adapters (implémentations concrètes des ports)
    llm_provider = get_llm_provider_for_model(model)
    policy_repository = PolicyRepositoryAdapter()
    budget_repository = BudgetRepositoryAdapter()

    # Audit (optionnel)
    if audit_log is None and enable_audit:
        audit_log = InMemoryAuditAdapter()

    # Metrics (optionnel)
    if metrics is None and enable_metrics:
        metrics = InMemoryMetricsAdapter()

    # Request Tracing (enabled by default for observability)
    if request_tracing is None and enable_tracing:
        request_tracing = PostgresRequestTracingAdapter()

    # Assemble le use case
    return EvaluateLLMRequestUseCase(
        policy_evaluator=policy_evaluator,
        budget_checker=budget_checker,
        policy_repository=policy_repository,
        budget_repository=budget_repository,
        llm_provider=llm_provider,
        audit_log=audit_log,
        metrics=metrics,
        request_tracer=request_tracing,
    )


def get_embedding_provider_for_model(model: str) -> EmbeddingProviderPort:
    """Retourne le provider d'embedding approprié pour un modèle donné.

    Args:
        model: Nom du modèle (ex: "text-embedding-ada-002")

    Returns:
        Le provider d'embedding approprié
    """
    openai_adapter = OpenAIEmbeddingAdapter()
    if openai_adapter.supports_model(model):
        return openai_adapter

    # Default to OpenAI for unknown models
    return openai_adapter


def create_embeddings_use_case(
    model: str = "text-embedding-ada-002",
) -> CreateEmbeddingsUseCase:
    """Factory pour créer le use case CreateEmbeddings.

    Args:
        model: Le modèle d'embedding à utiliser

    Returns:
        Instance du use case prête à l'emploi
    """
    # Domain
    policy_evaluator = PolicyEvaluator()
    budget_checker = BudgetChecker()

    # Adapters
    embedding_provider = get_embedding_provider_for_model(model)
    policy_repository = PolicyRepositoryAdapter()
    budget_repository = BudgetRepositoryAdapter()

    return CreateEmbeddingsUseCase(
        policy_evaluator=policy_evaluator,
        budget_checker=budget_checker,
        policy_repository=policy_repository,
        budget_repository=budget_repository,
        embedding_provider=embedding_provider,
    )


def create_manage_policies_use_case() -> ManagePoliciesUseCase:
    """Factory pour créer le use case ManagePolicies."""
    policy_repository = PolicyRepositoryAdapter()
    return ManagePoliciesUseCase(policy_repository=policy_repository)


def create_manage_budgets_use_case() -> ManageBudgetsUseCase:
    """Factory pour créer le use case ManageBudgets."""
    budget_repository = BudgetRepositoryAdapter()
    budget_checker = BudgetChecker()
    return ManageBudgetsUseCase(
        budget_repository=budget_repository,
        budget_checker=budget_checker,
    )
