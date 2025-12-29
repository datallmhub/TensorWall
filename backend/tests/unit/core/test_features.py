"""Comprehensive unit tests for gateway/core/features.py module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.core.features import (
    FeatureAction,
    FeatureDefinition,
    ApplicationFeatureRegistry,
    FeatureValidationResult,
    FeatureEnforcementError,
    FeatureRegistry,
    feature_registry,
    enforce_feature_async,
    enforce_feature,
)


# =============================================================================
# FeatureAction Enum Tests
# =============================================================================


class TestFeatureAction:
    """Tests for FeatureAction enum."""

    def test_all_actions_defined(self):
        """Test that all expected actions are defined."""
        expected_actions = [
            "chat",
            "completion",
            "embedding",
            "summarization",
            "classification",
            "extraction",
            "translation",
            "code_generation",
            "code_review",
            "analysis",
            "custom",
        ]
        for action in expected_actions:
            assert FeatureAction(action) is not None

    def test_action_values(self):
        """Test enum values match string representations."""
        assert FeatureAction.CHAT.value == "chat"
        assert FeatureAction.COMPLETION.value == "completion"
        assert FeatureAction.EMBEDDING.value == "embedding"
        assert FeatureAction.SUMMARIZATION.value == "summarization"
        assert FeatureAction.CLASSIFICATION.value == "classification"
        assert FeatureAction.EXTRACTION.value == "extraction"
        assert FeatureAction.TRANSLATION.value == "translation"
        assert FeatureAction.CODE_GENERATION.value == "code_generation"
        assert FeatureAction.CODE_REVIEW.value == "code_review"
        assert FeatureAction.ANALYSIS.value == "analysis"
        assert FeatureAction.CUSTOM.value == "custom"

    def test_action_is_string_enum(self):
        """Test that FeatureAction is a string enum."""
        assert isinstance(FeatureAction.CHAT, str)
        assert FeatureAction.CHAT == "chat"

    def test_invalid_action_raises(self):
        """Test that invalid action raises ValueError."""
        with pytest.raises(ValueError):
            FeatureAction("invalid_action")


# =============================================================================
# FeatureDefinition Model Tests
# =============================================================================


class TestFeatureDefinition:
    """Tests for FeatureDefinition Pydantic model."""

    def test_create_minimal_feature(self):
        """Test creating a feature with minimal required fields."""
        feature = FeatureDefinition(
            id="test-feature",
            name="Test Feature",
            description="A test feature",
            allowed_actions=[FeatureAction.CHAT],
        )

        assert feature.id == "test-feature"
        assert feature.name == "Test Feature"
        assert feature.description == "A test feature"
        assert FeatureAction.CHAT in feature.allowed_actions

    def test_default_values(self):
        """Test that default values are set correctly."""
        feature = FeatureDefinition(
            id="test-feature",
            name="Test Feature",
            description="A test feature",
            allowed_actions=[FeatureAction.CHAT],
        )

        assert feature.allowed_models == []
        assert feature.max_tokens_per_request is None
        assert feature.max_requests_per_minute is None
        assert feature.max_cost_per_request_usd is None
        assert feature.allowed_environments == ["development", "staging", "production"]
        assert feature.owner is None
        assert feature.is_active is True
        assert feature.allow_pii is False
        assert feature.require_data_separation is True

    def test_create_full_feature(self):
        """Test creating a feature with all fields."""
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        feature = FeatureDefinition(
            id="full-feature",
            name="Full Feature",
            description="A fully configured feature",
            allowed_actions=[FeatureAction.CHAT, FeatureAction.COMPLETION],
            allowed_models=["gpt-4", "gpt-3.5-turbo"],
            max_tokens_per_request=4000,
            max_requests_per_minute=100,
            max_cost_per_request_usd=0.50,
            allowed_environments=["production"],
            owner="team-ai",
            created_at=created_at,
            is_active=True,
            allow_pii=True,
            require_data_separation=False,
        )

        assert feature.id == "full-feature"
        assert feature.allowed_models == ["gpt-4", "gpt-3.5-turbo"]
        assert feature.max_tokens_per_request == 4000
        assert feature.max_requests_per_minute == 100
        assert feature.max_cost_per_request_usd == 0.50
        assert feature.allowed_environments == ["production"]
        assert feature.owner == "team-ai"
        assert feature.created_at == created_at
        assert feature.allow_pii is True
        assert feature.require_data_separation is False

    def test_multiple_actions(self):
        """Test feature with multiple allowed actions."""
        feature = FeatureDefinition(
            id="multi-action-feature",
            name="Multi Action",
            description="Feature with multiple actions",
            allowed_actions=[
                FeatureAction.CHAT,
                FeatureAction.EMBEDDING,
                FeatureAction.SUMMARIZATION,
            ],
        )

        assert len(feature.allowed_actions) == 3
        assert FeatureAction.CHAT in feature.allowed_actions
        assert FeatureAction.EMBEDDING in feature.allowed_actions
        assert FeatureAction.SUMMARIZATION in feature.allowed_actions


# =============================================================================
# ApplicationFeatureRegistry Model Tests
# =============================================================================


class TestApplicationFeatureRegistry:
    """Tests for ApplicationFeatureRegistry Pydantic model."""

    def test_create_minimal_registry(self):
        """Test creating a registry with minimal fields."""
        registry = ApplicationFeatureRegistry(app_id="test-app")

        assert registry.app_id == "test-app"
        assert registry.organization_id is None
        assert registry.features == {}
        assert registry.default_feature_id is None
        assert registry.strict_mode is True

    def test_create_full_registry(self):
        """Test creating a registry with all fields."""
        feature = FeatureDefinition(
            id="chat-feature",
            name="Chat Feature",
            description="Chat feature",
            allowed_actions=[FeatureAction.CHAT],
        )

        registry = ApplicationFeatureRegistry(
            app_id="test-app",
            organization_id="org-123",
            features={"chat-feature": feature},
            default_feature_id="chat-feature",
            strict_mode=False,
        )

        assert registry.app_id == "test-app"
        assert registry.organization_id == "org-123"
        assert "chat-feature" in registry.features
        assert registry.default_feature_id == "chat-feature"
        assert registry.strict_mode is False

    def test_registry_timestamps(self):
        """Test that timestamps are auto-generated."""
        registry = ApplicationFeatureRegistry(app_id="test-app")

        assert registry.created_at is not None
        assert registry.updated_at is not None
        assert isinstance(registry.created_at, datetime)
        assert isinstance(registry.updated_at, datetime)


# =============================================================================
# FeatureValidationResult Model Tests
# =============================================================================


class TestFeatureValidationResult:
    """Tests for FeatureValidationResult Pydantic model."""

    def test_create_allowed_result(self):
        """Test creating an allowed result."""
        result = FeatureValidationResult(
            allowed=True,
            feature_id="test-feature",
            feature_name="Test Feature",
            decision_code="ALLOWED",
            reason="Request allowed",
        )

        assert result.allowed is True
        assert result.feature_id == "test-feature"
        assert result.feature_name == "Test Feature"
        assert result.decision_code == "ALLOWED"
        assert result.reason == "Request allowed"

    def test_create_denied_result(self):
        """Test creating a denied result."""
        result = FeatureValidationResult(
            allowed=False,
            feature_id="test-feature",
            feature_name="Test Feature",
            decision_code="DENIED_ACTION_NOT_ALLOWED",
            reason="Action not allowed for this feature",
            applied_constraints={"max_tokens": 4000},
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_ACTION_NOT_ALLOWED"
        assert result.applied_constraints == {"max_tokens": 4000}

    def test_result_timestamp(self):
        """Test that checked_at timestamp is auto-generated."""
        result = FeatureValidationResult(
            allowed=True,
            decision_code="ALLOWED",
            reason="OK",
        )

        assert result.checked_at is not None
        assert isinstance(result.checked_at, datetime)

    def test_optional_fields(self):
        """Test that optional fields can be None."""
        result = FeatureValidationResult(
            allowed=True,
            decision_code="ALLOWED_NO_REGISTRY",
            reason="No registry configured",
        )

        assert result.feature_id is None
        assert result.feature_name is None
        assert result.applied_constraints == {}


# =============================================================================
# FeatureEnforcementError Tests
# =============================================================================


class TestFeatureEnforcementError:
    """Tests for FeatureEnforcementError exception."""

    def test_create_error(self):
        """Test creating an enforcement error."""
        result = FeatureValidationResult(
            allowed=False,
            feature_id="test-feature",
            decision_code="DENIED_ACTION_NOT_ALLOWED",
            reason="Action 'embedding' is not allowed",
        )

        error = FeatureEnforcementError(result)

        assert error.result is result
        assert str(error) == "Action 'embedding' is not allowed"

    def test_error_is_exception(self):
        """Test that FeatureEnforcementError is an Exception."""
        result = FeatureValidationResult(
            allowed=False,
            decision_code="DENIED",
            reason="Denied",
        )

        error = FeatureEnforcementError(result)

        assert isinstance(error, Exception)

    def test_error_can_be_raised_and_caught(self):
        """Test that error can be raised and caught."""
        result = FeatureValidationResult(
            allowed=False,
            decision_code="DENIED",
            reason="Feature disabled",
        )

        with pytest.raises(FeatureEnforcementError) as exc_info:
            raise FeatureEnforcementError(result)

        assert exc_info.value.result.decision_code == "DENIED"


# =============================================================================
# FeatureRegistry Class Tests
# =============================================================================


class TestFeatureRegistry:
    """Tests for FeatureRegistry class."""

    def test_init(self):
        """Test FeatureRegistry initialization."""
        registry = FeatureRegistry()

        assert registry._registries == {}
        assert registry._loaded_from_db is False

    def test_register_app(self):
        """Test registering an application."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")

        registry.register_app(app_registry)

        assert "test-app" in registry._registries
        assert registry._registries["test-app"] == app_registry

    def test_register_app_updates_timestamp(self):
        """Test that register_app updates the updated_at timestamp."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")
        original_time = app_registry.updated_at

        # Small delay to ensure different timestamp
        import time

        time.sleep(0.01)

        registry.register_app(app_registry)

        assert app_registry.updated_at >= original_time

    def test_get_registry_exists(self):
        """Test getting an existing registry."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")
        registry.register_app(app_registry)

        result = registry.get_registry("test-app")

        assert result is app_registry

    def test_get_registry_not_exists(self):
        """Test getting a non-existent registry."""
        registry = FeatureRegistry()

        result = registry.get_registry("non-existent-app")

        assert result is None

    def test_add_feature_success(self):
        """Test adding a feature to an existing app."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")
        registry.register_app(app_registry)

        feature = FeatureDefinition(
            id="new-feature",
            name="New Feature",
            description="A new feature",
            allowed_actions=[FeatureAction.CHAT],
        )

        result = registry.add_feature("test-app", feature)

        assert result is True
        assert "new-feature" in registry._registries["test-app"].features

    def test_add_feature_app_not_exists(self):
        """Test adding a feature to a non-existent app."""
        registry = FeatureRegistry()

        feature = FeatureDefinition(
            id="new-feature",
            name="New Feature",
            description="A new feature",
            allowed_actions=[FeatureAction.CHAT],
        )

        result = registry.add_feature("non-existent-app", feature)

        assert result is False

    def test_add_feature_updates_timestamp(self):
        """Test that add_feature updates the updated_at timestamp."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")
        registry.register_app(app_registry)
        original_time = app_registry.updated_at

        import time

        time.sleep(0.01)

        feature = FeatureDefinition(
            id="new-feature",
            name="New Feature",
            description="A new feature",
            allowed_actions=[FeatureAction.CHAT],
        )
        registry.add_feature("test-app", feature)

        assert registry._registries["test-app"].updated_at >= original_time

    def test_remove_feature_success(self):
        """Test removing a feature from an app."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="remove-me",
            name="Remove Me",
            description="To be removed",
            allowed_actions=[FeatureAction.CHAT],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"remove-me": feature},
        )
        registry.register_app(app_registry)

        result = registry.remove_feature("test-app", "remove-me")

        assert result is True
        assert "remove-me" not in registry._registries["test-app"].features

    def test_remove_feature_not_exists(self):
        """Test removing a non-existent feature."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")
        registry.register_app(app_registry)

        result = registry.remove_feature("test-app", "non-existent-feature")

        assert result is False

    def test_remove_feature_app_not_exists(self):
        """Test removing a feature from a non-existent app."""
        registry = FeatureRegistry()

        result = registry.remove_feature("non-existent-app", "some-feature")

        assert result is False

    def test_remove_feature_updates_timestamp(self):
        """Test that remove_feature updates the updated_at timestamp."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="remove-me",
            name="Remove Me",
            description="To be removed",
            allowed_actions=[FeatureAction.CHAT],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"remove-me": feature},
        )
        registry.register_app(app_registry)
        original_time = app_registry.updated_at

        import time

        time.sleep(0.01)

        registry.remove_feature("test-app", "remove-me")

        assert registry._registries["test-app"].updated_at >= original_time

    def test_get_feature_constraints_exists(self):
        """Test getting feature constraints."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="test-feature",
            name="Test Feature",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
            max_tokens_per_request=4000,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"test-feature": feature},
        )
        registry.register_app(app_registry)

        result = registry.get_feature_constraints("test-app", "test-feature")

        assert result is feature
        assert result.max_tokens_per_request == 4000

    def test_get_feature_constraints_feature_not_exists(self):
        """Test getting constraints for non-existent feature."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")
        registry.register_app(app_registry)

        result = registry.get_feature_constraints("test-app", "non-existent")

        assert result is None

    def test_get_feature_constraints_app_not_exists(self):
        """Test getting constraints for non-existent app."""
        registry = FeatureRegistry()

        result = registry.get_feature_constraints("non-existent-app", "some-feature")

        assert result is None

    def test_list_features_with_features(self):
        """Test listing features for an app."""
        registry = FeatureRegistry()
        feature1 = FeatureDefinition(
            id="feature-1",
            name="Feature 1",
            description="First",
            allowed_actions=[FeatureAction.CHAT],
        )
        feature2 = FeatureDefinition(
            id="feature-2",
            name="Feature 2",
            description="Second",
            allowed_actions=[FeatureAction.EMBEDDING],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"feature-1": feature1, "feature-2": feature2},
        )
        registry.register_app(app_registry)

        result = registry.list_features("test-app")

        assert len(result) == 2
        assert feature1 in result
        assert feature2 in result

    def test_list_features_no_features(self):
        """Test listing features for an app with no features."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")
        registry.register_app(app_registry)

        result = registry.list_features("test-app")

        assert result == []

    def test_list_features_app_not_exists(self):
        """Test listing features for non-existent app."""
        registry = FeatureRegistry()

        result = registry.list_features("non-existent-app")

        assert result == []


