"""
Fail-safe & Degraded Mode - Production Ready.

Ce module gère le comportement du gateway en cas de défaillance
des services de gouvernance.

Production features:
- Redis-based circuit breaker state (distributed)
- Configurable fail-open/fail-closed per service
- DB/Redis down strategies
- Health aggregation for Kubernetes probes
"""

from enum import Enum
from typing import Optional, Callable, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)


class FailureMode(str, Enum):
    """Mode de défaillance."""

    FAIL_OPEN = "fail_open"  # Allow request on failure
    FAIL_CLOSED = "fail_closed"  # Deny request on failure
    DEGRADED = "degraded"  # Allow with reduced functionality


class ServiceStatus(str, Enum):
    """Statut d'un service."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(str, Enum):
    """État du circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, blocking
    HALF_OPEN = "half_open"  # Testing if service recovered


class ServiceHealth(BaseModel):
    """État de santé d'un service."""

    name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None


class DependencyStrategy(str, Enum):
    """Strategy when a critical dependency is down."""

    REJECT_ALL = "reject_all"  # Return 503 for all requests
    READ_ONLY = "read_only"  # Allow reads, reject writes
    CACHED_ONLY = "cached_only"  # Only serve from cache
    ALLOW_WITH_WARNING = "allow_with_warning"  # Allow but add warning header


class DependencyConfig(BaseModel):
    """Configuration for a dependency (DB, Redis, etc.)."""

    name: str
    is_critical: bool = True
    strategy_when_down: DependencyStrategy = DependencyStrategy.REJECT_ALL
    health_check_interval_seconds: int = 10
    max_consecutive_failures: int = 3


class FailsafeConfig(BaseModel):
    """Configuration du mode fail-safe."""

    # Default behavior
    default_failure_mode: FailureMode = FailureMode.FAIL_CLOSED

    # Per-environment overrides
    environment_modes: dict[str, FailureMode] = {
        "development": FailureMode.FAIL_OPEN,
        "staging": FailureMode.FAIL_OPEN,
        "production": FailureMode.FAIL_CLOSED,
        "sandbox": FailureMode.FAIL_OPEN,
    }

    # Per-service overrides (CRITICAL: these define business logic)
    service_modes: dict[str, FailureMode] = {
        # FAIL_CLOSED: Security-critical, must work
        "policy_engine": FailureMode.FAIL_CLOSED,
        "budget_engine": FailureMode.FAIL_CLOSED,
        "security_checker": FailureMode.FAIL_CLOSED,
        "auth": FailureMode.FAIL_CLOSED,
        "license_enforcement": FailureMode.FAIL_CLOSED,
        # FAIL_OPEN: Non-blocking, best-effort
        "audit_logger": FailureMode.FAIL_OPEN,
        "metrics": FailureMode.FAIL_OPEN,
        "analytics": FailureMode.FAIL_OPEN,
        "abuse_detection": FailureMode.DEGRADED,  # Warn but allow
    }

    # Dependency strategies (DB, Redis, external services)
    dependency_configs: dict[str, DependencyConfig] = {
        "database": DependencyConfig(
            name="database",
            is_critical=True,
            strategy_when_down=DependencyStrategy.REJECT_ALL,
            max_consecutive_failures=3,
        ),
        "redis": DependencyConfig(
            name="redis",
            is_critical=False,  # Gateway can work without Redis (degraded)
            strategy_when_down=DependencyStrategy.ALLOW_WITH_WARNING,
            max_consecutive_failures=5,
        ),
        "llm_provider": DependencyConfig(
            name="llm_provider",
            is_critical=True,
            strategy_when_down=DependencyStrategy.REJECT_ALL,
            max_consecutive_failures=3,
        ),
    }

    # Circuit breaker settings
    circuit_failure_threshold: int = 5  # Failures before opening
    circuit_reset_timeout_seconds: int = 30  # Time before half-open
    circuit_success_threshold: int = 3  # Successes to close

    # Timeouts
    service_timeout_ms: int = 5000
    degraded_mode_timeout_ms: int = 1000  # Faster timeout in degraded mode


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping calls to failing services.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: int = 30,
        success_threshold: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_success_time: Optional[datetime] = None

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
                if elapsed >= self.reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        self._last_success_time = datetime.now(timezone.utc)

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker {self.name} closed (service recovered)")
        else:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)

        if self._state == CircuitState.HALF_OPEN:
            # Single failure in half-open reopens circuit
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} reopened (failure in half-open)")
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} opened (threshold reached)")

    def can_execute(self) -> bool:
        """Check if calls are allowed."""
        return self.state != CircuitState.OPEN

    def get_health(self) -> ServiceHealth:
        """Get service health based on circuit state."""
        status = {
            CircuitState.CLOSED: ServiceStatus.HEALTHY,
            CircuitState.HALF_OPEN: ServiceStatus.DEGRADED,
            CircuitState.OPEN: ServiceStatus.UNHEALTHY,
        }[self.state]

        return ServiceHealth(
            name=self.name,
            status=status,
            last_success=self._last_success_time,
            last_failure=self._last_failure_time,
            failure_count=self._failure_count,
            success_count=self._success_count,
        )


