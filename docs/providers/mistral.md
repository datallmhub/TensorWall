# Mistral AI Provider

TensorWall supports Mistral AI's powerful open-weight and commercial models.

## Supported Models

| Model | Type | Description |
|-------|------|-------------|
| `mistral-large-latest` | Chat | Most capable Mistral model |
| `mistral-medium-latest` | Chat | Balanced performance |
| `mistral-small-latest` | Chat | Fast and efficient |
| `codestral-latest` | Code | Specialized for coding |
| `ministral-8b-latest` | Chat | Compact 8B model |
| `ministral-3b-latest` | Chat | Ultra-compact 3B model |
| `open-mixtral-8x22b` | Chat | Open-weight MoE |
| `open-mixtral-8x7b` | Chat | Open-weight MoE |

## Configuration

### Environment Variables

```bash
# Required
MISTRAL_API_KEY=your_api_key

# Optional
MISTRAL_API_URL=https://api.mistral.ai/v1
```

### Request Format

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Authorization: Bearer your_mistral_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-large-latest",
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
        "Authorization": "Bearer xxx",
    },
    json={
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True,
    },
    stream=True,
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

### Codestral for Code

Use Codestral for coding tasks:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer xxx",
    },
    json={
        "model": "codestral-latest",
        "messages": [
            {"role": "user", "content": "Write a Python function to merge two sorted lists"}
        ],
    },
)
```

### Function Calling

Mistral supports native function calling:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer xxx",
    },
    json={
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": "What's the weather in Tokyo?"}],
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
                        }
                    }
                }
            }
        ]
    },
)
```

### JSON Mode

Structured JSON output:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer xxx",
    },
    json={
        "model": "mistral-large-latest",
        "messages": [
            {"role": "user", "content": "Extract the name and email from: John Doe, john@example.com"}
        ],
        "response_format": {"type": "json_object"},
    },
)
```

## Cost Tracking

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| mistral-large-latest | $2.00 | $6.00 |
| mistral-medium-latest | $2.70 | $8.10 |
| mistral-small-latest | $0.20 | $0.60 |
| codestral-latest | $0.30 | $0.90 |
| ministral-8b-latest | $0.10 | $0.10 |
| ministral-3b-latest | $0.04 | $0.04 |

## API Compatibility

Mistral uses OpenAI-compatible API format. TensorWall handles:

### Request Parameters

| Parameter | Support |
|-----------|---------|
| `messages` | Full support |
| `temperature` | Full support |
| `max_tokens` | Full support |
| `top_p` | Full support |
| `stream` | Full support |
| `tools` | Full support |
| `response_format` | Full support |

### Stop Sequences

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"X-API-Key": "gw_xxx"},
    json={
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": "List 5 colors:"}],
        "stop": ["6."],  # Stop before 6th item
    },
)
```

## EU Data Residency

Mistral AI is a French company with EU-hosted infrastructure:

- Data processed in EU
- GDPR compliant
- No data transfer to US

This makes Mistral ideal for EU organizations with data residency requirements.

## Embeddings

Mistral provides embedding models:

```python
response = requests.post(
    "http://localhost:8000/v1/embeddings",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer xxx",
    },
    json={
        "model": "mistral-embed",
        "input": "Hello, world!",
    },
)
```

## Best Practices

1. **Use mistral-small for simple tasks** - Fast and cost-effective
2. **Use codestral for code** - Specialized performance
3. **Use mistral-large for complex reasoning** - Best quality
4. **Use ministral for high volume** - Lowest cost
