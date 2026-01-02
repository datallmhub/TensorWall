# Observability

TensorWall provides comprehensive observability for LLM operations.

## Built-in Features

### Request Tracing

Every request is traced with:
- Unique request ID
- Timestamps (start, end)
- Latency measurements
- Token counts (input, output)
- Cost estimation
- Decision (ALLOW/WARN/BLOCK)
- Security findings

### Dashboard Analytics

The admin dashboard shows:
- Requests over time
- Cost by application/model
- Latency percentiles
- Error rates
- Security events

## Langfuse Integration

[Langfuse](https://langfuse.com) is an open-source LLM observability platform.

### Setup

1. Create a Langfuse account at https://cloud.langfuse.com
2. Create a project and get API keys
3. Configure TensorWall:

```bash
export LANGFUSE_PUBLIC_KEY="pk-..."
export LANGFUSE_SECRET_KEY="sk-..."
docker-compose up -d
```

### What Gets Sent

TensorWall sends to Langfuse:
- **Traces**: Full request lifecycle
- **Generations**: LLM call details (model, tokens, cost)
- **Spans**: Security checks, policy evaluation
- **Metadata**: TensorWall decision, security findings

### Example Trace

```
Trace: tensorwall-gpt-4o
├── Generation: gpt-4o
│   ├── Input: [messages]
│   ├── Output: "response..."
│   ├── Usage: {input: 150, output: 50}
│   └── Cost: $0.003
└── Span: security-check
    └── Findings: []
```

## Prometheus Metrics

TensorWall exposes Prometheus metrics at `/metrics`:

### Available Metrics

```prometheus
# Request latency histogram
tensorwall_request_latency_seconds_bucket{model="gpt-4o",le="0.5"} 100
tensorwall_request_latency_seconds_bucket{model="gpt-4o",le="1.0"} 150

# Request counter
tensorwall_requests_total{model="gpt-4o",status="success"} 1000
tensorwall_requests_total{model="gpt-4o",status="blocked"} 5

# Token usage
tensorwall_tokens_total{model="gpt-4o",type="input"} 150000
tensorwall_tokens_total{model="gpt-4o",type="output"} 50000

# Cost
tensorwall_cost_usd_total{model="gpt-4o",app="my-app"} 45.30

# Security events
tensorwall_security_findings_total{category="prompt_injection"} 12
```

### Grafana Dashboard

Import our pre-built Grafana dashboard:

```bash
# Coming soon
curl -o tensorwall-dashboard.json https://...
```

## Debug Mode

Enable detailed logging per-request:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-Debug: true" \
  ...
```

Response includes `_tensorwall` metadata:

```json
{
  "choices": [...],
  "_tensorwall": {
    "request_id": "req_abc123",
    "decision": "ALLOW",
    "security": {
      "safe": true,
      "risk_score": 0.0,
      "findings": []
    },
    "policies": {
      "evaluated": 3,
      "matched": 0
    },
    "budget": {
      "current_spend": 45.30,
      "limit": 100.00
    },
    "cost_usd": 0.003,
    "latency_ms": 450
  }
}
```

## Audit Logs

All requests are logged to the database for audit:

```sql
SELECT
  request_id,
  app_id,
  model,
  decision,
  cost_usd,
  created_at
FROM llm_request_traces
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

Configure retention:
```bash
AUDIT_RETENTION_DAYS=90  # Keep logs for 90 days
```

## Log Levels

Configure logging verbosity:

```bash
# In development
LOG_LEVEL=DEBUG

# In production
LOG_LEVEL=INFO
```

Logs include:
- Request received
- Authentication result
- Policy evaluation
- Security check
- Provider selection
- Response sent
