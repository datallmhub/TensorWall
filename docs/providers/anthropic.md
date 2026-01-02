# Anthropic Provider

TensorWall supports all Claude models from Anthropic.

## Supported Models

| Model | Type | Description |
|-------|------|-------------|
| `claude-opus-4-5-20251101` | Chat | Most capable Claude model |
| `claude-sonnet-4-20250514` | Chat | Balanced performance |
| `claude-3-5-sonnet-latest` | Chat | Latest Sonnet version |
| `claude-3-5-haiku-latest` | Chat | Fast and efficient |
| `claude-3-opus-20240229` | Chat | Previous flagship |
| `claude-3-sonnet-20240229` | Chat | Previous Sonnet |
| `claude-3-haiku-20240307` | Chat | Previous Haiku |

## Configuration

### Environment Variables

```bash
# Optional - API URL override
ANTHROPIC_API_URL=https://api.anthropic.com/v1
```

### Request Headers

Pass your Anthropic API key in the Authorization header:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Authorization: Bearer sk-ant-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Features

### Streaming

Full streaming support:

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-ant-xxx",
    },
    json={
        "model": "claude-sonnet-4-20250514",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True,
    },
    stream=True,
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

### System Prompts

System prompts are handled correctly for Claude:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-ant-xxx",
    },
    json={
        "model": "claude-sonnet-4-20250514",
        "messages": [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Write a Python function to sort a list"}
        ],
    },
)
```

### Tool Use

Claude's tool use is fully supported:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-ant-xxx",
    },
    json={
        "model": "claude-sonnet-4-20250514",
        "messages": [{"role": "user", "content": "What's 25 * 17?"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform arithmetic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"}
                        },
                        "required": ["expression"]
                    }
                }
            }
        ]
    },
)
```

### Vision

Claude's vision capabilities are supported:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-ant-xxx",
    },
    json={
        "model": "claude-sonnet-4-20250514",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,..."}
                    }
                ]
            }
        ]
    },
)
```

## Cost Tracking

TensorWall automatically tracks costs based on Anthropic's pricing:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| claude-opus-4-5 | $15.00 | $75.00 |
| claude-sonnet-4 | $3.00 | $15.00 |
| claude-3-5-sonnet | $3.00 | $15.00 |
| claude-3-5-haiku | $0.80 | $4.00 |

## API Translation

TensorWall automatically translates between OpenAI format and Anthropic's native format:

### Request Translation

| OpenAI Field | Anthropic Field |
|--------------|-----------------|
| `messages` | `messages` |
| `max_tokens` | `max_tokens` |
| `temperature` | `temperature` |
| `stream` | `stream` |
| `tools` | `tools` |

### Response Translation

Anthropic responses are converted to OpenAI format:

```json
{
  "id": "msg_xxx",
  "object": "chat.completion",
  "model": "claude-sonnet-4-20250514",
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
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```
