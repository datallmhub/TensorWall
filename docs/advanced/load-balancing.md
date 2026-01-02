# Load Balancing & Reliability

TensorWall includes enterprise-grade routing with load balancing, automatic fallback, and retry logic.

## LLM Router

The `LLMRouter` manages traffic distribution across multiple LLM endpoints.

### Basic Setup

```python
from backend.application.engines.router import (
    LLMRouter,
    RouteEndpoint,
    LoadBalanceStrategy,
    RetryConfig,
)
from backend.application.providers import openai_provider, azure_openai_provider

# Create router
router = LLMRouter(
    strategy=LoadBalanceStrategy.WEIGHTED,
    retry_config=RetryConfig(max_retries=3),
)

# Add route with multiple endpoints
router.add_route("gpt-4", [
    RouteEndpoint(provider=openai_provider, weight=70, priority=0),
    RouteEndpoint(provider=azure_openai_provider, weight=30, priority=1),
])

# Make request
response = await router.chat(request, api_key)
```

## Load Balancing Strategies

### Round Robin

Distributes requests evenly across healthy endpoints:

```python
router = LLMRouter(strategy=LoadBalanceStrategy.ROUND_ROBIN)
```

### Weighted

Routes based on configured weights (default):

```python
router = LLMRouter(strategy=LoadBalanceStrategy.WEIGHTED)

# 70% to OpenAI, 30% to Azure
router.add_route("gpt-4", [
    RouteEndpoint(provider=openai_provider, weight=70),
    RouteEndpoint(provider=azure_openai_provider, weight=30),
])
```

### Least Latency

Routes to the endpoint with lowest average latency:

```python
router = LLMRouter(strategy=LoadBalanceStrategy.LEAST_LATENCY)
```

### Random

Random selection from healthy endpoints:

```python
router = LLMRouter(strategy=LoadBalanceStrategy.RANDOM)
```

## Automatic Fallback

When an endpoint fails, traffic automatically routes to the next priority:

```python
router.add_route("gpt-4", [
    RouteEndpoint(provider=openai_provider, priority=0),    # Primary
    RouteEndpoint(provider=azure_provider, priority=1),     # Fallback 1
    RouteEndpoint(provider=anthropic_provider, priority=2), # Fallback 2
])
```

## Retry Configuration

Configure retry behavior with exponential backoff:

```python
retry_config = RetryConfig(
    max_retries=3,           # Maximum retry attempts
    base_delay=1.0,          # Initial delay (seconds)
    max_delay=30.0,          # Maximum delay
    exponential_base=2.0,    # Exponential factor
    jitter=True,             # Add random jitter
)

router = LLMRouter(retry_config=retry_config)
```

### Retry Delays

With default config:
- Attempt 1: immediate
- Attempt 2: ~1-2 seconds
- Attempt 3: ~2-4 seconds
- Attempt 4: ~4-8 seconds

## Circuit Breaker

The router includes a circuit breaker to prevent cascading failures:

### States

| State | Behavior |
|-------|----------|
| **CLOSED** | Normal operation, requests flow through |
| **OPEN** | Endpoint failing, requests blocked |
| **HALF_OPEN** | Testing if endpoint recovered |

### Configuration

```python
router = LLMRouter(
    failure_threshold=5,    # Failures before circuit opens
    recovery_time=60,       # Seconds before retrying
)
```

### How It Works

1. Endpoint fails 5 times → Circuit opens
2. Wait 60 seconds → Circuit half-opens
3. Send test request:
   - Success → Circuit closes (normal operation)
   - Failure → Circuit opens again

## Health Monitoring

Check endpoint health:

```python
health = router.get_health_status()
print(health)
```

Output:
```json
{
  "gpt-4": [
    {
      "provider": "openai",
      "healthy": true,
      "circuit_state": "closed",
      "failures": 0,
      "successes": 1523,
      "avg_latency_ms": 450.5
    },
    {
      "provider": "azure_openai",
      "healthy": true,
      "circuit_state": "closed",
      "failures": 2,
      "successes": 342,
      "avg_latency_ms": 520.3
    }
  ]
}
```

## Factory Functions

Quick setup with common patterns:

```python
from backend.application.engines.router import create_router_with_fallback
from backend.application.providers import openai_provider, azure_openai_provider

# Primary with fallback
router = create_router_with_fallback(
    primary_provider=openai_provider,
    fallback_providers=[azure_openai_provider],
    model_pattern="gpt-*",
)
```

## Best Practices

1. **Set appropriate weights** based on cost and performance
2. **Use priority for fallback** ordering (lower = higher priority)
3. **Configure retry** based on your latency requirements
4. **Monitor health** to detect provider issues
5. **Test failover** before production
