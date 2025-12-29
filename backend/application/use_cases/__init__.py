"""Use Cases - Application Layer orchestration.

Architecture Hexagonale: Les Use Cases orchestrent les appels au Domain
et aux Ports pour implémenter les cas d'utilisation de l'application.
"""

from backend.application.use_cases.evaluate_llm_request import (
    EvaluateLLMRequestUseCase,
    LLMRequestCommand,
    LLMRequestResult,
    RequestOutcome,
)

from backend.application.use_cases.create_embeddings import (
    CreateEmbeddingsUseCase,
    EmbeddingCommand,
    EmbeddingResult,
    EmbeddingOutcome,
)

from backend.application.use_cases.manage_policies import (
    ManagePoliciesUseCase,
    PolicyDTO,
    CreatePolicyCommand,
    UpdatePolicyCommand,
)

from backend.application.use_cases.manage_budgets import (
    ManageBudgetsUseCase,
    BudgetDTO,
    CreateBudgetCommand,
    UpdateBudgetCommand,
    BudgetCheckCommand,
)


__all__ = [
    # Chat
    "EvaluateLLMRequestUseCase",
    "LLMRequestCommand",
    "LLMRequestResult",
    "RequestOutcome",
    # Embeddings
    "CreateEmbeddingsUseCase",
    "EmbeddingCommand",
    "EmbeddingResult",
    "EmbeddingOutcome",
    # Policies
    "ManagePoliciesUseCase",
    "PolicyDTO",
    "CreatePolicyCommand",
    "UpdatePolicyCommand",
    # Budgets
    "ManageBudgetsUseCase",
    "BudgetDTO",
    "CreateBudgetCommand",
    "UpdateBudgetCommand",
    "BudgetCheckCommand",
]
