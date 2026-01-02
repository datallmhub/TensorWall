"""Environment Isolation System.

Provides strict separation between environments (dev, staging, production).
Prevents cross-environment data access and enforces environment-specific policies.
"""

from typing import Optional
from pydantic import BaseModel
from enum import Enum


class Environment(str, Enum):
    """Standard environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    SANDBOX = "sandbox"  # For testing/demos


class EnvironmentConfig(BaseModel):
    """Configuration for an environment."""

    name: Environment
    display_name: str

    # Access controls
    allowed_source_ips: list[str] = []  # Empty = all allowed
    require_api_key_prefix: Optional[str] = None  # e.g., "prod_", "dev_"

    # Policy enforcement
    strict_mode: bool = False  # Enforce all policies
    allow_debug_mode: bool = True  # Allow debug headers
    require_contracts: bool = True  # Require usage contracts

    # Model access
    allowed_models: list[str] = []  # Empty = all allowed
    blocked_models: list[str] = []  # Models not allowed in this env

    # Budget settings
    default_budget_multiplier: float = 1.0  # Multiplier for budgets

    # Security settings
    pii_detection_enabled: bool = True
    prompt_injection_detection: bool = True
    security_scan_level: str = "standard"  # minimal, standard, strict

    # Logging
    log_prompts: bool = True
    log_responses: bool = True
    audit_all_requests: bool = True

    # Feature flags
    allow_experimental_features: bool = False

    class Config:
        use_enum_values = True


# Default environment configurations
DEFAULT_ENVIRONMENTS: dict[Environment, EnvironmentConfig] = {
    Environment.DEVELOPMENT: EnvironmentConfig(
        name=Environment.DEVELOPMENT,
        display_name="Development",
        strict_mode=False,
        allow_debug_mode=True,
        require_contracts=False,
        pii_detection_enabled=False,
        prompt_injection_detection=True,
        security_scan_level="minimal",
        log_prompts=True,
        log_responses=True,
        audit_all_requests=False,
        allow_experimental_features=True,
        default_budget_multiplier=0.1,  # 10% of budget for dev
    ),
    Environment.STAGING: EnvironmentConfig(
        name=Environment.STAGING,
        display_name="Staging",
        strict_mode=True,
        allow_debug_mode=True,
        require_contracts=True,
        pii_detection_enabled=True,
        prompt_injection_detection=True,
        security_scan_level="standard",
        log_prompts=True,
        log_responses=True,
        audit_all_requests=True,
        allow_experimental_features=True,
        default_budget_multiplier=0.5,  # 50% of budget for staging
    ),
    Environment.PRODUCTION: EnvironmentConfig(
        name=Environment.PRODUCTION,
        display_name="Production",
        strict_mode=True,
        allow_debug_mode=False,
        require_contracts=True,
        pii_detection_enabled=True,
        prompt_injection_detection=True,
        security_scan_level="strict",
        log_prompts=False,  # Privacy in production
        log_responses=False,
        audit_all_requests=True,
        allow_experimental_features=False,
        default_budget_multiplier=1.0,
        blocked_models=["gpt-4-turbo-preview"],  # Block unstable models in prod
    ),
    Environment.SANDBOX: EnvironmentConfig(
        name=Environment.SANDBOX,
        display_name="Sandbox",
        strict_mode=False,
        allow_debug_mode=True,
        require_contracts=False,
        pii_detection_enabled=False,
        prompt_injection_detection=False,
        security_scan_level="minimal",
        log_prompts=True,
        log_responses=True,
        audit_all_requests=False,
        allow_experimental_features=True,
        default_budget_multiplier=0.01,  # 1% of budget for sandbox
    ),
}


class EnvironmentValidationResult(BaseModel):
    """Result of environment validation."""

    valid: bool
    environment: str
    errors: list[str] = []
    warnings: list[str] = []


class EnvironmentManager:
    """
    Manages environment isolation and validation.

    Features:
    - Environment detection and validation
    - Cross-environment access prevention
    - Environment-specific policy enforcement
    - API key environment binding
    """

    def __init__(self):
        self.environments: dict[Environment, EnvironmentConfig] = dict(
            DEFAULT_ENVIRONMENTS
        )
        self._api_key_environment_map: dict[str, Environment] = {}

    def configure_environment(self, config: EnvironmentConfig) -> None:
        """Configure or update an environment."""
        self.environments[config.name] = config

    def get_environment_config(self, env: str) -> Optional[EnvironmentConfig]:
        """Get configuration for an environment."""
        try:
            env_enum = Environment(env)
            return self.environments.get(env_enum)
        except ValueError:
            return None

    def bind_api_key_to_environment(
        self, api_key_prefix: str, environment: Environment
    ) -> None:
        """Bind an API key prefix to an environment."""
        self._api_key_environment_map[api_key_prefix] = environment

    def detect_environment_from_api_key(self, api_key: str) -> Optional[Environment]:
        """Detect environment from API key prefix."""
        for prefix, env in self._api_key_environment_map.items():
            if api_key.startswith(prefix):
                return env

        # Default detection based on common patterns
        if api_key.startswith("dev_") or api_key.startswith("development_"):
            return Environment.DEVELOPMENT
        if api_key.startswith("stg_") or api_key.startswith("staging_"):
            return Environment.STAGING
        if api_key.startswith("prod_") or api_key.startswith("production_"):
            return Environment.PRODUCTION
        if api_key.startswith("sandbox_") or api_key.startswith("sbx_"):
            return Environment.SANDBOX

        return None

    def validate_request(
        self,
        declared_environment: str,
        api_key: str,
        source_ip: Optional[str] = None,
        model: Optional[str] = None,
        has_contract: bool = False,
        is_debug: bool = False,
    ) -> EnvironmentValidationResult:
        """
        Validate a request against environment policies.

        Args:
            declared_environment: Environment declared in the request
            api_key: API key used for the request
            source_ip: Source IP address
            model: Model being requested
            has_contract: Whether request has a usage contract
            is_debug: Whether debug mode is requested

        Returns:
            EnvironmentValidationResult with validation status
        """
        errors = []
        warnings = []

        # Get environment config
        config = self.get_environment_config(declared_environment)
        if not config:
            return EnvironmentValidationResult(
                valid=False,
                environment=declared_environment,
                errors=[f"Unknown environment: {declared_environment}"],
            )

        # Check API key matches environment
        detected_env = self.detect_environment_from_api_key(api_key)
        if detected_env and detected_env.value != declared_environment:
            if config.strict_mode:
                errors.append(
                    f"API key environment mismatch: key is for {detected_env.value}, "
                    f"but request declares {declared_environment}"
                )
            else:
                warnings.append(
                    f"API key appears to be for {detected_env.value}, "
                    f"but request declares {declared_environment}"
                )

        # Check required API key prefix
        if config.require_api_key_prefix:
            if not api_key.startswith(config.require_api_key_prefix):
                errors.append(
                    f"API key must start with '{config.require_api_key_prefix}' "
                    f"for {declared_environment} environment"
                )

        # Check source IP
        if config.allowed_source_ips and source_ip:
            if source_ip not in config.allowed_source_ips:
                # Check CIDR ranges (simplified)
                ip_allowed = False
                for allowed_ip in config.allowed_source_ips:
                    if "/" in allowed_ip:
                        # CIDR notation - simplified check
                        if source_ip.startswith(
                            allowed_ip.split("/")[0].rsplit(".", 1)[0]
                        ):
                            ip_allowed = True
                            break
                    elif source_ip == allowed_ip:
                        ip_allowed = True
                        break

                if not ip_allowed:
                    errors.append(
                        f"Source IP {source_ip} not allowed in {declared_environment}"
                    )

        # Check model access
        if model:
            if config.blocked_models and model in config.blocked_models:
                errors.append(f"Model '{model}' is blocked in {declared_environment}")

            if config.allowed_models and model not in config.allowed_models:
                errors.append(
                    f"Model '{model}' is not allowed in {declared_environment}"
                )

        # Check contract requirement
        if config.require_contracts and not has_contract:
            errors.append(f"Usage contract required in {declared_environment}")

        # Check debug mode
        if is_debug and not config.allow_debug_mode:
            errors.append(f"Debug mode not allowed in {declared_environment}")

        return EnvironmentValidationResult(
            valid=len(errors) == 0,
            environment=declared_environment,
            errors=errors,
            warnings=warnings,
        )

    def get_effective_budget_limit(
        self,
        base_limit: float,
        environment: str,
    ) -> float:
        """
        Get the effective budget limit for an environment.

        Applies environment-specific multipliers to base limits.
        """
        config = self.get_environment_config(environment)
        if not config:
            return base_limit

        return base_limit * config.default_budget_multiplier

    def should_log_content(self, environment: str) -> tuple[bool, bool]:
        """
        Check if prompts and responses should be logged.

        Returns:
            Tuple of (log_prompts, log_responses)
        """
        config = self.get_environment_config(environment)
        if not config:
            return True, True

        return config.log_prompts, config.log_responses

    def get_security_level(self, environment: str) -> str:
        """Get the security scan level for an environment."""
        config = self.get_environment_config(environment)
        if not config:
            return "standard"

        return config.security_scan_level

    def is_strict_mode(self, environment: str) -> bool:
        """Check if strict mode is enabled for an environment."""
        config = self.get_environment_config(environment)
        if not config:
            return False

        return config.strict_mode

    def allows_experimental_features(self, environment: str) -> bool:
        """Check if experimental features are allowed in an environment."""
        config = self.get_environment_config(environment)
        if not config:
            return False

        return config.allow_experimental_features


class CrossEnvironmentGuard:
    """
    Guards against cross-environment data access.

    Ensures data from one environment cannot leak to another.
    """

    def __init__(self, environment_manager: EnvironmentManager):
        self.env_manager = environment_manager

    def can_access_data(
        self,
        requesting_environment: str,
        data_environment: str,
    ) -> tuple[bool, str]:
        """
        Check if data from one environment can be accessed by another.

        Returns:
            Tuple of (allowed, reason)
        """
        # Same environment always allowed
        if requesting_environment == data_environment:
            return True, "Same environment"

        # Production can never access non-production data
        if requesting_environment == Environment.PRODUCTION.value:
            return False, "Production cannot access non-production data"

        # Non-production environments can access each other's data in non-strict mode
        req_config = self.env_manager.get_environment_config(requesting_environment)
        if req_config and not req_config.strict_mode:
            # Development can access staging
            if requesting_environment == Environment.DEVELOPMENT.value:
                if data_environment == Environment.STAGING.value:
                    return True, "Development can access staging data"

        return (
            False,
            f"Cross-environment access denied: {requesting_environment} -> {data_environment}",
        )

    def validate_cache_key(
        self,
        cache_key: str,
        environment: str,
    ) -> tuple[bool, str]:
        """
        Validate that a cache key is appropriate for the environment.

        Cache keys should be namespaced by environment to prevent leakage.
        """
        expected_prefix = f"env:{environment}:"

        if not cache_key.startswith(expected_prefix):
            return False, f"Cache key must be namespaced with '{expected_prefix}'"

        return True, "Valid cache key"

    def namespace_cache_key(self, key: str, environment: str) -> str:
        """Add environment namespace to a cache key."""
        return f"env:{environment}:{key}"


# Singleton instances
environment_manager = EnvironmentManager()
cross_env_guard = CrossEnvironmentGuard(environment_manager)


# Convenience functions
def get_environment_config(env: str) -> Optional[EnvironmentConfig]:
    """Get configuration for an environment."""
    return environment_manager.get_environment_config(env)


def validate_environment(
    declared_environment: str,
    api_key: str,
    **kwargs,
) -> EnvironmentValidationResult:
    """Validate a request against environment policies."""
    return environment_manager.validate_request(declared_environment, api_key, **kwargs)


def namespace_key(key: str, environment: str) -> str:
    """Add environment namespace to a key."""
    return cross_env_guard.namespace_cache_key(key, environment)


class EnvironmentIsolation:
    """
    Hard isolation for environment resources.

    Ensures complete separation of:
    - API keys (no cross-env reuse)
    - Budgets (physically separated)
    - Policies (scoped per env)
    - Metrics (separate namespaces)
    - Audit logs (isolated)
    """

    def __init__(self):
        # Track API key assignments to prevent reuse
        self._key_to_env: dict[str, str] = {}
        self._env_budgets: dict[str, dict[str, float]] = {}
        self._env_policies: dict[str, list[str]] = {}

    def register_api_key(self, api_key: str, environment: str) -> bool:
        """
        Register an API key for a specific environment.

        Returns False if key is already registered to different env.
        """
        existing = self._key_to_env.get(api_key)
        if existing and existing != environment:
            return False
        self._key_to_env[api_key] = environment
        return True

    def validate_api_key_environment(
        self, api_key: str, requested_environment: str
    ) -> tuple[bool, str]:
        """
        Validate API key matches requested environment.

        Returns:
            (valid, reason)
        """
        registered_env = self._key_to_env.get(api_key)

        if not registered_env:
            # First use - register it
            self._key_to_env[api_key] = requested_environment
            return True, "API key registered to environment"

        if registered_env != requested_environment:
            return False, (
                f"API key is bound to '{registered_env}' environment. "
                f"Cannot use in '{requested_environment}'. "
                "Create a separate key for each environment."
            )

        return True, "API key matches environment"

    def get_budget_namespace(self, environment: str) -> str:
        """Get isolated budget namespace for environment."""
        return f"budget:env:{environment}"

    def get_policy_namespace(self, environment: str) -> str:
        """Get isolated policy namespace for environment."""
        return f"policy:env:{environment}"

    def get_metrics_namespace(self, environment: str) -> str:
        """Get isolated metrics namespace for environment."""
        return f"metrics:env:{environment}"

    def get_audit_namespace(self, environment: str) -> str:
        """Get isolated audit log namespace for environment."""
        return f"audit:env:{environment}"

    def isolate_budget_id(self, budget_id: str, environment: str) -> str:
        """Create environment-isolated budget ID."""
        if budget_id.startswith(f"env:{environment}:"):
            return budget_id
        return f"env:{environment}:{budget_id}"

    def isolate_policy_id(self, policy_id: str, environment: str) -> str:
        """Create environment-isolated policy ID."""
        if policy_id.startswith(f"env:{environment}:"):
            return policy_id
        return f"env:{environment}:{policy_id}"

    def extract_environment_from_id(
        self, isolated_id: str
    ) -> tuple[Optional[str], str]:
        """
        Extract environment from isolated ID.

        Returns:
            (environment, original_id)
        """
        if isolated_id.startswith("env:"):
            parts = isolated_id.split(":", 2)
            if len(parts) >= 3:
                return parts[1], parts[2]
        return None, isolated_id

    def validate_cross_env_access(
        self,
        source_env: str,
        target_resource_id: str,
    ) -> tuple[bool, str]:
        """
        Validate access to a resource from a different environment.

        Returns:
            (allowed, reason)
        """
        target_env, _ = self.extract_environment_from_id(target_resource_id)

        if not target_env:
            # No environment in ID - allow (legacy compatibility)
            return True, "Resource has no environment scope"

        if target_env == source_env:
            return True, "Same environment"

        # Strict: no cross-env access
        return False, (
            f"Cross-environment access denied. "
            f"Resource belongs to '{target_env}', request is from '{source_env}'"
        )


class EnvironmentAwareMetrics:
    """
    Environment-aware metrics collection.

    Ensures metrics from different environments are never mixed.
    """

    def __init__(self, isolation: EnvironmentIsolation):
        self._isolation = isolation
        self._counters: dict[str, dict[str, int]] = {}
        self._gauges: dict[str, dict[str, float]] = {}

    def _get_metric_key(self, name: str, environment: str) -> str:
        """Get environment-namespaced metric key."""
        return f"{self._isolation.get_metrics_namespace(environment)}:{name}"

    def increment_counter(
        self,
        name: str,
        environment: str,
        value: int = 1,
        labels: Optional[dict[str, str]] = None,
    ) -> None:
        """Increment a counter with environment isolation."""
        key = self._get_metric_key(name, environment)
        label_key = str(labels) if labels else "default"

        if key not in self._counters:
            self._counters[key] = {}
        if label_key not in self._counters[key]:
            self._counters[key][label_key] = 0

        self._counters[key][label_key] += value

    def set_gauge(
        self,
        name: str,
        environment: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ) -> None:
        """Set a gauge with environment isolation."""
        key = self._get_metric_key(name, environment)
        label_key = str(labels) if labels else "default"

        if key not in self._gauges:
            self._gauges[key] = {}

        self._gauges[key][label_key] = value

    def get_counter(
        self, name: str, environment: str, labels: Optional[dict[str, str]] = None
    ) -> int:
        """Get counter value for specific environment."""
        key = self._get_metric_key(name, environment)
        label_key = str(labels) if labels else "default"

        return self._counters.get(key, {}).get(label_key, 0)

    def get_all_counters_for_env(self, environment: str) -> dict[str, dict[str, int]]:
        """Get all counters for a specific environment."""
        prefix = self._isolation.get_metrics_namespace(environment)
        return {k: v for k, v in self._counters.items() if k.startswith(prefix)}


# Enhanced singleton instances
environment_isolation = EnvironmentIsolation()
env_aware_metrics = EnvironmentAwareMetrics(environment_isolation)


def validate_api_key_isolation(api_key: str, environment: str) -> tuple[bool, str]:
    """Validate API key is bound to the correct environment."""
    return environment_isolation.validate_api_key_environment(api_key, environment)


def isolate_resource_id(resource_type: str, resource_id: str, environment: str) -> str:
    """Create an environment-isolated resource ID."""
    if resource_type == "budget":
        return environment_isolation.isolate_budget_id(resource_id, environment)
    elif resource_type == "policy":
        return environment_isolation.isolate_policy_id(resource_id, environment)
    else:
        return f"env:{environment}:{resource_type}:{resource_id}"
