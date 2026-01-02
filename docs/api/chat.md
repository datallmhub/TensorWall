# Chat Completions API

The Chat Completions API is the primary endpoint for interacting with LLMs through TensorWall.

## Endpoint

```
POST /v1/chat/completions
```

## Authentication

Two headers are required:

| Header | Description | Required |
|--------|-------------|----------|
| `X-API-Key` | TensorWall application API key | Yes |
| `Authorization` | LLM provider API key (Bearer token) | Depends on provider |

## Request

### Headers

```http
POST /v1/chat/completions HTTP/1.1
Host: localhost:8000
X-API-Key: gw_xxxx
Authorization: Bearer sk-your-llm-key
Content-Type: application/json
```

### Optional Headers

| Header | Type | Description |
|--------|------|-------------|
| `X-Dry-Run` | boolean | Test without making LLM call |
| `X-Debug` | boolean | Include TensorWall metadata in response |
| `X-Feature` | string | Feature tag for analytics |
| `X-Request-ID` | string | Custom request ID |

### Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model identifier |
| `messages` | array | Yes | Array of message objects |
| `temperature` | number | No | Sampling temperature (0-2) |
| `max_tokens` | integer | No | Maximum tokens to generate |
| `top_p` | number | No | Nucleus sampling parameter |
| `stream` | boolean | No | Enable streaming response |
| `tools` | array | No | Available tools/functions |
| `tool_choice` | string/object | No | Tool selection strategy |
| `response_format` | object | No | Response format (e.g., JSON mode) |
| `stop` | string/array | No | Stop sequences |

### Message Object

```json
{
  "role": "user",
  "content": "Hello, how are you?"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | `system`, `user`, `assistant`, or `tool` |
| `content` | string/array | Message content (text or multimodal) |
| `name` | string | Optional name for the message author |
| `tool_calls` | array | Tool calls made by assistant |
| `tool_call_id` | string | ID of tool call being responded to |

### Multimodal Content

For vision models:

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What's in this image?"},
    {
      "type": "image_url",
      "image_url": {"url": "https://example.com/image.jpg"}
    }
  ]
}
```

## Response

### Success Response

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```

### Debug Response

When `X-Debug: true`:

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "gpt-4o",
  "choices": [...],
  "usage": {...},
  "_tensorwall": {
    "request_id": "req_abc123",
    "decision": "ALLOW",
    "security": {
      "safe": true,
      "risk_level": "low",
      "risk_score": 0.0,
      "findings": []
    },
    "cost_usd": 0.002,
    "latency_ms": 450,
    "provider": "openai"
  }
}
```

### Dry-Run Response

When `X-Dry-Run: true`:

```json
{
  "dry_run": true,
  "decision": "ALLOW",
  "request_id": "req_abc123",
  "estimated_cost": 0.003,
  "estimated_tokens": {
    "input": 50,
    "output": 100
  },
  "security": {
    "safe": true,
    "risk_level": "low",
    "risk_score": 0.0,
    "findings": []
  },
  "policies": {
    "matched": ["default-allow"],
    "blocked": []
  }
}
```

## Streaming

Enable streaming with `"stream": true`:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_xxx" \
  -H "Authorization: Bearer sk-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'
```

### Stream Format

Server-Sent Events (SSE):

```
data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","choices":[{"delta":{"content":"1"}}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","choices":[{"delta":{"content":", "}}]}

data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","choices":[{"delta":{"content":"2"}}]}

data: [DONE]
```

## Tools / Function Calling

### Request with Tools

```json
{
  "model": "gpt-4o",
  "messages": [{"role": "user", "content": "What's the weather in Paris?"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City name"
            }
          },
          "required": ["location"]
        }
      }
    }
  ]
}
```

### Response with Tool Call

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"Paris\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

### Submit Tool Result

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "user", "content": "What's the weather in Paris?"},
    {
      "role": "assistant",
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {"name": "get_weather", "arguments": "{\"location\": \"Paris\"}"}
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "content": "{\"temperature\": 18, \"condition\": \"cloudy\"}"
    }
  ]
}
```

## Error Responses

### Security Blocked

```json
{
  "error": {
    "code": "SECURITY_BLOCKED",
    "message": "Request blocked by security guard",
    "details": {
      "risk_level": "high",
      "risk_score": 0.85,
      "findings": [
        {
          "category": "prompt_injection",
          "severity": "high",
          "description": "Potential prompt injection detected"
        }
      ]
    }
  }
}
```

### Rate Limited

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded",
    "retry_after": 60
  }
}
```

### Budget Exceeded

```json
{
  "error": {
    "code": "BUDGET_EXCEEDED",
    "message": "Monthly budget limit reached",
    "details": {
      "budget_limit": 100.00,
      "current_spend": 100.50
    }
  }
}
```

### Provider Error

```json
{
  "error": {
    "code": "PROVIDER_ERROR",
    "message": "LLM provider returned an error",
    "details": {
      "provider": "openai",
      "status": 500,
      "message": "Internal server error"
    }
  }
}
```

## Examples

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-xxx",
    },
    json={
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        "temperature": 0.7,
        "max_tokens": 150,
    },
)

data = response.json()
print(data["choices"][0]["message"]["content"])
```

### JavaScript

```javascript
const response = await fetch("http://localhost:8000/v1/chat/completions", {
  method: "POST",
  headers: {
    "X-API-Key": "gw_xxx",
    "Authorization": "Bearer sk-xxx",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: "gpt-4o",
    messages: [{ role: "user", content: "Hello!" }],
  }),
});

const data = await response.json();
console.log(data.choices[0].message.content);
```

### OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-your-key",
    default_headers={"X-API-Key": "gw_xxx"},
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)

print(response.choices[0].message.content)
```
