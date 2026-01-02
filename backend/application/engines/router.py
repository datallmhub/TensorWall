"""
LLM Router with Load Balancing, Fallback, and Retry

Features:
- Round-robin load balancing across multiple endpoints
- Automatic fallback to backup providers
- Configurable retry with exponential backoff
- Health checking and circuit breaker
- Latency-based routing

Usage:
    router = LLMRouter()
    router.add_route("gpt-4", [
        {"provider": "openai", "weight": 70},
        {"provider": "azure", "endpoint": "https://...", "weight": 30},
    ])
    response = await router.chat(request, api_key)
"""

import asyncio
import random
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from backend.application.providers.base import LLMProvider, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class EndpointHealth:
    """Health status for an endpoint."""

    failures: int = 0
    successes: int = 0
    last_failure: float = 0
    last_success: float = 0
    circuit_state: CircuitState = CircuitState.CLOSED
    avg_latency_ms: float = 0
    request_count: int = 0

    def record_success(self, latency_ms: float):
        """Record a successful request."""
        self.successes += 1
        self.last_success = time.time()
        self.request_count += 1
        # Update rolling average latency
        self.avg_latency_ms = (
            self.avg_latency_ms * (self.request_count - 1) + latency_ms
        ) / self.request_count
        # Reset circuit breaker on success
        if self.circuit_state == CircuitState.HALF_OPEN:
            self.circuit_state = CircuitState.CLOSED
            self.failures = 0

    def record_failure(self):
        """Record a failed request."""
        self.failures += 1
        self.last_failure = time.time()

    def is_healthy(self, failure_threshold: int = 5, recovery_time: float = 60) -> bool:
        """Check if endpoint is healthy based on circuit breaker state."""
        if self.circuit_state == CircuitState.OPEN:
            # Check if enough time has passed to try again
            if time.time() - self.last_failure > recovery_time:
                self.circuit_state = CircuitState.HALF_OPEN
                return True
            return False

        if self.failures >= failure_threshold:
            self.circuit_state = CircuitState.OPEN
            return False

        return True


@dataclass
class RouteEndpoint:
    """Configuration for a routing endpoint."""

    provider: LLMProvider
    weight: int = 100
    priority: int = 0  # Lower = higher priority (for fallback ordering)
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None  # Optional override
    health: EndpointHealth = field(default_factory=EndpointHealth)

    def __post_init__(self):
        if self.health is None:
            self.health = EndpointHealth()


