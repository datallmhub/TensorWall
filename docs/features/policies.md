# Policy Engine

TensorWall's Policy Engine evaluates rules **before** each LLM call to determine if the request should be allowed, warned, or blocked.

## Policy Types

| Type | Description | Example |
|------|-------------|---------|
| `model_restriction` | Block specific models | Block GPT-4 in development |
| `token_limit` | Limit max tokens | Max 2000 tokens per request |
| `rate_limit` | Limit request frequency | 100 requests/minute |
| `time_restriction` | Restrict by time | No requests after 6PM |
| `environment_restriction` | Restrict by environment | Block production models in dev |

## Policy Actions

| Action | Behavior |
|--------|----------|
| `ALLOW` | Request proceeds normally |
| `WARN` | Request proceeds, warning logged |
| `DENY` | Request blocked with error |

## Creating Policies

### Via Dashboard

1. Go to **Policies** → **Create Policy**
2. Select policy type
3. Configure conditions
4. Choose action (ALLOW/WARN/DENY)
5. Set priority (lower = higher priority)

### Via API

```bash
curl -X POST http://localhost:8000/admin/policies \
  -H "Cookie: access_token=..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block GPT-4 in Development",
    "description": "Prevent expensive models in dev",
    "application_id": 1,
    "rule_type": "model_restriction",
    "conditions": {
      "models": ["gpt-4", "gpt-4-turbo"],
      "environments": ["development"]
    },
    "action": "DENY",
    "priority": 100,
    "is_enabled": true
  }'
```

## Policy Examples

### Block Expensive Models in Dev

```json
{
  "name": "Block GPT-4 in Dev",
  "rule_type": "model_restriction",
  "conditions": {
    "models": ["gpt-4", "gpt-4-turbo", "claude-3-opus"],
    "environments": ["development"]
  },
  "action": "DENY"
}
```

### Warn on High Token Usage

```json
{
  "name": "Warn High Tokens",
  "rule_type": "token_limit",
  "conditions": {
    "max_tokens": 4000
  },
  "action": "WARN"
}
```

### Rate Limit per Application

```json
{
  "name": "Rate Limit",
  "rule_type": "rate_limit",
  "conditions": {
    "requests_per_minute": 60
  },
  "action": "DENY"
}
```

## Policy Evaluation

Policies are evaluated in priority order (lower priority number = evaluated first):

1. All matching policies are collected
2. Evaluated from lowest to highest priority
3. First DENY stops evaluation
4. WARN is accumulated
5. ALLOW is default if no DENY

## Dry-Run Mode

Test policies without making actual LLM calls:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_xxx" \
  -H "X-Dry-Run: true" \
  -d '{"model": "gpt-4", "messages": [...]}'
```

Response:
```json
{
  "dry_run": true,
  "decision": "DENY",
  "policy_matches": [
    {
      "name": "Block GPT-4 in Dev",
      "action": "DENY",
      "reason": "Model gpt-4 blocked in development"
    }
  ]
}
```

## Debug Mode

Include full decision trace in responses:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-Debug: true" \
  ...
```

Response includes `_tensorwall.policies` with all evaluated rules.
