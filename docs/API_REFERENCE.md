# LLM Gateway API Reference

**Version:** 0.1.0
**Base URL:** `https://api.your-domain.com`

## Overview

The LLM Governance Gateway provides an OpenAI-compatible API with enterprise governance features including policy enforcement, budget control, multi-tenancy, and comprehensive audit logging.

## Authentication

All API requests require authentication via the `X-API-Key` header.

```bash
curl -X POST https://api.example.com/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Authorization: Bearer sk-your-openai-key" \
  -H "Content-Type: application/json"
```

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Gateway API key for authentication |
| `Authorization` | Conditional | `Bearer <LLM_KEY>` required for real LLM calls |

## Common Headers

| Header | Description |
|--------|-------------|
| `X-Debug` | Set to `true` to include decision chain in response |
| `X-Dry-Run` | Set to `true` to simulate without LLM call |
| `X-Feature-Id` | Feature/use-case identifier for allowlisting |
| `X-Organization-Id` | Tenant organization ID |
| `X-LLM-Contract` | JSON usage contract |

---

## LLM API Endpoints

### POST /v1/chat/completions

Create a chat completion with governance.

**Request:**

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "max_tokens": 500,
  "temperature": 0.7,
  "stream": false,
  "contract": {
    "app_id": "my-app",
    "feature": "customer-support",
    "action": "generate",
    "environment": "production"
  }
}
```

**Response (200 OK):**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1702847123,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 10,
    "total_tokens": 35
  },
  "gateway_metadata": {
    "request_id": "req_550e8400-e29b-41d4-a716-446655440000",
    "decision_id": "dec_123456",
    "latency_ms": 234,
    "cost_usd": 0.000425
  }
}
```

**Dry-Run Response (X-Dry-Run: true):**

```json
{
  "dry_run": true,
  "request_id": "req_550e8400...",
  "would_be_allowed": false,
  "blocking_reason": "Policy 'Block GPT-4 in production'",
  "decision_chain": {
    "final_outcome": "deny",
    "total_decisions": 5
  },
  "policies_evaluated": 3,
  "policies_blocking": [
    {
      "policy_id": "policy-001",
      "policy_name": "Block GPT-4 in production",
      "action": "deny"
    }
  ],
  "recommendations": ["Use gpt-4o-mini instead"]
}
```

### POST /v1/embeddings

Create embeddings with governance.

**Request:**

```json
{
  "model": "text-embedding-3-small",
  "input": "The quick brown fox jumps over the lazy dog."
}
```

---

## Admin API Endpoints

### Tenants

#### GET /admin/tenants

List all organizations.

**Response:**

```json
{
  "organizations": [
    {
      "id": "org_abc123",
      "name": "Acme Corp",
      "slug": "acme-corp",
      "status": "active",
      "tier": "professional",
      "max_applications": 25
    }
  ],
  "total": 1
}
```

#### POST /admin/tenants

Create a new organization.

**Request:**

```json
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "owner_email": "admin@acme.com",
  "tier": "professional"
}
```

#### GET /admin/tenants/{org_id}

Get organization details.

#### PATCH /admin/tenants/{org_id}

Update organization settings.

#### GET /admin/tenants/{org_id}/limits

Get resource limits and current usage.

**Response:**

```json
{
  "organization_id": "org_abc123",
  "limits": [
    {"resource_type": "applications", "current": 5, "max": 25, "within_limits": true},
    {"resource_type": "api_keys", "current": 12, "max": 500, "within_limits": true},
    {"resource_type": "users", "current": 8, "max": 100, "within_limits": true}
  ]
}
```

### Applications

#### GET /admin/tenants/{org_id}/applications

List applications for an organization.

#### POST /admin/tenants/{org_id}/applications

Create a new application.

**Request:**

```json
{
  "name": "Customer Support Bot",
  "description": "AI chatbot for inquiries",
  "environments": ["development", "staging", "production"],
  "budget_limit_usd": 1000.00,
  "rate_limit_rpm": 100
}
```

#### GET /admin/tenants/{org_id}/applications/{app_id}

Get application details.

#### DELETE /admin/tenants/{org_id}/applications/{app_id}

Deactivate an application.

---

### Plans & Licensing

#### GET /admin/plans

List all available plans.

**Response:**

```json
{
  "plans": [
    {
      "id": "plan_free",
      "name": "Free",
      "tier": "free",
      "price_monthly_usd": 0,
      "limits": {
        "max_applications": 1,
        "max_requests_per_month": 10000,
        "rate_limit_rpm": 60
      }
    },
    {
      "id": "plan_professional",
      "name": "Professional",
      "tier": "professional",
      "price_monthly_usd": 199,
      "limits": {
        "max_applications": 25,
        "max_requests_per_month": 1000000,
        "rate_limit_rpm": 1000
      }
    }
  ]
}
```

#### GET /admin/plans/{tier}

Get details of a specific plan.

#### GET /admin/plans/compare

Compare all plans side by side.

#### GET /admin/plans/subscriptions/{org_id}

Get subscription for an organization.

#### POST /admin/plans/subscriptions/{org_id}

Create or update subscription.

**Query Parameters:**
- `tier` (string): Plan tier (free, starter, professional, enterprise)
- `trial_days` (int): Trial period in days

#### PATCH /admin/plans/subscriptions/{org_id}/upgrade

Upgrade to a new plan.

#### GET /admin/plans/usage/{org_id}

Get current usage for an organization.

**Response:**