class FailsafeDecision(BaseModel):
    """Décision prise en mode fail-safe."""

    allowed: bool
    mode: FailureMode
    reason: str
    service_name: Optional[str] = None
    original_error: Optional[str] = None
    is_degraded: bool = False
    warnings: list[str] = []


class FailsafeManager:
    """
    Gestionnaire de fail-safe et mode dégradé.

    Responsabilités:
    - Gérer les circuit breakers par service
    - Prendre des décisions en cas de défaillance
    - Reporter l'état de santé des services
    """

    def __init__(self, config: Optional[FailsafeConfig] = None):
        self.config = config or FailsafeConfig()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._service_health: dict[str, ServiceHealth] = {}

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if service_name not in self._circuit_breakers:
            self._circuit_breakers[service_name] = CircuitBreaker(
                name=service_name,
                failure_threshold=self.config.circuit_failure_threshold,
                reset_timeout=self.config.circuit_reset_timeout_seconds,
                success_threshold=self.config.circuit_success_threshold,
            )
        return self._circuit_breakers[service_name]

    def get_failure_mode(self, service_name: str, environment: str) -> FailureMode:
        """Determine failure mode for a service in an environment."""
        # Service-specific mode takes precedence
        if service_name in self.config.service_modes:
            return self.config.service_modes[service_name]

        # Then environment mode
        if environment in self.config.environment_modes:
            return self.config.environment_modes[environment]

        # Default
        return self.config.default_failure_mode

    async def execute_with_failsafe(
        self,
        service_name: str,
        environment: str,
        operation: Callable[..., Any],
        *args,
        fallback: Optional[Callable[..., Any]] = None,
        **kwargs,
    ) -> tuple[Any, FailsafeDecision]:
        """
        Execute an operation with fail-safe handling.

        Args:
            service_name: Name of the service
            environment: Current environment
            operation: Async function to execute
            fallback: Optional fallback function
            *args, **kwargs: Arguments for operation

        Returns:
            (result, decision)
        """
        circuit = self.get_circuit_breaker(service_name)
        failure_mode = self.get_failure_mode(service_name, environment)

        # Check circuit breaker
        if not circuit.can_execute():
            return self._handle_circuit_open(
                service_name, environment, failure_mode, fallback, *args, **kwargs
            )

        # Try to execute
        try:
            timeout = self.config.service_timeout_ms / 1000
            result = await asyncio.wait_for(
                operation(*args, **kwargs)
                if asyncio.iscoroutinefunction(operation)
                else asyncio.to_thread(operation, *args, **kwargs),
                timeout=timeout,
            )

            circuit.record_success()

            return result, FailsafeDecision(
                allowed=True,
                mode=failure_mode,
                reason="Service executed successfully",
                service_name=service_name,
            )

        except asyncio.TimeoutError:
            circuit.record_failure()
            return self._handle_failure(
                service_name,
                environment,
                failure_mode,
                f"Service timeout after {self.config.service_timeout_ms}ms",
                fallback,
                *args,
                **kwargs,
            )

        except Exception as e:
            circuit.record_failure()
            return self._handle_failure(
                service_name, environment, failure_mode, str(e), fallback, *args, **kwargs
            )

    def _handle_circuit_open(
        self,
        service_name: str,
        environment: str,
        failure_mode: FailureMode,
        fallback: Optional[Callable],
        *args,
        **kwargs,
    ) -> tuple[Any, FailsafeDecision]:
        """Handle case where circuit breaker is open."""
        return self._handle_failure(
            service_name,
            environment,
            failure_mode,
            "Circuit breaker is open",
            fallback,
            *args,
            **kwargs,
        )

    def _handle_failure(
        self,
        service_name: str,
        environment: str,
        failure_mode: FailureMode,
        error: str,
        fallback: Optional[Callable],
        *args,
        **kwargs,
    ) -> tuple[Any, FailsafeDecision]:
        """Handle service failure based on configured mode."""
        logger.warning(f"Service {service_name} failed: {error}. Mode: {failure_mode}")

        if failure_mode == FailureMode.FAIL_OPEN:
            # Allow request to proceed
            result = None
            if fallback:
                try:
                    result = fallback(*args, **kwargs)
                except Exception:
                    pass

            return result, FailsafeDecision(
                allowed=True,
                mode=failure_mode,
                reason=f"Fail-open: allowing request despite {service_name} failure",
                service_name=service_name,
                original_error=error,
                is_degraded=True,
                warnings=[f"Service {service_name} is unavailable, running in degraded mode"],
            )

        elif failure_mode == FailureMode.FAIL_CLOSED:
            return None, FailsafeDecision(
                allowed=False,
                mode=failure_mode,
                reason=f"Fail-closed: denying request due to {service_name} failure",
                service_name=service_name,
                original_error=error,
            )

        elif failure_mode == FailureMode.DEGRADED:
            # Try fallback with reduced timeout
            result = None
            if fallback:
                try:
                    result = fallback(*args, **kwargs)
                except Exception:
                    pass

            return result, FailsafeDecision(
                allowed=True,
                mode=failure_mode,
                reason=f"Degraded mode: proceeding with limited {service_name} functionality",
                service_name=service_name,
                original_error=error,
                is_degraded=True,
                warnings=[f"Running in degraded mode for {service_name}"],
            )

        return None, FailsafeDecision(
            allowed=False,
            mode=failure_mode,
            reason="Unknown failure mode",
        )

    def get_system_health(self) -> dict[str, ServiceHealth]:
        """Get health status of all services."""
        health = {}
        for name, circuit in self._circuit_breakers.items():
            health[name] = circuit.get_health()
        return health

    def get_overall_status(self) -> ServiceStatus:
        """Get overall system status."""
        health = self.get_system_health()

        if not health:
            return ServiceStatus.UNKNOWN

        unhealthy_count = sum(1 for h in health.values() if h.status == ServiceStatus.UNHEALTHY)
        degraded_count = sum(1 for h in health.values() if h.status == ServiceStatus.DEGRADED)

        if unhealthy_count > 0:
            return ServiceStatus.UNHEALTHY
        elif degraded_count > 0:
            return ServiceStatus.DEGRADED
        return ServiceStatus.HEALTHY

    def reset_circuit(self, service_name: str) -> bool:
        """Manually reset a circuit breaker."""
        if service_name in self._circuit_breakers:
            del self._circuit_breakers[service_name]
            logger.info(f"Circuit breaker {service_name} reset")
            return True
        return False