@dataclass
class RetryConfig:
    """Retry configuration."""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff."""
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random()  # 50-150% of delay
        return delay


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_LATENCY = "least_latency"
    RANDOM = "random"


class LLMRouter:
    """
    LLM Router with load balancing, fallback, and retry.

    Features:
    - Multiple load balancing strategies
    - Automatic fallback on failure
    - Configurable retry with exponential backoff
    - Circuit breaker pattern
    - Health monitoring
    """

    def __init__(
        self,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.WEIGHTED,
        retry_config: Optional[RetryConfig] = None,
        failure_threshold: int = 5,
        recovery_time: float = 60,
    ):
        """
        Initialize LLM Router.

        Args:
            strategy: Load balancing strategy
            retry_config: Retry configuration
            failure_threshold: Number of failures before circuit opens
            recovery_time: Seconds to wait before retrying failed endpoint
        """
        self.strategy = strategy
        self.retry_config = retry_config or RetryConfig()
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.routes: dict[str, list[RouteEndpoint]] = {}
        self._round_robin_index: dict[str, int] = {}

    def add_route(
        self,
        model_pattern: str,
        endpoints: list[RouteEndpoint],
    ) -> None:
        """
        Add routing configuration for a model pattern.

        Args:
            model_pattern: Model name or pattern (e.g., "gpt-4", "gpt-*")
            endpoints: List of endpoint configurations
        """
        # Sort by priority (lower = higher priority)
        endpoints.sort(key=lambda e: e.priority)
        self.routes[model_pattern] = endpoints
        self._round_robin_index[model_pattern] = 0

    def get_endpoints(self, model: str) -> list[RouteEndpoint]:
        """Get endpoints for a model, checking patterns."""
        # Exact match first
        if model in self.routes:
            return self.routes[model]

        # Pattern matching
        for pattern, endpoints in self.routes.items():
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if model.startswith(prefix):
                    return endpoints

        return []

    def _select_endpoint_round_robin(
        self,
        endpoints: list[RouteEndpoint],
        model: str,
    ) -> Optional[RouteEndpoint]:
        """Select endpoint using round-robin."""
        healthy = [
            e
            for e in endpoints
            if e.health.is_healthy(self.failure_threshold, self.recovery_time)
        ]
        if not healthy:
            return None

        idx = self._round_robin_index.get(model, 0) % len(healthy)
        self._round_robin_index[model] = idx + 1
        return healthy[idx]

    def _select_endpoint_weighted(
        self,
        endpoints: list[RouteEndpoint],
    ) -> Optional[RouteEndpoint]:
        """Select endpoint using weighted random selection."""
        healthy = [
            e
            for e in endpoints
            if e.health.is_healthy(self.failure_threshold, self.recovery_time)
        ]
        if not healthy:
            return None

        total_weight = sum(e.weight for e in healthy)
        r = random.uniform(0, total_weight)
        current = 0
        for endpoint in healthy:
            current += endpoint.weight
            if r <= current:
                return endpoint
        return healthy[-1]

    def _select_endpoint_least_latency(
        self,
        endpoints: list[RouteEndpoint],
    ) -> Optional[RouteEndpoint]:
        """Select endpoint with lowest average latency."""
        healthy = [
            e
            for e in endpoints
            if e.health.is_healthy(self.failure_threshold, self.recovery_time)
        ]
        if not healthy:
            return None

        # Prefer endpoints with recorded latency, fallback to first
        with_latency = [e for e in healthy if e.health.request_count > 0]
        if with_latency:
            return min(with_latency, key=lambda e: e.health.avg_latency_ms)
        return healthy[0]

    def _select_endpoint(
        self,
        endpoints: list[RouteEndpoint],
        model: str,
    ) -> Optional[RouteEndpoint]:
        """Select an endpoint based on the configured strategy."""
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._select_endpoint_round_robin(endpoints, model)
        elif self.strategy == LoadBalanceStrategy.WEIGHTED:
            return self._select_endpoint_weighted(endpoints)
        elif self.strategy == LoadBalanceStrategy.LEAST_LATENCY:
            return self._select_endpoint_least_latency(endpoints)
        elif self.strategy == LoadBalanceStrategy.RANDOM:
            healthy = [
                e
                for e in endpoints
                if e.health.is_healthy(self.failure_threshold, self.recovery_time)
            ]
            return random.choice(healthy) if healthy else None
        else:
            return endpoints[0] if endpoints else None

    async def chat(
        self,
        request: ChatRequest,
        api_key: str,
        fallback: bool = True,
    ) -> ChatResponse:
        """
        Route chat request with load balancing, retry, and fallback.

        Args:
            request: Chat request
            api_key: Default API key
            fallback: Whether to fallback to other endpoints on failure

        Returns:
            ChatResponse from successful endpoint

        Raises:
            Exception: If all endpoints fail
        """
        endpoints = self.get_endpoints(request.model)
        if not endpoints:
            raise ValueError(f"No route configured for model: {request.model}")

        errors = []
        tried_endpoints = set()

        for attempt in range(self.retry_config.max_retries + 1):
            # Select endpoint
            available = [e for e in endpoints if id(e) not in tried_endpoints]
            if not available and fallback:
                # All tried, reset for retry with backoff
                tried_endpoints.clear()
                available = endpoints

            endpoint = self._select_endpoint(available, request.model)
            if not endpoint:
                if errors:
                    raise errors[-1]
                raise ValueError(f"No healthy endpoint for model: {request.model}")

            tried_endpoints.add(id(endpoint))
            effective_api_key = endpoint.api_key or api_key

            try:
                start_time = time.time()
                response = await endpoint.provider.chat(request, effective_api_key)
                latency_ms = (time.time() - start_time) * 1000

                # Record success
                endpoint.health.record_success(latency_ms)
                logger.info(
                    f"Request succeeded on {endpoint.provider.name} "
                    f"(latency: {latency_ms:.0f}ms)"
                )
                return response

            except Exception as e:
                endpoint.health.record_failure()
                errors.append(e)
                logger.warning(f"Request failed on {endpoint.provider.name}: {e}")

                # If not last attempt and fallback enabled, try next endpoint
                if fallback and attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    logger.info(f"Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue

        # All attempts failed
        raise Exception(
            f"All endpoints failed for model {request.model}. "
            f"Errors: {[str(e) for e in errors]}"
        )

    def get_health_status(self) -> dict:
        """Get health status for all endpoints."""
        status = {}
        for model, endpoints in self.routes.items():
            status[model] = [
                {
                    "provider": e.provider.name,
                    "healthy": e.health.is_healthy(
                        self.failure_threshold, self.recovery_time
                    ),
                    "circuit_state": e.health.circuit_state.value,
                    "failures": e.health.failures,
                    "successes": e.health.successes,
                    "avg_latency_ms": round(e.health.avg_latency_ms, 2),
                }
                for e in endpoints
            ]
        return status


# Factory function for common configurations
def create_router_with_fallback(
    primary_provider: LLMProvider,
    fallback_providers: list[LLMProvider],
    model_pattern: str = "*",
) -> LLMRouter:
    """
    Create a router with primary and fallback providers.

    Example:
        router = create_router_with_fallback(
            primary_provider=openai_provider,
            fallback_providers=[azure_openai_provider, anthropic_provider],
            model_pattern="gpt-*",
        )
    """
    router = LLMRouter(
        strategy=LoadBalanceStrategy.WEIGHTED,
        retry_config=RetryConfig(max_retries=3),
    )

    endpoints = [
        RouteEndpoint(provider=primary_provider, weight=100, priority=0),
    ]
    for i, provider in enumerate(fallback_providers):
        endpoints.append(RouteEndpoint(provider=provider, weight=50, priority=i + 1))

    router.add_route(model_pattern, endpoints)
    return router


# Default router instance
default_router = LLMRouter()
