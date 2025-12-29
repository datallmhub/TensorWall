"""Budget Checking - Pure business logic.

AUCUNE dépendance externe. Logique pure.
"""

from dataclasses import dataclass, field

from backend.domain.models import Budget


@dataclass
class BudgetStatus:
    """Résultat de la vérification du budget."""

    allowed: bool
    remaining_usd: float
    usage_percent: float
    exceeded_budgets: list[Budget] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def has_warning(self) -> bool:
        """True si usage > 80%."""
        return self.usage_percent >= 80.0


class BudgetChecker:
    """Vérifie les budgets de manière pure (sans I/O)."""

    # Coûts par 1K tokens (approximatifs)
    MODEL_COSTS = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    }

    DEFAULT_COST = {"input": 0.001, "output": 0.002}

    def check(
        self,
        budgets: list[Budget],
        estimated_cost: float,
    ) -> BudgetStatus:
        """Vérifie si le coût estimé respecte les budgets.

        Args:
            budgets: Liste des budgets à vérifier
            estimated_cost: Coût estimé en USD

        Returns:
            BudgetStatus avec le résultat
        """
        if not budgets:
            return BudgetStatus(
                allowed=True,
                remaining_usd=float("inf"),
                usage_percent=0.0,
                reasons=["No budgets defined"],
            )

        exceeded: list[Budget] = []
        reasons: list[str] = []
        min_remaining = float("inf")
        max_usage = 0.0

        for budget in budgets:
            if budget.remaining_usd < estimated_cost:
                exceeded.append(budget)
                reasons.append(
                    f"Budget '{budget.id}' would exceed: "
                    f"remaining ${budget.remaining_usd:.4f}, "
                    f"estimated ${estimated_cost:.4f}"
                )

            min_remaining = min(min_remaining, budget.remaining_usd)
            max_usage = max(max_usage, budget.usage_percent)

        if exceeded:
            return BudgetStatus(
                allowed=False,
                remaining_usd=min_remaining,
                usage_percent=max_usage,
                exceeded_budgets=exceeded,
                reasons=reasons,
            )

        # Warnings si > 80%
        if max_usage >= 80.0:
            reasons.append(f"Budget usage at {max_usage:.1f}%")

        return BudgetStatus(
            allowed=True,
            remaining_usd=min_remaining,
            usage_percent=max_usage,
            reasons=reasons,
        )

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estime le coût d'une requête.

        Args:
            model: Nom du modèle
            input_tokens: Nombre de tokens en entrée
            output_tokens: Nombre de tokens en sortie

        Returns:
            Coût estimé en USD
        """
        # Trouver le coût du modèle
        costs = self.DEFAULT_COST
        for model_prefix, model_costs in self.MODEL_COSTS.items():
            if model.startswith(model_prefix):
                costs = model_costs
                break

        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]

        return input_cost + output_cost
