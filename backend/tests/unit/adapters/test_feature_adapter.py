"""Tests unitaires pour l'adapter de registre de features.

Ces tests vérifient que InMemoryFeatureAdapter implémente correctement
l'interface FeatureRegistryPort.
"""

import pytest

from backend.adapters.feature import InMemoryFeatureAdapter
from backend.ports.feature_registry import (
    FeatureRegistryPort,
    FeatureDefinition,
    FeatureAction,
    FeatureDecision,
)


# =============================================================================
# Tests InMemoryFeatureAdapter - Basic
# =============================================================================


class TestInMemoryFeatureAdapter:
    """Tests pour l'adapter InMemory."""

    def test_implements_port(self):
        """Vérifie que l'adapter implémente le port."""
        adapter = InMemoryFeatureAdapter()
        assert isinstance(adapter, FeatureRegistryPort)

    @pytest.mark.asyncio
    async def test_no_registry_is_permissive(self):
        """Vérifie qu'une app sans registre est permissive."""
        adapter = InMemoryFeatureAdapter()

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="chat",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.decision == FeatureDecision.ALLOWED_NO_REGISTRY

    @pytest.mark.asyncio
    async def test_register_and_check_feature(self):
        """Vérifie l'enregistrement et la vérification d'une feature."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="customer-support",
            name="Customer Support Chat",
            allowed_actions=[FeatureAction.CHAT],
            allowed_models=["gpt-4", "gpt-3.5-turbo"],
        )

        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="customer-support",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.decision == FeatureDecision.ALLOWED
        assert result.feature_id == "customer-support"


# =============================================================================
# Tests Strict Mode
# =============================================================================


class TestStrictMode:
    """Tests pour le mode strict."""

    @pytest.mark.asyncio
    async def test_strict_mode_denies_unknown_feature(self):
        """Vérifie que le mode strict refuse les features inconnues."""
        adapter = InMemoryFeatureAdapter(default_strict_mode=True)

        # Enregistrer une feature pour activer le mode strict
        feature = FeatureDefinition(
            id="known-feature",
            name="Known Feature",
            allowed_actions=[FeatureAction.CHAT],
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="unknown-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision == FeatureDecision.DENIED_UNKNOWN_FEATURE

    @pytest.mark.asyncio
    async def test_permissive_mode_allows_unknown_feature(self):
        """Vérifie que le mode permissif autorise les features inconnues."""
        adapter = InMemoryFeatureAdapter(default_strict_mode=False)

        feature = FeatureDefinition(
            id="known-feature",
            name="Known Feature",
            allowed_actions=[FeatureAction.CHAT],
        )
        await adapter.register_feature("app-1", feature)
        await adapter.set_strict_mode("app-1", False)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="unknown-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.decision == FeatureDecision.ALLOWED_PERMISSIVE

    @pytest.mark.asyncio
    async def test_strict_mode_no_feature_specified(self):
        """Vérifie que le mode strict refuse si pas de feature spécifiée."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="some-feature",
            name="Some Feature",
            allowed_actions=[FeatureAction.CHAT],
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id=None,  # Pas de feature spécifiée
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision == FeatureDecision.DENIED_NO_FEATURE_SPECIFIED


# =============================================================================
# Tests Default Feature
# =============================================================================


class TestDefaultFeature:
    """Tests pour la feature par défaut."""

    @pytest.mark.asyncio
    async def test_default_feature_used_when_none_specified(self):
        """Vérifie que la feature par défaut est utilisée."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="default-chat",
            name="Default Chat",
            allowed_actions=[FeatureAction.CHAT],
        )
        await adapter.register_feature("app-1", feature)
        await adapter.set_default_feature("app-1", "default-chat")

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id=None,
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.feature_id == "default-chat"


# =============================================================================
# Tests Action Validation
# =============================================================================


class TestActionValidation:
    """Tests pour la validation des actions."""

    @pytest.mark.asyncio
    async def test_allowed_action_passes(self):
        """Vérifie qu'une action autorisée passe."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="chat-feature",
            name="Chat Feature",
            allowed_actions=[FeatureAction.CHAT, FeatureAction.COMPLETION],
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_disallowed_action_denied(self):
        """Vérifie qu'une action non autorisée est refusée."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="chat-only",
            name="Chat Only",
            allowed_actions=[FeatureAction.CHAT],
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="chat-only",
            action=FeatureAction.EMBEDDING,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision == FeatureDecision.DENIED_ACTION_NOT_ALLOWED


# =============================================================================
# Tests Model Validation
# =============================================================================


class TestModelValidation:
    """Tests pour la validation des modèles."""

    @pytest.mark.asyncio
    async def test_allowed_model_passes(self):
        """Vérifie qu'un modèle autorisé passe."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            allowed_models=["gpt-4", "gpt-3.5-turbo"],
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_disallowed_model_denied(self):
        """Vérifie qu'un modèle non autorisé est refusé."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            allowed_models=["gpt-3.5-turbo"],
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision == FeatureDecision.DENIED_MODEL_NOT_ALLOWED

    @pytest.mark.asyncio
    async def test_wildcard_model_matching(self):
        """Vérifie le matching avec wildcards."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            allowed_models=["gpt-*", "claude-*"],
        )
        await adapter.register_feature("app-1", feature)

        # gpt-4 devrait matcher gpt-*
        result1 = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )
        assert result1.allowed is True

        # claude-3-opus devrait matcher claude-*
        result2 = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="claude-3-opus",
            environment="production",
        )
        assert result2.allowed is True

        # llama-2 ne devrait pas matcher
        result3 = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="llama-2",
            environment="production",
        )
        assert result3.allowed is False


