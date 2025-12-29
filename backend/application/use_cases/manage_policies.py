"""Manage Policies Use Case.

Architecture Hexagonale: Use Cases pour la gestion CRUD des policies.
"""

from dataclasses import dataclass, field
from typing import Any

from backend.domain.models import PolicyRule, PolicyAction
from backend.ports.policy_repository import PolicyRepositoryPort


@dataclass
class PolicyDTO:
    """DTO pour les policies."""

    id: str
    name: str
    action: str
    priority: int
    conditions: dict[str, Any]
    enabled: bool


@dataclass
class CreatePolicyCommand:
    """Command pour créer une policy."""

    name: str
    action: str
    priority: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)
    app_id: str | None = None
    org_id: str | None = None


@dataclass
class UpdatePolicyCommand:
    """Command pour mettre à jour une policy."""

    policy_id: str
    name: str | None = None
    action: str | None = None
    priority: int | None = None
    conditions: dict[str, Any] | None = None
    enabled: bool | None = None


class ManagePoliciesUseCase:
    """Use Case: Gérer les policies (CRUD).

    Orchestration simple pour les opérations CRUD sur les policies.
    """

    def __init__(self, policy_repository: PolicyRepositoryPort):
        self.policy_repository = policy_repository

    def _to_dto(self, rule: PolicyRule) -> PolicyDTO:
        """Convertit une PolicyRule en DTO."""
        return PolicyDTO(
            id=rule.id,
            name=rule.name,
            action=rule.action.value,
            priority=rule.priority,
            conditions=rule.conditions,
            enabled=rule.enabled,
        )

    async def list_policies(
        self,
        app_id: str | None = None,
        org_id: str | None = None,
        environment: str | None = None,
    ) -> list[PolicyDTO]:
        """Liste les policies."""
        rules = await self.policy_repository.get_active_rules(
            org_id=org_id,
            app_id=app_id,
            environment=environment,
        )
        return [self._to_dto(rule) for rule in rules]

    async def get_policy(self, policy_id: str) -> PolicyDTO | None:
        """Récupère une policy par ID."""
        rule = await self.policy_repository.get_rule_by_id(policy_id)
        if not rule:
            return None
        return self._to_dto(rule)

    async def create_policy(self, command: CreatePolicyCommand) -> PolicyDTO:
        """Crée une nouvelle policy."""
        rule = PolicyRule(
            id="",  # Sera généré par le repository
            name=command.name,
            action=PolicyAction(command.action),
            priority=command.priority,
            conditions=command.conditions,
            enabled=True,
        )
        created = await self.policy_repository.create_rule(rule)
        return self._to_dto(created)

    async def update_policy(self, command: UpdatePolicyCommand) -> PolicyDTO | None:
        """Met à jour une policy."""
        existing = await self.policy_repository.get_rule_by_id(command.policy_id)
        if not existing:
            return None

        # Mettre à jour les champs fournis
        if command.name is not None:
            existing.name = command.name
        if command.action is not None:
            existing.action = PolicyAction(command.action)
        if command.priority is not None:
            existing.priority = command.priority
        if command.conditions is not None:
            existing.conditions = command.conditions
        if command.enabled is not None:
            existing.enabled = command.enabled

        updated = await self.policy_repository.update_rule(existing)
        return self._to_dto(updated)

    async def delete_policy(self, policy_id: str) -> bool:
        """Supprime une policy."""
        return await self.policy_repository.delete_rule(policy_id)
