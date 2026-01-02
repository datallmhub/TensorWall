# Admin API

The Admin API provides endpoints for managing TensorWall configuration, applications, policies, and monitoring.

## Authentication

Admin endpoints require authentication via session cookie or JWT token:

```http
Cookie: session=xxx
# or
Authorization: Bearer eyJhbG...
```

## Applications

### List Applications

```http
GET /admin/applications
```

Response:
```json
{
  "applications": [
    {
      "id": 1,
      "name": "My App",
      "api_key_prefix": "gw_abc",
      "owner": "developer@example.com",
      "created_at": "2024-01-01T00:00:00Z",
      "is_active": true
    }
  ],
  "total": 1
}
```

### Create Application

```http
POST /admin/applications
Content-Type: application/json

{
  "name": "New App",
  "owner": "developer@example.com",
  "description": "My new application"
}
```

Response:
```json
{
  "id": 2,
  "name": "New App",
  "api_key": "gw_abc123_xxxxxxxxxxxx",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Note:** The full API key is only returned once at creation.

### Get Application

```http
GET /admin/applications/{id}
```

### Update Application

```http
PUT /admin/applications/{id}
Content-Type: application/json

{
  "name": "Updated Name",
  "is_active": true
}
```

### Delete Application

```http
DELETE /admin/applications/{id}
```

### Regenerate API Key

```http
POST /admin/applications/{id}/regenerate-key
```

## Policies

### List Policies

```http
GET /admin/policies
```

Response:
```json
{
  "policies": [
    {
      "id": 1,
      "name": "production-policy",
      "rules": [...],
      "priority": 100,
      "enabled": true
    }
  ]
}
```

### Create Policy

```http
POST /admin/policies
Content-Type: application/json

{
  "name": "my-policy",
  "rules": [
    {
      "condition": {"model": {"in": ["gpt-4o"]}},
      "action": "allow"
    }
  ],
  "priority": 100
}
```

### Update Policy

```http
PUT /admin/policies/{id}
Content-Type: application/json

{
  "rules": [...],
  "enabled": true
}
```

### Delete Policy

```http
DELETE /admin/policies/{id}
```

## Budgets

### List Budgets

```http
GET /admin/budgets
```

Response:
```json
{
  "budgets": [
    {
      "id": 1,
      "app_id": 1,
      "type": "monthly",
      "limit_usd": 100.00,
      "current_spend_usd": 45.50,
      "reset_day": 1
    }
  ]
}
```

### Create Budget

```http
POST /admin/budgets
Content-Type: application/json

{
  "app_id": 1,
  "type": "monthly",
  "limit_usd": 100.00,
  "reset_day": 1,
  "alert_threshold": 0.8
}
```

### Update Budget

```http
PUT /admin/budgets/{id}
Content-Type: application/json

{
  "limit_usd": 150.00
}
```

### Delete Budget

```http
DELETE /admin/budgets/{id}
```

## Analytics

### Usage Summary

```http
GET /admin/analytics/summary?period=30d
```

Response:
```json
{
  "period": "30d",
  "total_requests": 15234,
  "total_tokens": 2500000,
  "total_cost_usd": 125.50,
  "by_model": {
    "gpt-4o": {"requests": 5000, "cost": 75.00},
    "gpt-4o-mini": {"requests": 10234, "cost": 50.50}
  },
  "by_app": {
    "1": {"requests": 10000, "cost": 80.00},
    "2": {"requests": 5234, "cost": 45.50}
  }
}
```

### Request History

```http
GET /admin/analytics/requests?limit=100&offset=0
```

Response:
```json
{
  "requests": [
    {
      "id": "req_abc123",
      "app_id": 1,
      "model": "gpt-4o",
      "input_tokens": 100,
      "output_tokens": 150,
      "cost_usd": 0.005,
      "latency_ms": 450,
      "decision": "ALLOW",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 15234
}
```

### Time Series

```http
GET /admin/analytics/timeseries?metric=requests&period=7d&interval=1h
```

Response:
```json
{
  "metric": "requests",
  "period": "7d",
  "interval": "1h",
  "data": [
    {"timestamp": "2024-01-01T00:00:00Z", "value": 150},
    {"timestamp": "2024-01-01T01:00:00Z", "value": 125},
    ...
  ]
}
```

## Security

### Security Findings

```http
GET /admin/security/findings?severity=high&limit=50
```

Response:
```json
{
  "findings": [
    {
      "request_id": "req_abc123",
      "app_id": 1,
      "category": "prompt_injection",
      "severity": "high",
      "description": "Instruction override detected",
      "detected_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 25
}
```

### Security Stats

```http
GET /admin/security/stats?period=30d
```

Response:
```json
{
  "total_scanned": 15234,
  "total_blocked": 45,
  "total_warned": 123,
  "by_category": {
    "prompt_injection": 30,
    "pii_detection": 50,
    "secrets_detection": 15
  },
  "block_rate": 0.003
}
```

## Users

### List Users

```http
GET /admin/users
```

### Create User

```http
POST /admin/users
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure-password",
  "role": "viewer"
}
```

### Update User

```http
PUT /admin/users/{id}
Content-Type: application/json

{
  "role": "admin"
}
```

### Delete User

```http
DELETE /admin/users/{id}
```

## Health & Status

### System Health

```http
GET /health/live
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Detailed Health

```http
GET /health/ready
```

Response:
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "providers": {
      "openai": "healthy",
      "anthropic": "healthy"
    }
  }
}
```

### Version Info

```http
GET /version
```

Response:
```json
{
  "version": "0.2.0",
  "build": "abc1234",
  "environment": "production"
}
```

## Error Responses

### Unauthorized

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

### Forbidden

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions"
  }
}
```

### Not Found

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```

### Validation Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request body",
    "details": {
      "name": "Field is required"
    }
  }
}
```

## Rate Limiting

Admin API endpoints are rate-limited:

| Endpoint | Limit |
|----------|-------|
| Read operations | 100/minute |
| Write operations | 30/minute |
| Analytics queries | 20/minute |

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067260
```
