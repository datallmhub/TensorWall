# Budget Control

TensorWall tracks LLM spending and enforces budget limits per application, user, or organization.

## Budget Types

| Scope | Description |
|-------|-------------|
| `APPLICATION` | Budget for a specific application |
| `USER` | Budget for a specific user |
| `ORGANIZATION` | Budget for an entire organization |
| `FEATURE` | Budget for a specific feature/use-case |

## Budget Periods

| Period | Description |
|--------|-------------|
| `DAILY` | Resets every day at midnight UTC |
| `WEEKLY` | Resets every Monday at midnight UTC |
| `MONTHLY` | Resets on the 1st of each month |
| `QUARTERLY` | Resets every 3 months |
| `YEARLY` | Resets on January 1st |

## Limit Types

| Limit | Behavior |
|-------|----------|
| **Soft Limit** | Warning logged, request proceeds |
| **Hard Limit** | Request blocked with error |

## Creating Budgets

### Via Dashboard

1. Go to **Budgets** → **Create Budget**
2. Select scope (Application, User, etc.)
3. Set soft and hard limits (USD)
4. Choose period
5. Save

### Via API

```bash
curl -X POST http://localhost:8000/admin/budgets \
  -H "Cookie: access_token=..." \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "APPLICATION",
    "application_id": 1,
    "soft_limit_usd": 50.0,
    "hard_limit_usd": 100.0,
    "period": "MONTHLY",
    "is_active": true
  }'
```

## Budget Response

When a request exceeds limits:

### Soft Limit Exceeded
```json
{
  "id": "chatcmpl-xxx",
  "choices": [...],
  "_tensorwall": {
    "budget_warning": "Soft limit exceeded: $52.30 / $50.00"
  }
}
```

### Hard Limit Exceeded
```json
{
  "error": {
    "code": "BUDGET_EXCEEDED",
    "message": "Hard budget limit exceeded",
    "details": {
      "current_spend": 102.50,
      "hard_limit": 100.00,
      "period": "MONTHLY"
    }
  }
}
```

## Cost Tracking

TensorWall estimates costs based on token usage and model pricing:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| claude-3-sonnet | $3.00 | $15.00 |
| claude-3-haiku | $0.25 | $1.25 |

## Viewing Spend

### Dashboard

Go to **Budgets** to see:
- Current spend vs limits
- Spend by day/week/month
- Spend by model
- Spend by application

### API

```bash
# Get budget status
curl http://localhost:8000/admin/budgets/1 \
  -H "Cookie: access_token=..."
```

Response:
```json
{
  "id": 1,
  "scope": "APPLICATION",
  "soft_limit_usd": 50.0,
  "hard_limit_usd": 100.0,
  "current_spend_usd": 32.45,
  "period": "MONTHLY",
  "period_start": "2024-01-01T00:00:00Z",
  "utilization_percent": 32.45
}
```

## Alerts

Configure alerts when approaching limits:

| Threshold | Action |
|-----------|--------|
| 50% of soft limit | Log warning |
| 80% of soft limit | Email alert |
| 100% of soft limit | Log + Email |
| 100% of hard limit | Block + Email |

Configure email alerts via environment variables:
```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=xxx
ALERT_FROM_EMAIL=alerts@tensorwall.io
```