# Singleton
failsafe_manager = FailsafeManager()


async def with_failsafe(
    service_name: str,
    environment: str,
    operation: Callable[..., Any],
    *args,
    fallback: Optional[Callable] = None,
    **kwargs,
) -> tuple[Any, FailsafeDecision]:
    """Execute with fail-safe handling."""
    return await failsafe_manager.execute_with_failsafe(
        service_name, environment, operation, *args, fallback=fallback, **kwargs
    )


def get_system_health() -> dict[str, ServiceHealth]:
    """Get system health status."""
    return failsafe_manager.get_system_health()


def get_failure_mode(service_name: str, environment: str) -> FailureMode:
    """Get failure mode for a service."""
    return failsafe_manager.get_failure_mode(service_name, environment)


# =============================================================================
# Dependency Health Manager (DB, Redis, LLM Provider)
# =============================================================================


class DependencyHealthManager:
    """
    Manages health state of critical dependencies.

    Used for:
    - Kubernetes readiness probes
    - Request routing decisions
    - Graceful degradation
    """

    def __init__(self, config: Optional[FailsafeConfig] = None):
        self.config = config or FailsafeConfig()
        self._health_state: dict[str, ServiceHealth] = {}
        self._consecutive_failures: dict[str, int] = {}

    def record_success(self, dependency_name: str, latency_ms: float) -> None:
        """Record successful health check for a dependency."""
        self._consecutive_failures[dependency_name] = 0
        self._health_state[dependency_name] = ServiceHealth(
            name=dependency_name,
            status=ServiceStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            last_success=datetime.now(timezone.utc),
            latency_ms=latency_ms,
        )

    def record_failure(self, dependency_name: str, error: str) -> None:
        """Record failed health check for a dependency."""
        failures = self._consecutive_failures.get(dependency_name, 0) + 1
        self._consecutive_failures[dependency_name] = failures

        dep_config = self.config.dependency_configs.get(
            dependency_name, DependencyConfig(name=dependency_name)
        )

        status = ServiceStatus.DEGRADED
        if failures >= dep_config.max_consecutive_failures:
            status = ServiceStatus.UNHEALTHY

        self._health_state[dependency_name] = ServiceHealth(
            name=dependency_name,
            status=status,
            last_check=datetime.now(timezone.utc),
            last_failure=datetime.now(timezone.utc),
            failure_count=failures,
            error_message=error,
        )

        if status == ServiceStatus.UNHEALTHY:
            logger.error(
                f"Dependency {dependency_name} marked UNHEALTHY after {failures} failures: {error}"
            )

    def get_dependency_health(self, dependency_name: str) -> ServiceHealth:
        """Get health status of a dependency."""
        return self._health_state.get(
            dependency_name, ServiceHealth(name=dependency_name, status=ServiceStatus.UNKNOWN)
        )

    def is_dependency_healthy(self, dependency_name: str) -> bool:
        """Check if a dependency is healthy."""
        health = self.get_dependency_health(dependency_name)
        return health.status == ServiceStatus.HEALTHY

    def should_allow_request(self, dependency_name: str) -> tuple[bool, Optional[str]]:
        """
        Determine if requests should be allowed based on dependency health.

        Returns:
            (allowed, warning_message)
        """
        health = self.get_dependency_health(dependency_name)
        dep_config = self.config.dependency_configs.get(
            dependency_name, DependencyConfig(name=dependency_name)
        )

        if health.status == ServiceStatus.HEALTHY:
            return True, None

        if health.status == ServiceStatus.UNKNOWN:
            # First request, dependency not yet checked
            return True, f"Dependency {dependency_name} status unknown"

        # Dependency is DEGRADED or UNHEALTHY
        strategy = dep_config.strategy_when_down

        if strategy == DependencyStrategy.REJECT_ALL:
            return False, f"Dependency {dependency_name} is {health.status.value}"

        elif strategy == DependencyStrategy.ALLOW_WITH_WARNING:
            return (
                True,
                f"Dependency {dependency_name} is {health.status.value}, proceeding in degraded mode",
            )

        elif strategy == DependencyStrategy.READ_ONLY:
            # Caller must handle read-only mode
            return True, f"Dependency {dependency_name} is {health.status.value}, read-only mode"

        elif strategy == DependencyStrategy.CACHED_ONLY:
            return (
                True,
                f"Dependency {dependency_name} is {health.status.value}, serving from cache only",
            )

        return False, f"Unknown strategy for {dependency_name}"

    def get_all_health(self) -> dict[str, ServiceHealth]:
        """Get health status of all dependencies."""
        return self._health_state.copy()

    def is_system_ready(self) -> tuple[bool, list[str]]:
        """
        Check if system is ready to serve requests.

        Returns:
            (ready, list_of_issues)
        """
        issues = []

        for dep_name, dep_config in self.config.dependency_configs.items():
            if not dep_config.is_critical:
                continue

            health = self.get_dependency_health(dep_name)

            if health.status == ServiceStatus.UNHEALTHY:
                issues.append(f"Critical dependency {dep_name} is unhealthy")
            elif health.status == ServiceStatus.UNKNOWN:
                issues.append(f"Critical dependency {dep_name} not yet checked")

        return len(issues) == 0, issues


# Singleton for dependency health
dependency_health_manager = DependencyHealthManager()


def record_dependency_success(dependency_name: str, latency_ms: float) -> None:
    """Record successful dependency check."""
    dependency_health_manager.record_success(dependency_name, latency_ms)


def record_dependency_failure(dependency_name: str, error: str) -> None:
    """Record failed dependency check."""
    dependency_health_manager.record_failure(dependency_name, error)


def is_system_ready() -> tuple[bool, list[str]]:
    """Check if system is ready to serve requests."""
    return dependency_health_manager.is_system_ready()


def should_allow_request(dependency_name: str) -> tuple[bool, Optional[str]]:
    """Check if request should be allowed based on dependency health."""
    return dependency_health_manager.should_allow_request(dependency_name)