# =============================================================================
# FeatureRegistry Validation Tests
# =============================================================================


class TestFeatureRegistryValidation:
    """Tests for FeatureRegistry.validate_request and _do_validate methods."""

    @pytest.fixture
    def registry_with_feature(self):
        """Create a registry with a configured feature."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="chat-feature",
            name="Chat Feature",
            description="Chat capability",
            allowed_actions=[FeatureAction.CHAT, FeatureAction.COMPLETION],
            allowed_models=["gpt-4", "gpt-3.5-turbo"],
            allowed_environments=["production", "staging"],
            max_tokens_per_request=4000,
            max_cost_per_request_usd=0.10,
            is_active=True,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"chat-feature": feature},
            default_feature_id="chat-feature",
            strict_mode=True,
        )
        registry.register_app(app_registry)
        return registry

    def test_validate_no_registry_permissive(self):
        """Test validation with no registry returns permissive result."""
        registry = FeatureRegistry()

        result = registry.validate_request(
            app_id="unknown-app",
            feature_id="some-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.decision_code == "ALLOWED_NO_REGISTRY"

    def test_validate_no_feature_strict_mode_denied(self):
        """Test validation without feature in strict mode is denied."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            strict_mode=True,
            default_feature_id=None,
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id=None,
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_NO_FEATURE_SPECIFIED"

    def test_validate_no_feature_permissive_mode_allowed(self):
        """Test validation without feature in permissive mode is allowed."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            strict_mode=False,
            default_feature_id=None,
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id=None,
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.decision_code == "ALLOWED_PERMISSIVE_MODE"

    def test_validate_empty_feature_uses_default(self, registry_with_feature):
        """Test that empty feature ID uses default feature."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.feature_id == "chat-feature"

    def test_validate_unknown_feature_uses_default(self, registry_with_feature):
        """Test that 'unknown' feature ID uses default feature."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="unknown",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.feature_id == "chat-feature"

    def test_validate_unknown_feature_strict_mode_denied(self):
        """Test validation with unknown feature in strict mode is denied."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            strict_mode=True,
            default_feature_id=None,
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id="non-existent-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_UNKNOWN_FEATURE"
        assert "non-existent-feature" in result.reason

    def test_validate_unknown_feature_permissive_allowed(self):
        """Test validation with unknown feature in permissive mode is allowed."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            strict_mode=False,
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id="non-existent-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.decision_code == "ALLOWED_UNKNOWN_FEATURE_PERMISSIVE"

    def test_validate_feature_disabled_denied(self):
        """Test validation with disabled feature is denied."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="disabled-feature",
            name="Disabled Feature",
            description="Disabled",
            allowed_actions=[FeatureAction.CHAT],
            is_active=False,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"disabled-feature": feature},
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id="disabled-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_FEATURE_DISABLED"

    def test_validate_action_not_allowed_denied(self, registry_with_feature):
        """Test validation with disallowed action is denied."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.EMBEDDING,  # Not in allowed_actions
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_ACTION_NOT_ALLOWED"
        assert "embedding" in result.reason

    def test_validate_action_allowed(self, registry_with_feature):
        """Test validation with allowed action succeeds."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True

    def test_validate_model_not_allowed_denied(self, registry_with_feature):
        """Test validation with disallowed model is denied."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="claude-3-opus",  # Not in allowed_models
            environment="production",
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_MODEL_NOT_ALLOWED"

    def test_validate_model_allowed(self, registry_with_feature):
        """Test validation with allowed model succeeds."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True

    def test_validate_no_model_restriction(self):
        """Test validation when no model restriction is set."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="any-model-feature",
            name="Any Model",
            description="No model restriction",
            allowed_actions=[FeatureAction.CHAT],
            allowed_models=[],  # Empty = any model allowed
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"any-model-feature": feature},
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id="any-model-feature",
            action=FeatureAction.CHAT,
            model="any-model",
            environment="production",
        )

        assert result.allowed is True

    def test_validate_environment_not_allowed_denied(self, registry_with_feature):
        """Test validation with disallowed environment is denied."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="development",  # Not in allowed_environments
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_ENVIRONMENT_NOT_ALLOWED"

    def test_validate_environment_allowed(self, registry_with_feature):
        """Test validation with allowed environment succeeds."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="staging",
        )

        assert result.allowed is True

    def test_validate_token_limit_exceeded_denied(self, registry_with_feature):
        """Test validation with token limit exceeded is denied."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_tokens=5000,  # Exceeds 4000 limit
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_TOKEN_LIMIT_EXCEEDED"
        assert "5000" in result.reason
        assert result.applied_constraints["max_tokens"] == 4000

    def test_validate_token_limit_within_allowed(self, registry_with_feature):
        """Test validation with tokens within limit succeeds."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_tokens=3000,  # Within 4000 limit
        )

        assert result.allowed is True

    def test_validate_no_token_estimate_allowed(self, registry_with_feature):
        """Test validation without token estimate succeeds."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_tokens=None,
        )

        assert result.allowed is True

    def test_validate_cost_limit_exceeded_denied(self, registry_with_feature):
        """Test validation with cost limit exceeded is denied."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_cost_usd=0.50,  # Exceeds 0.10 limit
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_COST_LIMIT_EXCEEDED"
        assert result.applied_constraints["max_cost_usd"] == 0.10

    def test_validate_cost_limit_within_allowed(self, registry_with_feature):
        """Test validation with cost within limit succeeds."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_cost_usd=0.05,
        )

        assert result.allowed is True

    def test_validate_no_cost_estimate_allowed(self, registry_with_feature):
        """Test validation without cost estimate succeeds."""
        result = registry_with_feature.validate_request(
            app_id="test-app",
            feature_id="chat-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_cost_usd=None,
        )

        assert result.allowed is True

    def test_validate_allowed_includes_constraints(self):
        """Test that allowed result includes applied constraints."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="constrained-feature",
            name="Constrained",
            description="With constraints",
            allowed_actions=[FeatureAction.CHAT],
            max_tokens_per_request=4000,
            max_requests_per_minute=100,
            max_cost_per_request_usd=0.50,
            require_data_separation=True,
            allow_pii=False,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"constrained-feature": feature},
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id="constrained-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.decision_code == "ALLOWED"
        assert result.applied_constraints["max_tokens"] == 4000
        assert result.applied_constraints["max_rpm"] == 100
        assert result.applied_constraints["max_cost_usd"] == 0.50
        assert result.applied_constraints["require_data_separation"] is True
        assert result.applied_constraints["pii_blocked"] is True


# =============================================================================
# FeatureRegistry Async Tests
# =============================================================================


class TestFeatureRegistryAsync:
    """Tests for async methods of FeatureRegistry."""

    @pytest.mark.asyncio
    async def test_get_registry_async_cached(self):
        """Test get_registry_async returns cached registry."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(app_id="test-app")
        registry.register_app(app_registry)

        result = await registry.get_registry_async("test-app")

        assert result is app_registry

    @pytest.mark.asyncio
    async def test_get_registry_async_loads_from_db(self):
        """Test get_registry_async loads from DB when not cached."""
        registry = FeatureRegistry()

        with patch.object(registry, "load_from_db", new_callable=AsyncMock) as mock_load:
            mock_registry = ApplicationFeatureRegistry(app_id="new-app")
            mock_load.return_value = mock_registry

            await registry.get_registry_async("new-app")

            mock_load.assert_called_once_with("new-app")

    @pytest.mark.asyncio
    async def test_validate_request_async(self):
        """Test async validation."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="async-feature",
            name="Async Feature",
            description="For async test",
            allowed_actions=[FeatureAction.CHAT],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"async-feature": feature},
        )
        registry.register_app(app_registry)

        result = await registry.validate_request_async(
            app_id="test-app",
            feature_id="async-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True


# =============================================================================
# Load from DB Tests
# =============================================================================


class TestFeatureRegistryLoadFromDb:
    """Tests for FeatureRegistry.load_from_db method."""

    @pytest.mark.asyncio
    async def test_load_from_db_no_features(self):
        """Test loading when no features exist returns permissive registry."""
        registry = FeatureRegistry()

        mock_db_context = AsyncMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        mock_db_context.__aenter__.return_value = mock_db
        mock_db_context.__aexit__.return_value = None

        with patch("backend.db.session.get_db_context", return_value=mock_db_context):
            result = await registry.load_from_db("test-app")

        assert result is not None
        assert result.app_id == "test-app"
        assert result.strict_mode is False
        assert result.features == {}

    @pytest.mark.asyncio
    async def test_load_from_db_with_features(self):
        """Test loading features from database."""
        registry = FeatureRegistry()

        # Create mock DB feature
        mock_feature = MagicMock()
        mock_feature.feature_id = "db-feature"
        mock_feature.name = "DB Feature"
        mock_feature.description = "From database"
        mock_feature.allowed_actions = ["chat", "completion"]
        mock_feature.allowed_models = ["gpt-4"]
        mock_feature.max_tokens_per_request = 4000
        mock_feature.max_cost_per_request = 0.10
        mock_feature.allowed_environments = ["production"]
        mock_feature.is_enabled = True
        mock_feature.require_contract = True

        mock_db_context = AsyncMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_feature]
        mock_db.execute.return_value = mock_result

        mock_db_context.__aenter__.return_value = mock_db
        mock_db_context.__aexit__.return_value = None

        with patch("backend.db.session.get_db_context", return_value=mock_db_context):
            result = await registry.load_from_db("test-app")

        assert result is not None
        assert result.app_id == "test-app"
        assert result.strict_mode is True
        assert "db-feature" in result.features
        assert result.default_feature_id == "db-feature"

        feature = result.features["db-feature"]
        assert feature.name == "DB Feature"
        assert FeatureAction.CHAT in feature.allowed_actions
        assert FeatureAction.COMPLETION in feature.allowed_actions

    @pytest.mark.asyncio
    async def test_load_from_db_invalid_action_skipped(self):
        """Test that invalid actions are skipped during load."""
        registry = FeatureRegistry()

        mock_feature = MagicMock()
        mock_feature.feature_id = "db-feature"
        mock_feature.name = "DB Feature"
        mock_feature.description = "Test"
        mock_feature.allowed_actions = ["chat", "invalid_action", "completion"]
        mock_feature.allowed_models = []
        mock_feature.max_tokens_per_request = None
        mock_feature.max_cost_per_request = None
        mock_feature.allowed_environments = ["production"]
        mock_feature.is_enabled = True
        mock_feature.require_contract = False

        mock_db_context = AsyncMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_feature]
        mock_db.execute.return_value = mock_result

        mock_db_context.__aenter__.return_value = mock_db
        mock_db_context.__aexit__.return_value = None

        with patch("backend.db.session.get_db_context", return_value=mock_db_context):
            result = await registry.load_from_db("test-app")

        feature = result.features["db-feature"]
        # Only valid actions should be included
        assert len(feature.allowed_actions) == 2
        assert FeatureAction.CHAT in feature.allowed_actions
        assert FeatureAction.COMPLETION in feature.allowed_actions

    @pytest.mark.asyncio
    async def test_load_from_db_exception_returns_permissive(self):
        """Test that DB exception returns permissive registry."""
        registry = FeatureRegistry()

        with patch("backend.db.session.get_db_context", side_effect=Exception("DB error")):
            result = await registry.load_from_db("test-app")

        assert result is not None
        assert result.app_id == "test-app"
        assert result.strict_mode is False

    @pytest.mark.asyncio
    async def test_load_from_db_caches_result(self):
        """Test that load_from_db caches the result."""
        registry = FeatureRegistry()

        mock_db_context = AsyncMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        mock_db_context.__aenter__.return_value = mock_db
        mock_db_context.__aexit__.return_value = None

        with patch("backend.db.session.get_db_context", return_value=mock_db_context):
            await registry.load_from_db("test-app")

        assert "test-app" in registry._registries

    @pytest.mark.asyncio
    async def test_load_from_db_default_feature_with_chat(self):
        """Test that first feature with chat action becomes default."""
        registry = FeatureRegistry()

        # First feature without chat
        mock_feature1 = MagicMock()
        mock_feature1.feature_id = "embedding-feature"
        mock_feature1.name = "Embedding"
        mock_feature1.description = "Embeddings only"
        mock_feature1.allowed_actions = ["embedding"]
        mock_feature1.allowed_models = []
        mock_feature1.max_tokens_per_request = None
        mock_feature1.max_cost_per_request = None
        mock_feature1.allowed_environments = ["production"]
        mock_feature1.is_enabled = True
        mock_feature1.require_contract = False

        # Second feature with chat
        mock_feature2 = MagicMock()
        mock_feature2.feature_id = "chat-feature"
        mock_feature2.name = "Chat"
        mock_feature2.description = "Chat feature"
        mock_feature2.allowed_actions = ["chat"]
        mock_feature2.allowed_models = []
        mock_feature2.max_tokens_per_request = None
        mock_feature2.max_cost_per_request = None
        mock_feature2.allowed_environments = ["production"]
        mock_feature2.is_enabled = True
        mock_feature2.require_contract = False

        mock_db_context = AsyncMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_feature1, mock_feature2]
        mock_db.execute.return_value = mock_result

        mock_db_context.__aenter__.return_value = mock_db
        mock_db_context.__aexit__.return_value = None

        with patch("backend.db.session.get_db_context", return_value=mock_db_context):
            result = await registry.load_from_db("test-app")

        assert result.default_feature_id == "chat-feature"

    @pytest.mark.asyncio
    async def test_load_from_db_null_allowed_actions(self):
        """Test loading when allowed_actions is None."""
        registry = FeatureRegistry()

        mock_feature = MagicMock()
        mock_feature.feature_id = "null-actions"
        mock_feature.name = "Null Actions"
        mock_feature.description = "Test"
        mock_feature.allowed_actions = None  # None instead of list
        mock_feature.allowed_models = None
        mock_feature.max_tokens_per_request = None
        mock_feature.max_cost_per_request = None
        mock_feature.allowed_environments = None
        mock_feature.is_enabled = True
        mock_feature.require_contract = False

        mock_db_context = AsyncMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_feature]
        mock_db.execute.return_value = mock_result

        mock_db_context.__aenter__.return_value = mock_db
        mock_db_context.__aexit__.return_value = None

        with patch("backend.db.session.get_db_context", return_value=mock_db_context):
            result = await registry.load_from_db("test-app")

        assert result is not None
        feature = result.features["null-actions"]
        assert feature.allowed_actions == []
        assert feature.allowed_models == []
        assert feature.allowed_environments == ["development", "staging", "production"]


# =============================================================================
# Enforce Feature Tests
# =============================================================================


class TestEnforceFeature:
    """Tests for enforce_feature and enforce_feature_async functions."""

    def test_enforce_feature_allowed(self):
        """Test enforce_feature returns result when allowed."""
        # Clear and set up the singleton registry
        feature_registry._registries.clear()

        feature = FeatureDefinition(
            id="test-feature",
            name="Test Feature",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"test-feature": feature},
        )
        feature_registry.register_app(app_registry)

        result = enforce_feature(
            app_id="test-app",
            feature_id="test-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True

    def test_enforce_feature_denied_raises(self):
        """Test enforce_feature raises error when denied."""
        feature_registry._registries.clear()

        feature = FeatureDefinition(
            id="test-feature",
            name="Test Feature",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
            is_active=False,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"test-feature": feature},
        )
        feature_registry.register_app(app_registry)

        with pytest.raises(FeatureEnforcementError) as exc_info:
            enforce_feature(
                app_id="test-app",
                feature_id="test-feature",
                action=FeatureAction.CHAT,
                model="gpt-4",
                environment="production",
            )

        assert exc_info.value.result.decision_code == "DENIED_FEATURE_DISABLED"

    @pytest.mark.asyncio
    async def test_enforce_feature_async_allowed(self):
        """Test enforce_feature_async returns result when allowed."""
        feature_registry._registries.clear()

        feature = FeatureDefinition(
            id="async-feature",
            name="Async Feature",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"async-feature": feature},
        )
        feature_registry.register_app(app_registry)

        result = await enforce_feature_async(
            app_id="test-app",
            feature_id="async-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_enforce_feature_async_denied_raises(self):
        """Test enforce_feature_async raises error when denied."""
        feature_registry._registries.clear()

        feature = FeatureDefinition(
            id="async-feature",
            name="Async Feature",
            description="Test",
            allowed_actions=[FeatureAction.EMBEDDING],  # Not chat
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"async-feature": feature},
        )
        feature_registry.register_app(app_registry)

        with pytest.raises(FeatureEnforcementError) as exc_info:
            await enforce_feature_async(
                app_id="test-app",
                feature_id="async-feature",
                action=FeatureAction.CHAT,
                model="gpt-4",
                environment="production",
            )

        assert exc_info.value.result.decision_code == "DENIED_ACTION_NOT_ALLOWED"

    def test_enforce_feature_with_tokens(self):
        """Test enforce_feature with token estimation."""
        feature_registry._registries.clear()

        feature = FeatureDefinition(
            id="token-feature",
            name="Token Feature",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
            max_tokens_per_request=1000,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"token-feature": feature},
        )
        feature_registry.register_app(app_registry)

        with pytest.raises(FeatureEnforcementError) as exc_info:
            enforce_feature(
                app_id="test-app",
                feature_id="token-feature",
                action=FeatureAction.CHAT,
                model="gpt-4",
                environment="production",
                estimated_tokens=2000,
            )

        assert exc_info.value.result.decision_code == "DENIED_TOKEN_LIMIT_EXCEEDED"

    def test_enforce_feature_with_cost(self):
        """Test enforce_feature with cost estimation."""
        feature_registry._registries.clear()

        feature = FeatureDefinition(
            id="cost-feature",
            name="Cost Feature",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
            max_cost_per_request_usd=0.01,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"cost-feature": feature},
        )
        feature_registry.register_app(app_registry)

        with pytest.raises(FeatureEnforcementError) as exc_info:
            enforce_feature(
                app_id="test-app",
                feature_id="cost-feature",
                action=FeatureAction.CHAT,
                model="gpt-4",
                environment="production",
                estimated_cost_usd=0.50,
            )

        assert exc_info.value.result.decision_code == "DENIED_COST_LIMIT_EXCEEDED"


# =============================================================================
# Singleton Tests
# =============================================================================


class TestFeatureRegistrySingleton:
    """Tests for feature_registry singleton."""

    def test_singleton_exists(self):
        """Test that feature_registry singleton is available."""
        from backend.core.features import feature_registry as singleton

        assert singleton is not None
        assert isinstance(singleton, FeatureRegistry)

    def test_singleton_is_same_instance(self):
        """Test that importing returns same instance."""
        from backend.core.features import feature_registry as singleton1
        from backend.core.features import feature_registry as singleton2

        assert singleton1 is singleton2


# =============================================================================
# Model Pattern Matching Tests
# =============================================================================


class TestModelPatternMatching:
    """Tests for model pattern matching in feature validation."""

    def test_exact_model_match(self):
        """Test exact model matching."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="exact-model",
            name="Exact Model",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
            allowed_models=["gpt-4-turbo"],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"exact-model": feature},
        )
        registry.register_app(app_registry)

        # Exact match should work
        result = registry.validate_request(
            app_id="test-app",
            feature_id="exact-model",
            action=FeatureAction.CHAT,
            model="gpt-4-turbo",
            environment="production",
        )
        assert result.allowed is True

        # Similar but different model should fail
        result = registry.validate_request(
            app_id="test-app",
            feature_id="exact-model",
            action=FeatureAction.CHAT,
            model="gpt-4-turbo-preview",
            environment="production",
        )
        assert result.allowed is False

    def test_wildcard_model_match(self):
        """Test wildcard model matching."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="wildcard-model",
            name="Wildcard Model",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
            allowed_models=["gpt-*", "claude-*"],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"wildcard-model": feature},
        )
        registry.register_app(app_registry)

        # Should match gpt- prefix
        result = registry.validate_request(
            app_id="test-app",
            feature_id="wildcard-model",
            action=FeatureAction.CHAT,
            model="gpt-4-turbo",
            environment="production",
        )
        assert result.allowed is True

        # Should match claude- prefix
        result = registry.validate_request(
            app_id="test-app",
            feature_id="wildcard-model",
            action=FeatureAction.CHAT,
            model="claude-3-opus",
            environment="production",
        )
        assert result.allowed is True

        # Should not match other prefixes
        result = registry.validate_request(
            app_id="test-app",
            feature_id="wildcard-model",
            action=FeatureAction.CHAT,
            model="llama-2-70b",
            environment="production",
        )
        assert result.allowed is False


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_none_feature_id_in_strict_mode(self):
        """Test None feature_id in strict mode without default."""
        registry = FeatureRegistry()
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            strict_mode=True,
            default_feature_id=None,
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id=None,
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is False
        assert result.decision_code == "DENIED_NO_FEATURE_SPECIFIED"

    def test_empty_string_feature_id(self):
        """Test empty string feature_id uses default."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="default-feature",
            name="Default",
            description="Default feature",
            allowed_actions=[FeatureAction.CHAT],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"default-feature": feature},
            default_feature_id="default-feature",
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id="",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        assert result.feature_id == "default-feature"

    def test_validation_result_reason_contains_details(self):
        """Test that denied results contain helpful error details."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="test-feature",
            name="Test Feature",
            description="Test",
            allowed_actions=[FeatureAction.EMBEDDING],
            allowed_models=["text-embedding-ada-002"],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"test-feature": feature},
        )
        registry.register_app(app_registry)

        # Test action mismatch error details
        result = registry.validate_request(
            app_id="test-app",
            feature_id="test-feature",
            action=FeatureAction.CHAT,
            model="text-embedding-ada-002",
            environment="production",
        )

        assert "chat" in result.reason.lower()
        assert "embedding" in result.reason.lower()

    def test_feature_with_all_environments(self):
        """Test feature with all default environments."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="all-env-feature",
            name="All Environments",
            description="Test",
            allowed_actions=[FeatureAction.CHAT],
            # Default: ["development", "staging", "production"]
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"all-env-feature": feature},
        )
        registry.register_app(app_registry)

        for env in ["development", "staging", "production"]:
            result = registry.validate_request(
                app_id="test-app",
                feature_id="all-env-feature",
                action=FeatureAction.CHAT,
                model="gpt-4",
                environment=env,
            )
            assert result.allowed is True, f"Should be allowed in {env}"

    def test_feature_with_pii_settings(self):
        """Test feature with PII settings."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="pii-feature",
            name="PII Feature",
            description="With PII settings",
            allowed_actions=[FeatureAction.CHAT],
            allow_pii=True,
            require_data_separation=False,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"pii-feature": feature},
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="test-app",
            feature_id="pii-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
        # No pii_blocked constraint when allow_pii is True
        assert "pii_blocked" not in result.applied_constraints
        # No require_data_separation when it's False
        assert "require_data_separation" not in result.applied_constraints

    def test_multiple_features_in_registry(self):
        """Test registry with multiple features."""
        registry = FeatureRegistry()
        feature1 = FeatureDefinition(
            id="chat-feature",
            name="Chat",
            description="Chat",
            allowed_actions=[FeatureAction.CHAT],
        )
        feature2 = FeatureDefinition(
            id="embed-feature",
            name="Embed",
            description="Embed",
            allowed_actions=[FeatureAction.EMBEDDING],
        )
        feature3 = FeatureDefinition(
            id="code-feature",
            name="Code",
            description="Code",
            allowed_actions=[FeatureAction.CODE_GENERATION, FeatureAction.CODE_REVIEW],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={
                "chat-feature": feature1,
                "embed-feature": feature2,
                "code-feature": feature3,
            },
        )
        registry.register_app(app_registry)

        # Validate each feature with correct action
        assert (
            registry.validate_request(
                app_id="test-app",
                feature_id="chat-feature",
                action=FeatureAction.CHAT,
                model="gpt-4",
                environment="production",
            ).allowed
            is True
        )

        assert (
            registry.validate_request(
                app_id="test-app",
                feature_id="embed-feature",
                action=FeatureAction.EMBEDDING,
                model="gpt-4",
                environment="production",
            ).allowed
            is True
        )

        assert (
            registry.validate_request(
                app_id="test-app",
                feature_id="code-feature",
                action=FeatureAction.CODE_GENERATION,
                model="gpt-4",
                environment="production",
            ).allowed
            is True
        )

        # Cross-feature action should fail
        assert (
            registry.validate_request(
                app_id="test-app",
                feature_id="chat-feature",
                action=FeatureAction.EMBEDDING,
                model="gpt-4",
                environment="production",
            ).allowed
            is False
        )


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestFeatureValidationFlow:
    """Integration-style tests for complete validation flows."""

    def test_complete_allowed_flow(self):
        """Test complete flow for an allowed request."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="production-chat",
            name="Production Chat",
            description="Production chat capability",
            allowed_actions=[FeatureAction.CHAT, FeatureAction.COMPLETION],
            allowed_models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            allowed_environments=["production"],
            max_tokens_per_request=8000,
            max_cost_per_request_usd=1.00,
            is_active=True,
            require_data_separation=True,
            allow_pii=False,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="prod-app",
            features={"production-chat": feature},
            default_feature_id="production-chat",
            strict_mode=True,
        )
        registry.register_app(app_registry)

        result = registry.validate_request(
            app_id="prod-app",
            feature_id="production-chat",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
            estimated_tokens=4000,
            estimated_cost_usd=0.50,
        )

        assert result.allowed is True
        assert result.decision_code == "ALLOWED"
        assert result.feature_id == "production-chat"
        assert result.feature_name == "Production Chat"
        assert result.applied_constraints["max_tokens"] == 8000
        assert result.applied_constraints["max_cost_usd"] == 1.00
        assert result.applied_constraints["pii_blocked"] is True
        assert result.applied_constraints["require_data_separation"] is True

    def test_complete_denied_flow_multiple_violations(self):
        """Test that first violation is returned when multiple violations exist."""
        registry = FeatureRegistry()
        feature = FeatureDefinition(
            id="restricted-feature",
            name="Restricted",
            description="Highly restricted",
            allowed_actions=[FeatureAction.EMBEDDING],
            allowed_models=["text-embedding-ada-002"],
            allowed_environments=["staging"],
            max_tokens_per_request=100,
            is_active=True,
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="test-app",
            features={"restricted-feature": feature},
        )
        registry.register_app(app_registry)

        # Multiple violations: wrong action, wrong model, wrong env, too many tokens
        result = registry.validate_request(
            app_id="test-app",
            feature_id="restricted-feature",
            action=FeatureAction.CHAT,  # Wrong
            model="gpt-4",  # Wrong
            environment="production",  # Wrong
            estimated_tokens=1000,  # Too many
        )

        # Should fail on first check (action)
        assert result.allowed is False
        assert result.decision_code == "DENIED_ACTION_NOT_ALLOWED"

    @pytest.mark.asyncio
    async def test_async_flow_with_db_load(self):
        """Test async flow that would load from DB."""
        registry = FeatureRegistry()

        # Pre-register an app (simulating DB load)
        feature = FeatureDefinition(
            id="db-loaded-feature",
            name="DB Loaded",
            description="From DB",
            allowed_actions=[FeatureAction.CHAT],
        )
        app_registry = ApplicationFeatureRegistry(
            app_id="db-app",
            features={"db-loaded-feature": feature},
        )
        registry.register_app(app_registry)

        # Async validation should use cached registry
        result = await registry.validate_request_async(
            app_id="db-app",
            feature_id="db-loaded-feature",
            action=FeatureAction.CHAT,
            model="gpt-4",
            environment="production",
        )

        assert result.allowed is True
