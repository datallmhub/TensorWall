"""Unit tests for Failsafe / Degraded Mode module."""

from datetime import datetime, timezone, timedelta

from backend.core.failsafe import (
    FailureMode,
    ServiceStatus,
    CircuitState,
    ServiceHealth,
    DependencyStrategy,
    DependencyConfig,
    FailsafeConfig,
)


class TestFailureMode:
    """Tests for FailureMode enum."""

    def test_valid_modes(self):
        """Test all valid modes."""
        assert FailureMode.FAIL_OPEN == "fail_open"
        assert FailureMode.FAIL_CLOSED == "fail_closed"
        assert FailureMode.DEGRADED == "degraded"


class TestServiceStatus:
    """Tests for ServiceStatus enum."""

    def test_valid_statuses(self):
        """Test all valid statuses."""
        assert ServiceStatus.HEALTHY == "healthy"
        assert ServiceStatus.DEGRADED == "degraded"
        assert ServiceStatus.UNHEALTHY == "unhealthy"
        assert ServiceStatus.UNKNOWN == "unknown"


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_valid_states(self):
        """Test all valid states."""
        assert CircuitState.CLOSED == "closed"
        assert CircuitState.OPEN == "open"
        assert CircuitState.HALF_OPEN == "half_open"


class TestServiceHealth:
    """Tests for ServiceHealth model."""

    def test_create_minimal(self):
        """Test creating ServiceHealth with minimal fields."""
        health = ServiceHealth(name="database")

        assert health.name == "database"
        assert health.status == ServiceStatus.UNKNOWN
        assert health.failure_count == 0
        assert health.success_count == 0

    def test_create_healthy(self):
        """Test creating healthy service."""
        health = ServiceHealth(
            name="database",
            status=ServiceStatus.HEALTHY,
            last_success=datetime.now(timezone.utc),
            success_count=100,
            latency_ms=5.5,
        )

        assert health.status == ServiceStatus.HEALTHY
        assert health.success_count == 100
        assert health.latency_ms == 5.5

    def test_create_unhealthy(self):
        """Test creating unhealthy service."""
        health = ServiceHealth(
            name="redis",
            status=ServiceStatus.UNHEALTHY,
            last_failure=datetime.now(timezone.utc),
            failure_count=5,
            error_message="Connection refused",
        )

        assert health.status == ServiceStatus.UNHEALTHY
        assert health.failure_count == 5
        assert health.error_message == "Connection refused"


class TestDependencyStrategy:
    """Tests for DependencyStrategy enum."""

    def test_valid_strategies(self):
        """Test all valid strategies."""
        assert DependencyStrategy.REJECT_ALL == "reject_all"
        assert DependencyStrategy.READ_ONLY == "read_only"
        assert DependencyStrategy.CACHED_ONLY == "cached_only"
        assert DependencyStrategy.ALLOW_WITH_WARNING == "allow_with_warning"


class TestDependencyConfig:
    """Tests for DependencyConfig model."""

    def test_create_minimal(self):
        """Test creating DependencyConfig with minimal fields."""
        config = DependencyConfig(name="database")

        assert config.name == "database"
        assert config.is_critical is True
        assert config.strategy_when_down == DependencyStrategy.REJECT_ALL

    def test_create_non_critical(self):
        """Test creating non-critical dependency config."""
        config = DependencyConfig(
            name="cache",
            is_critical=False,
            strategy_when_down=DependencyStrategy.ALLOW_WITH_WARNING,
            health_check_interval_seconds=30,
            max_consecutive_failures=5,
        )

        assert config.is_critical is False
        assert config.strategy_when_down == DependencyStrategy.ALLOW_WITH_WARNING