# =============================================================================
# Tests Environment Validation
# =============================================================================


class TestEnvironmentValidation:
    """Tests pour la validation des environnements."""

    @pytest.mark.asyncio
    async def test_allowed_environment_passes(self):
        """Vérifie qu'un environnement autorisé passe."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            allowed_environments=["production"],
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_disallowed_environment_denied(self):
        """Vérifie qu'un environnement non autorisé est refusé."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            allowed_environments=["development", "staging"],
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision == FeatureDecision.DENIED_ENVIRONMENT_NOT_ALLOWED


# =============================================================================
# Tests Token/Cost Limits
# =============================================================================


class TestLimits:
    """Tests pour les limites de tokens et coût."""

    @pytest.mark.asyncio
    async def test_token_limit_exceeded(self):
        """Vérifie que le dépassement de tokens est refusé."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            max_tokens_per_request=1000,
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_tokens=1500,
        )

        assert result.allowed is False
        assert result.decision == FeatureDecision.DENIED_TOKEN_LIMIT

    @pytest.mark.asyncio
    async def test_cost_limit_exceeded(self):
        """Vérifie que le dépassement de coût est refusé."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            max_cost_per_request_usd=0.10,
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_cost_usd=0.50,
        )

        assert result.allowed is False
        assert result.decision == FeatureDecision.DENIED_COST_LIMIT


# =============================================================================
# Tests Feature State
# =============================================================================


class TestFeatureState:
    """Tests pour l'état des features."""

    @pytest.mark.asyncio
    async def test_disabled_feature_denied(self):
        """Vérifie qu'une feature désactivée est refusée."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            is_active=False,
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision == FeatureDecision.DENIED_FEATURE_DISABLED


# =============================================================================
# Tests CRUD Operations
# =============================================================================


class TestCRUD:
    """Tests pour les opérations CRUD."""

    @pytest.mark.asyncio
    async def test_get_feature(self):
        """Vérifie la récupération d'une feature."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
        )
        await adapter.register_feature("app-1", feature)

        retrieved = await adapter.get_feature("app-1", "feature-1")

        assert retrieved is not None
        assert retrieved.id == "feature-1"
        assert retrieved.name == "Feature 1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_feature(self):
        """Vérifie la récupération d'une feature inexistante."""
        adapter = InMemoryFeatureAdapter()

        retrieved = await adapter.get_feature("app-1", "nonexistent")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_features(self):
        """Vérifie le listing des features."""
        adapter = InMemoryFeatureAdapter()

        feature1 = FeatureDefinition(
            id="f1", name="F1", allowed_actions=[FeatureAction.CHAT]
        )
        feature2 = FeatureDefinition(
            id="f2", name="F2", allowed_actions=[FeatureAction.EMBEDDING]
        )

        await adapter.register_feature("app-1", feature1)
        await adapter.register_feature("app-1", feature2)

        features = await adapter.list_features("app-1")

        assert len(features) == 2
        ids = {f.id for f in features}
        assert "f1" in ids
        assert "f2" in ids

    @pytest.mark.asyncio
    async def test_remove_feature(self):
        """Vérifie la suppression d'une feature."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
        )
        await adapter.register_feature("app-1", feature)

        removed = await adapter.remove_feature("app-1", "feature-1")
        assert removed is True

        retrieved = await adapter.get_feature("app-1", "feature-1")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_feature(self):
        """Vérifie la suppression d'une feature inexistante."""
        adapter = InMemoryFeatureAdapter()

        removed = await adapter.remove_feature("app-1", "nonexistent")
        assert removed is False


# =============================================================================
# Tests Applied Constraints
# =============================================================================


class TestAppliedConstraints:
    """Tests pour les contraintes appliquées."""

    @pytest.mark.asyncio
    async def test_constraints_returned_on_success(self):
        """Vérifie que les contraintes sont retournées en cas de succès."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            allowed_actions=[FeatureAction.CHAT],
            max_tokens_per_request=1000,
            max_cost_per_request_usd=0.10,
            require_data_separation=True,
            allow_pii=False,
        )
        await adapter.register_feature("app-1", feature)

        result = await adapter.check_feature(
            app_id="app-1",
            feature_id="feature-1",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.applied_constraints["max_tokens"] == 1000
        assert result.applied_constraints["max_cost_usd"] == 0.10
        assert result.applied_constraints["require_data_separation"] is True
        assert result.applied_constraints["pii_blocked"] is True


# =============================================================================
# Tests Test Helpers
# =============================================================================


class TestHelpers:
    """Tests pour les helpers de test."""

    @pytest.mark.asyncio
    async def test_clear_all(self):
        """Vérifie l'effacement de toutes les données."""
        adapter = InMemoryFeatureAdapter()

        feature = FeatureDefinition(
            id="f1", name="F1", allowed_actions=[FeatureAction.CHAT]
        )
        await adapter.register_feature("app-1", feature)
        await adapter.set_strict_mode("app-1", True)

        adapter.clear_all()

        assert adapter.get_feature_count("app-1") == 0

    def test_get_feature_count(self):
        """Vérifie le comptage des features."""
        adapter = InMemoryFeatureAdapter()

        assert adapter.get_feature_count("app-1") == 0

    def test_is_strict_mode(self):
        """Vérifie le helper is_strict_mode."""
        adapter = InMemoryFeatureAdapter(default_strict_mode=True)

        assert adapter.is_strict_mode("app-1") is True
