"""Unit tests for Environment Isolation System."""

from backend.core.environments import (
    Environment,
    EnvironmentConfig,
    DEFAULT_ENVIRONMENTS,
)


class TestEnvironment:
    """Tests for Environment enum."""

    def test_valid_environments(self):
        """Test all valid environments."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"
        assert Environment.SANDBOX == "sandbox"

    def test_from_string(self):
        """Test creating environment from string."""
        env = Environment("production")
        assert env == Environment.PRODUCTION


class TestEnvironmentConfig:
    """Tests for EnvironmentConfig model."""

    def test_create_minimal(self):
        """Test creating config with minimal fields."""
        config = EnvironmentConfig(
            name=Environment.DEVELOPMENT,
            display_name="Dev",
        )

        assert config.name == Environment.DEVELOPMENT
        assert config.strict_mode is False
        assert config.allowed_models == []

    def test_create_production(self):
        """Test creating production config."""
        config = EnvironmentConfig(
            name=Environment.PRODUCTION,
            display_name="Production",
            strict_mode=True,
            allow_debug_mode=False,
            require_contracts=True,
            pii_detection_enabled=True,
            security_scan_level="strict",
        )

        assert config.strict_mode is True
        assert config.allow_debug_mode is False
        assert config.security_scan_level == "strict"

    def test_allowed_source_ips_default(self):
        """Test that allowed_source_ips is empty by default."""
        config = EnvironmentConfig(
            name=Environment.DEVELOPMENT,
            display_name="Dev",
        )

        assert config.allowed_source_ips == []

    def test_budget_multiplier_default(self):
        """Test default budget multiplier."""
        config = EnvironmentConfig(
            name=Environment.DEVELOPMENT,
            display_name="Dev",
        )

        assert config.default_budget_multiplier == 1.0


class TestDefaultEnvironments:
    """Tests for DEFAULT_ENVIRONMENTS."""

    def test_all_environments_have_defaults(self):
        """Test that all standard environments have defaults."""
        assert Environment.DEVELOPMENT in DEFAULT_ENVIRONMENTS
        assert Environment.STAGING in DEFAULT_ENVIRONMENTS
        assert Environment.PRODUCTION in DEFAULT_ENVIRONMENTS
        assert Environment.SANDBOX in DEFAULT_ENVIRONMENTS

    def test_development_config(self):
        """Test development environment configuration."""
        config = DEFAULT_ENVIRONMENTS[Environment.DEVELOPMENT]

        assert config.strict_mode is False
        assert config.allow_debug_mode is True
        assert config.require_contracts is False
        assert config.pii_detection_enabled is False
        assert config.allow_experimental_features is True
        assert config.default_budget_multiplier == 0.1  # 10%

    def test_staging_config(self):
        """Test staging environment configuration."""
        config = DEFAULT_ENVIRONMENTS[Environment.STAGING]

        assert config.strict_mode is True
        assert config.allow_debug_mode is True
        assert config.require_contracts is True
        assert config.pii_detection_enabled is True
        assert config.security_scan_level == "standard"
        assert config.default_budget_multiplier == 0.5  # 50%

    def test_production_config(self):
        """Test production environment configuration."""
        config = DEFAULT_ENVIRONMENTS[Environment.PRODUCTION]

        assert config.strict_mode is True
        assert config.allow_debug_mode is False
        assert config.require_contracts is True
        assert config.pii_detection_enabled is True
        assert config.security_scan_level == "strict"
        assert config.log_prompts is False  # Privacy
        assert config.log_responses is False  # Privacy
        assert config.default_budget_multiplier == 1.0  # Full budget

    def test_sandbox_config(self):
        """Test sandbox environment configuration."""
        config = DEFAULT_ENVIRONMENTS[Environment.SANDBOX]

        assert config.allow_experimental_features is True
        assert config.audit_all_requests is False


class TestSecuritySettings:
    """Tests for security-related environment settings."""

    def test_production_has_strict_security(self):
        """Test that production has strictest security."""
        prod_config = DEFAULT_ENVIRONMENTS[Environment.PRODUCTION]
        dev_config = DEFAULT_ENVIRONMENTS[Environment.DEVELOPMENT]

        # Production should have stricter security
        assert prod_config.security_scan_level == "strict"
        assert dev_config.security_scan_level == "minimal"

        # Production should have all detection enabled
        assert prod_config.pii_detection_enabled is True
        assert prod_config.prompt_injection_detection is True

    def test_development_has_relaxed_security(self):
        """Test that development has relaxed security for easier testing."""
        config = DEFAULT_ENVIRONMENTS[Environment.DEVELOPMENT]

        assert config.pii_detection_enabled is False
        assert config.security_scan_level == "minimal"


class TestBudgetSettings:
    """Tests for budget-related environment settings."""

    def test_budget_multipliers_scale_correctly(self):
        """Test that budget multipliers scale from dev to prod."""
        dev_mult = DEFAULT_ENVIRONMENTS[
            Environment.DEVELOPMENT
        ].default_budget_multiplier
        staging_mult = DEFAULT_ENVIRONMENTS[
            Environment.STAGING
        ].default_budget_multiplier
        prod_mult = DEFAULT_ENVIRONMENTS[
            Environment.PRODUCTION
        ].default_budget_multiplier

        # Should scale up: dev < staging < prod
        assert dev_mult < staging_mult < prod_mult


class TestModelAccess:
    """Tests for model access control."""

    def test_default_allows_all_models(self):
        """Test that default config allows all models."""
        config = EnvironmentConfig(
            name=Environment.DEVELOPMENT,
            display_name="Dev",
        )

        assert config.allowed_models == []  # Empty = all allowed
        assert config.blocked_models == []

    def test_blocked_models(self):
        """Test blocking specific models."""
        config = EnvironmentConfig(
            name=Environment.DEVELOPMENT,
            display_name="Dev",
            blocked_models=["gpt-4", "claude-3-opus"],
        )

        assert "gpt-4" in config.blocked_models
        assert "claude-3-opus" in config.blocked_models

    def test_allowed_models(self):
        """Test allowing only specific models."""
        config = EnvironmentConfig(
            name=Environment.DEVELOPMENT,
            display_name="Dev",
            allowed_models=["gpt-3.5-turbo"],
        )

        assert "gpt-3.5-turbo" in config.allowed_models


class TestLoggingSettings:
    """Tests for logging-related environment settings."""

    def test_production_minimal_logging(self):
        """Test that production has minimal logging for privacy."""
        config = DEFAULT_ENVIRONMENTS[Environment.PRODUCTION]

        # Should not log prompts/responses in production
        assert config.log_prompts is False
        assert config.log_responses is False

        # But should audit requests
        assert config.audit_all_requests is True

    def test_development_full_logging(self):
        """Test that development has full logging for debugging."""
        config = DEFAULT_ENVIRONMENTS[Environment.DEVELOPMENT]

        assert config.log_prompts is True
        assert config.log_responses is True