```json
{
  "organization_id": "org_abc123",
  "plan_tier": "professional",
  "requests": {
    "used": 45000,
    "limit": 1000000,
    "remaining": 955000,
    "percent_used": 4.5
  },
  "tokens": {
    "used": 2500000,
    "limit": 50000000,
    "remaining": 47500000,
    "percent_used": 5.0
  },
  "spend_usd": {
    "used": 125.50,
    "limit": 5000,
    "remaining": 4874.50,
    "percent_used": 2.51
  },
  "rate_limits": {
    "requests_per_minute": 1000,
    "tokens_per_minute": 100000
  }
}
```

#### GET /admin/plans/features/{org_id}/{feature}

Check if a feature is available.

#### GET /admin/plans/features

List all available features.

---

### Policies

#### GET /admin/policies

List all policies.

#### POST /admin/policies

Create a new policy.

**Request:**

```json
{
  "name": "Block GPT-4 in Production",
  "description": "Prevent GPT-4 usage in production",
  "rule_type": "model_restriction",
  "conditions": {
    "models": ["gpt-4", "gpt-4-turbo"],
    "environment": "production"
  },
  "action": "deny",
  "priority": 100,
  "enabled": true
}
```

#### GET /admin/policies/{policy_id}

Get policy details.

#### PATCH /admin/policies/{policy_id}

Update a policy.

#### DELETE /admin/policies/{policy_id}

Delete a policy.

---

### Budgets

#### GET /admin/budgets

List all budgets.

#### POST /admin/budgets

Create a budget.

**Request:**

```json
{
  "app_id": "my-app",
  "feature": "customer-support",
  "environment": "production",
  "soft_limit_usd": 400.00,
  "hard_limit_usd": 500.00,
  "period": "monthly"
}
```

#### GET /admin/budgets/{budget_id}

Get budget details and current usage.

---

### Features (Use-Case Allowlisting)

#### GET /admin/features

List all registered features.

#### POST /admin/features

Register a new feature.

**Request:**

```json
{
  "id": "customer-support",
  "name": "Customer Support Chat",
  "description": "AI-powered customer support",
  "allowed_actions": ["chat", "analyze"],
  "allowed_models": ["gpt-4o", "gpt-4o-mini"],
  "allowed_environments": ["development", "staging", "production"],
  "max_tokens_per_request": 2000,
  "max_cost_per_request_usd": 0.10,
  "require_data_separation": true
}
```

---

### Analytics

#### GET /admin/analytics/usage

Get usage statistics.

**Query Parameters:**
- `app_id` (string): Filter by application
- `start_date` (date): Start of period
- `end_date` (date): End of period
- `group_by` (string): Grouping (day, week, month)

#### GET /admin/analytics/audit

Get audit logs.

**Query Parameters:**
- `app_id` (string): Filter by application
- `decision` (string): Filter by decision (allow, deny)
- `limit` (int): Number of records
- `offset` (int): Pagination offset

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "details": {}
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `authentication_required` | 401 | No API key provided |
| `invalid_api_key` | 401 | Invalid or revoked key |
| `request_denied` | 403 | Blocked by policy |
| `feature_not_allowed` | 403 | Use-case not permitted |
| `budget_would_exceed` | 429 | Budget limit reached |
| `rate_limit_exceeded` | 429 | Too many requests |
| `plan_limit_exceeded` | 429 | Monthly limit reached |
| `tenant_validation_failed` | 403 | Invalid organization |
| `input_validation_failed` | 400 | Invalid input detected |

---

## Decision Codes

When `X-Debug: true` is set, responses include decision details:

### Authentication
- `AUTH_SUCCESS` - Authentication successful
- `AUTH_MISSING_KEY` - No API key provided
- `AUTH_INVALID_KEY` - Invalid API key

### Feature Check
- `FEATURE_ALLOWED` - Feature/action allowed
- `FEATURE_UNKNOWN` - Unknown feature
- `FEATURE_MODEL_FORBIDDEN` - Model not allowed

### Policy Check
- `POLICY_ALLOWED` - All policies passed
- `POLICY_MODEL_BLOCKED` - Model blocked by policy
- `POLICY_TOKEN_LIMIT` - Token limit exceeded

### Budget Check
- `BUDGET_OK` - Within budget
- `BUDGET_WARNING` - Approaching limit
- `BUDGET_EXCEEDED` - Budget exceeded
- `BUDGET_FORECAST_EXCEEDED` - Projected to exceed

### Security Check
- `SECURITY_CLEAN` - No issues detected
- `SECURITY_INJECTION_DETECTED` - Prompt injection detected
- `SECURITY_PII_DETECTED` - PII detected

---

## Rate Limits

Rate limits vary by plan tier:

| Tier | Requests/min | Tokens/min | Monthly Requests |
|------|-------------|------------|------------------|
| Free | 60 | 10,000 | 10,000 |
| Starter | 300 | 50,000 | 100,000 |
| Professional | 1,000 | 100,000 | 1,000,000 |
| Enterprise | Custom | Custom | Unlimited |

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

---

## Webhooks

Configure webhooks in organization settings to receive events:

- `request.completed` - LLM request completed
- `request.denied` - Request blocked by policy
- `budget.warning` - Approaching budget limit
- `budget.exceeded` - Budget exceeded
- `security.alert` - Security issue detected

---

## SDKs

### Python

```bash
pip install llm-gateway-sdk
```

```python
from llm_gateway import GatewayClient

client = GatewayClient(
    gateway_url="https://api.example.com",
    api_key="gw_your_key",
    llm_key="sk-your-openai-key"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
    feature_id="customer-support"
)
```

### JavaScript/TypeScript

```bash
npm install @llm-gateway/sdk
```

```typescript
import { GatewayClient } from '@llm-gateway/sdk';

const client = new GatewayClient({
  gatewayUrl: 'https://api.example.com',
  apiKey: 'gw_your_key',
  llmKey: 'sk-your-openai-key'
});

const response = await client.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Hello!' }],
  featureId: 'customer-support'
});
```
