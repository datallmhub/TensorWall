"""Policy Evaluation - Pure business logic.

AUCUNE dépendance externe. Logique pure.
"""

from dataclasses import dataclass, field

from backend.domain.models import PolicyRule, PolicyAction


@dataclass
class PolicyDecision:
    """Résultat de l'évaluation des policies."""

    action: PolicyAction
    matched_rules: list[PolicyRule] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def is_allowed(self) -> bool:
        return self.action == PolicyAction.ALLOW

    @property
    def is_denied(self) -> bool:
        return self.action == PolicyAction.DENY


class PolicyEvaluator:
    """Évalue les policies de manière pure (sans I/O)."""

    def evaluate(
        self,
        rules: list[PolicyRule],
        context: dict,
    ) -> PolicyDecision:
        """Évalue les règles contre le contexte.

        Args:
            rules: Liste des règles à évaluer
            context: Contexte de la requête (app_id, model, environment, etc.)

        Returns:
            PolicyDecision avec le résultat
        """
        if not rules:
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                reasons=["No policies defined"],
            )

        matched_rules: list[PolicyRule] = []
        reasons: list[str] = []

        # Trier par priorité (plus haute d'abord)
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if not rule.enabled:
                continue

            if self._matches(rule, context):
                matched_rules.append(rule)
                reasons.append(f"Rule '{rule.name}' matched")

                # Si DENY, on arrête immédiatement
                if rule.action == PolicyAction.DENY:
                    return PolicyDecision(
                        action=PolicyAction.DENY,
                        matched_rules=matched_rules,
                        reasons=reasons,
                    )

        # Déterminer l'action finale
        if not matched_rules:
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                reasons=["No matching rules"],
            )

        # Si on a des WARN, on permet mais avec warnings
        has_warn = any(r.action == PolicyAction.WARN for r in matched_rules)
        if has_warn:
            return PolicyDecision(
                action=PolicyAction.WARN,
                matched_rules=matched_rules,
                reasons=reasons,
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            matched_rules=matched_rules,
            reasons=reasons,
        )

    def _matches(self, rule: PolicyRule, context: dict) -> bool:
        """Vérifie si une règle matche le contexte."""
        for key, expected in rule.conditions.items():
            # Handle plural/singular key mapping (models -> model, apps -> app_id)
            context_key = key
            if key == "models":
                context_key = "model"
            elif key == "apps":
                context_key = "app_id"
            elif key == "environments":
                context_key = "environment"
            elif key == "features":
                context_key = "feature"

            actual = context.get(context_key)

            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

        return True