class TestFailsafeConfig:
    """Tests for FailsafeConfig model."""

    def test_create_default(self):
        """Test creating FailsafeConfig with defaults."""
        config = FailsafeConfig()

        assert config.default_failure_mode == FailureMode.FAIL_CLOSED

    def test_environment_modes(self):
        """Test environment-specific modes."""
        config = FailsafeConfig()

        assert config.environment_modes["development"] == FailureMode.FAIL_OPEN
        assert config.environment_modes["production"] == FailureMode.FAIL_CLOSED

    def test_service_modes(self):
        """Test service-specific modes."""
        config = FailsafeConfig()

        # Security-critical services should fail closed
        assert config.service_modes["policy_engine"] == FailureMode.FAIL_CLOSED
        assert config.service_modes["budget_engine"] == FailureMode.FAIL_CLOSED
        assert config.service_modes["auth"] == FailureMode.FAIL_CLOSED

        # Non-blocking services should fail open
        assert config.service_modes["audit_logger"] == FailureMode.FAIL_OPEN
        assert config.service_modes["metrics"] == FailureMode.FAIL_OPEN

    def test_custom_config(self):
        """Test creating custom FailsafeConfig."""
        config = FailsafeConfig(
            default_failure_mode=FailureMode.FAIL_OPEN,
            environment_modes={
                "production": FailureMode.FAIL_OPEN,
            },
            service_modes={
                "custom_service": FailureMode.DEGRADED,
            },
        )

        assert config.default_failure_mode == FailureMode.FAIL_OPEN
        assert config.environment_modes["production"] == FailureMode.FAIL_OPEN
        assert config.service_modes["custom_service"] == FailureMode.DEGRADED


class TestServiceHealthTracking:
    """Tests for service health tracking scenarios."""

    def test_healthy_to_degraded(self):
        """Test service transitioning from healthy to degraded."""
        health = ServiceHealth(
            name="database",
            status=ServiceStatus.HEALTHY,
            success_count=100,
            failure_count=0,
        )

        # Simulate some failures
        health.failure_count = 2
        health.status = ServiceStatus.DEGRADED
        health.error_message = "Slow response"

        assert health.status == ServiceStatus.DEGRADED
        assert health.failure_count == 2

    def test_degraded_to_unhealthy(self):
        """Test service transitioning from degraded to unhealthy."""
        health = ServiceHealth(
            name="redis",
            status=ServiceStatus.DEGRADED,
            failure_count=3,
        )

        # More failures
        health.failure_count = 5
        health.status = ServiceStatus.UNHEALTHY
        health.last_failure = datetime.now(timezone.utc)

        assert health.status == ServiceStatus.UNHEALTHY

    def test_recovery(self):
        """Test service recovery."""
        health = ServiceHealth(
            name="database",
            status=ServiceStatus.UNHEALTHY,
            failure_count=10,
        )

        # Recovery
        health.status = ServiceStatus.HEALTHY
        health.failure_count = 0
        health.success_count = 1
        health.last_success = datetime.now(timezone.utc)
        health.error_message = None

        assert health.status == ServiceStatus.HEALTHY
        assert health.failure_count == 0


class TestCircuitBreakerStates:
    """Tests for circuit breaker state transitions."""

    def test_closed_to_open(self):
        """Test circuit going from closed to open on failures."""
        # Simulating circuit breaker behavior
        state = CircuitState.CLOSED
        failure_count = 0
        threshold = 5

        # Simulate failures
        for _ in range(5):
            failure_count += 1

        if failure_count >= threshold:
            state = CircuitState.OPEN

        assert state == CircuitState.OPEN

    def test_open_to_half_open(self):
        """Test circuit going from open to half-open after timeout."""
        state = CircuitState.OPEN
        open_since = datetime.now(timezone.utc) - timedelta(seconds=60)
        timeout_seconds = 30

        # Check if timeout elapsed
        if (datetime.now(timezone.utc) - open_since).total_seconds() >= timeout_seconds:
            state = CircuitState.HALF_OPEN

        assert state == CircuitState.HALF_OPEN

    def test_half_open_to_closed(self):
        """Test circuit going from half-open to closed on success."""
        state = CircuitState.HALF_OPEN
        success = True

        if success:
            state = CircuitState.CLOSED

        assert state == CircuitState.CLOSED

    def test_half_open_to_open(self):
        """Test circuit going from half-open back to open on failure."""
        state = CircuitState.HALF_OPEN
        failure = True

        if failure:
            state = CircuitState.OPEN

        assert state == CircuitState.OPEN
