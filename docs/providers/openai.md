# OpenAI Provider

TensorWall supports all OpenAI models through its native API integration.

## Supported Models

| Model | Type | Description |
|-------|------|-------------|
| `gpt-4o` | Chat | Latest flagship model |
| `gpt-4o-mini` | Chat | Fast, cost-effective |
| `gpt-4-turbo` | Chat | Previous generation turbo |
| `gpt-4` | Chat | Base GPT-4 |
| `gpt-3.5-turbo` | Chat | Fast and affordable |
| `o1` | Reasoning | Advanced reasoning |
| `o1-mini` | Reasoning | Efficient reasoning |
| `text-embedding-3-small` | Embedding | Small embedding model |
| `text-embedding-3-large` | Embedding | Large embedding model |

## Configuration

### Environment Variables

```bash
# Optional - API URL override
OPENAI_API_URL=https://api.openai.com/v1
```

### Request Headers

Pass your OpenAI API key in the Authorization header:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Authorization: Bearer sk-your-openai-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Features

### Streaming

Full streaming support with Server-Sent Events:

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
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True,
    },
    stream=True,
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

### Function Calling

Function calling is fully proxied:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-xxx",
    },
    json={
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "What's the weather in Paris?"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        },
                        "required": ["location"]
                    }
                }
            }
        ]
    },
)
```

### Vision

GPT-4o vision is supported:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-xxx",
    },
    json={
        "model": "gpt-4o",
        "messages": [
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
        ]
    },
)
```

## Cost Tracking

TensorWall automatically tracks costs based on OpenAI's pricing:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |

## Error Handling

OpenAI errors are mapped to TensorWall error codes:

| OpenAI Error | TensorWall Code | Description |
|--------------|-----------------|-------------|
| 401 | `AUTH_ERROR` | Invalid API key |
| 429 | `RATE_LIMITED` | Rate limit exceeded |
| 500 | `PROVIDER_ERROR` | OpenAI service error |
| 503 | `PROVIDER_UNAVAILABLE` | Service temporarily unavailable |
