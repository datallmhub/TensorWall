"""Application Layer - Use Cases and Orchestration.

Architecture Hexagonale: La couche Application orchestre les appels
entre le Domain (logique pure) et les Ports (interfaces).

Structure:
- use_cases/ : Les cas d'utilisation de l'application
- factory.py : Wiring des dépendances (dependency injection)
"""

from backend.application.use_cases import (
    # Chat
    EvaluateLLMRequestUseCase,
    LLMRequestCommand,
    LLMRequestResult,
    RequestOutcome,
    # Embeddings
    CreateEmbeddingsUseCase,
    EmbeddingCommand,
    EmbeddingResult,
    EmbeddingOutcome,
    # Policies
    ManagePoliciesUseCase,
    PolicyDTO,
    CreatePolicyCommand,
    UpdatePolicyCommand,
    # Budgets
    ManageBudgetsUseCase,
    BudgetDTO,
    CreateBudgetCommand,
    UpdateBudgetCommand,
    BudgetCheckCommand,
)

from backend.application.factory import (
    create_evaluate_llm_request_use_case,
    get_llm_provider_for_model,
    create_embeddings_use_case,
    get_embedding_provider_for_model,
    create_manage_policies_use_case,
    create_manage_budgets_use_case,
)


__all__ = [
    # Chat Use Cases
    "EvaluateLLMRequestUseCase",
    "LLMRequestCommand",
    "LLMRequestResult",
    "RequestOutcome",
    # Embedding Use Cases
    "CreateEmbeddingsUseCase",
    "EmbeddingCommand",
    "EmbeddingResult",
    "EmbeddingOutcome",
    # Policy Use Cases
    "ManagePoliciesUseCase",
    "PolicyDTO",
    "CreatePolicyCommand",
    "UpdatePolicyCommand",
    # Budget Use Cases
    "ManageBudgetsUseCase",
    "BudgetDTO",
    "CreateBudgetCommand",
    "UpdateBudgetCommand",
    "BudgetCheckCommand",
    # Factory
    "create_evaluate_llm_request_use_case",
    "get_llm_provider_for_model",
    "create_embeddings_use_case",
    "get_embedding_provider_for_model",
    "create_manage_policies_use_case",
    "create_manage_budgets_use_case",
]
