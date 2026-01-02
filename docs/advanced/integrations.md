# Integrations

TensorWall integrates with various observability, monitoring, and security platforms.

## Langfuse

[Langfuse](https://langfuse.com) is an open-source LLM observability platform.

### Configuration

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com  # or self-hosted
```

### What's Traced

TensorWall sends to Langfuse:
- Request traces
- LLM generations
- Token usage
- Costs
- Latency
- Security findings

### Trace Structure

```
Trace (tensorwall-{model})
├── Generation (LLM call)
│   ├── Input messages
│   ├── Output content
│   ├── Usage metrics
│   └── Cost
└── Span (security-check) [if findings]
    ├── Finding count
    └── Finding details
```

### Viewing in Langfuse

1. Go to Langfuse dashboard
2. Navigate to **Traces**
3. Filter by `tensorwall` tag
4. View request details, costs, and security findings

### Custom Metadata

Add custom metadata to traces:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "X-Feature": "chatbot",  # Appears in Langfuse
    },
    json={...}
)
```

## Prometheus

Export metrics to Prometheus for monitoring and alerting.

### Configuration

```bash
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
```

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `tensorwall_requests_total` | Counter | Total requests by status |
| `tensorwall_tokens_total` | Counter | Total tokens by model |
| `tensorwall_cost_usd_total` | Counter | Total cost in USD |
| `tensorwall_latency_seconds` | Histogram | Request latency |
| `tensorwall_security_findings_total` | Counter | Security findings by category |
| `tensorwall_circuit_breaker_state` | Gauge | Circuit breaker status |

### Grafana Dashboard

Import the provided dashboard:

```bash
# Import dashboard
curl -X POST http://grafana:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @grafana/tensorwall-dashboard.json
```

### Alerting Rules

Example Prometheus alert rules:

```yaml
groups:
  - name: tensorwall
    rules:
      - alert: HighBlockRate
        expr: rate(tensorwall_requests_total{status="blocked"}[5m]) / rate(tensorwall_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High security block rate"

      - alert: BudgetExceeded
        expr: tensorwall_budget_usage_ratio > 0.9
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Budget nearly exhausted"
```

## OpenTelemetry

Export traces and metrics via OpenTelemetry.

### Configuration

```bash
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=tensorwall
```

### Trace Attributes

TensorWall adds these span attributes:

| Attribute | Description |
|-----------|-------------|
| `llm.model` | Model name |
| `llm.provider` | Provider name |
| `llm.tokens.input` | Input tokens |
| `llm.tokens.output` | Output tokens |
| `tensorwall.decision` | ALLOW/WARN/BLOCK |
| `tensorwall.cost_usd` | Request cost |

### Jaeger Integration

View traces in Jaeger:

```bash
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "4317:4317"
```

## Datadog

Send metrics and traces to Datadog.

### Configuration

```bash
DD_API_KEY=your-datadog-api-key
DD_SITE=datadoghq.com
DD_SERVICE=tensorwall
DD_ENV=production
```

### Metrics

TensorWall exports these metrics:
- `tensorwall.requests`
- `tensorwall.tokens`
- `tensorwall.cost`
- `tensorwall.latency`
- `tensorwall.security.findings`

### APM Traces

Enable Datadog APM:

```bash
DD_TRACE_ENABLED=true
DD_PROFILING_ENABLED=true
```

## Slack

Send alerts to Slack channels.

### Configuration

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
SLACK_CHANNEL=#llm-alerts
```

### Alert Types

| Alert | Trigger |
|-------|---------|
| Security Block | High-severity security finding |
| Budget Warning | Budget at 80% |
| Budget Exceeded | Budget exhausted |
| Provider Down | Provider circuit breaker open |

### Message Format

```
🚨 TensorWall Security Alert

App: my-app
Request: req_abc123
Category: prompt_injection
Severity: HIGH

Details: Potential prompt injection: instruction_override

View in Dashboard →
```

## PagerDuty

Integrate with PagerDuty for on-call alerting.

### Configuration

```bash
PAGERDUTY_ROUTING_KEY=your-routing-key
PAGERDUTY_SERVICE_ID=your-service-id
```

### Incident Triggers

| Severity | PagerDuty Action |
|----------|------------------|
| Critical | Create incident, page on-call |
| High | Create incident |
| Medium | Create event |
| Low | Log only |

## Webhooks

Send events to custom webhook endpoints.

### Configuration

```bash
WEBHOOK_URL=https://your-service.com/webhook
WEBHOOK_SECRET=your-webhook-secret
```

### Event Types

| Event | Description |
|-------|-------------|
| `request.blocked` | Request blocked by security |
| `budget.warning` | Budget threshold reached |
| `budget.exceeded` | Budget exhausted |
| `provider.down` | Provider unavailable |

### Payload Format

```json
{
  "event": "request.blocked",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "request_id": "req_abc123",
    "app_id": "app_1",
    "model": "gpt-4o",
    "findings": [...]
  },
  "signature": "sha256=..."
}
```

### Signature Verification

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## SIEM Integration

Export security events to SIEM systems.

### Splunk

```bash
SPLUNK_HEC_URL=https://splunk.example.com:8088
SPLUNK_HEC_TOKEN=your-hec-token
SPLUNK_INDEX=tensorwall
```

### Elastic (ELK)

```bash
ELASTICSEARCH_URL=https://elasticsearch:9200
ELASTICSEARCH_INDEX=tensorwall-security
ELASTICSEARCH_API_KEY=your-api-key
```

### Log Format

Security events are logged in JSON format:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "event_type": "security_finding",
  "request_id": "req_abc123",
  "app_id": "app_1",
  "finding": {
    "category": "prompt_injection",
    "severity": "high",
    "description": "..."
  }
}
```

## Database Export

Export analytics to external databases.

### PostgreSQL (TimescaleDB)

```bash
ANALYTICS_DB_URL=postgresql://user:pass@timescale:5432/analytics
ANALYTICS_EXPORT_INTERVAL=60
```

### ClickHouse

```bash
CLICKHOUSE_URL=http://clickhouse:8123
CLICKHOUSE_DATABASE=tensorwall
```

## Custom Integrations

Create custom integrations using the adapter pattern:

```python
from backend.adapters.observability import ObservabilityAdapter

class CustomAdapter(ObservabilityAdapter):
    """Custom observability adapter."""

    async def trace_request(
        self,
        request_id: str,
        app_id: str,
        model: str,
        **kwargs
    ) -> None:
        # Send to your system
        await self.client.send({
            "request_id": request_id,
            "app_id": app_id,
            "model": model,
            **kwargs
        })
```

Register the adapter:

```python
from backend.adapters.observability import register_adapter

register_adapter("custom", CustomAdapter())
```
