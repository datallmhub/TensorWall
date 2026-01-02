# Groq Provider

TensorWall supports Groq for ultra-fast LLM inference.

## Supported Models

| Model | Type | Description |
|-------|------|-------------|
| `llama-3.3-70b-versatile` | Chat | Latest Llama 3.3 70B |
| `llama-3.1-70b-versatile` | Chat | Llama 3.1 70B |
| `llama-3.1-8b-instant` | Chat | Fast Llama 3.1 8B |
| `llama3-70b-8192` | Chat | Llama 3 70B |
| `llama3-8b-8192` | Chat | Llama 3 8B |
| `mixtral-8x7b-32768` | Chat | Mixtral 8x7B |
| `gemma2-9b-it` | Chat | Google Gemma 2 |

## Configuration

### Environment Variables

```bash
# Required
GROQ_API_KEY=gsk_your_api_key

# Optional
GROQ_API_URL=https://api.groq.com/openai/v1
```

### Request Format

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Authorization: Bearer gsk_your_groq_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Features

### Ultra-Fast Inference

Groq uses custom LPU (Language Processing Unit) hardware for extremely fast inference:

- **500+ tokens/second** output speed
- **Sub-100ms** time to first token
- Ideal for real-time applications

### Streaming

Full streaming support with fast token delivery:

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer gsk_xxx",
    },
    json={
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Write a poem"}],
        "stream": True,
    },
    stream=True,
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

### JSON Mode

Groq supports JSON mode for structured outputs:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer gsk_xxx",
    },
    json={
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": "List 3 colors as JSON array"}
        ],
        "response_format": {"type": "json_object"},
    },
)
```

### Tool Use

Function calling is supported:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer gsk_xxx",
    },
    json={
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "What's 15 * 23?"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Perform calculation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"}
                        }
                    }
                }
            }
        ]
    },
)
```

## Cost Tracking

Groq offers competitive pricing:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| llama-3.3-70b-versatile | $0.59 | $0.79 |
| llama-3.1-70b-versatile | $0.59 | $0.79 |
| llama-3.1-8b-instant | $0.05 | $0.08 |
| mixtral-8x7b-32768 | $0.24 | $0.24 |
| gemma2-9b-it | $0.20 | $0.20 |

## Use Cases

### Real-Time Chat

Groq's speed makes it ideal for:
- Interactive chatbots
- Voice assistants
- Real-time coding assistants

### Batch Processing

High throughput for:
- Document summarization
- Content generation
- Data extraction

## Load Balancing with Groq

Use Groq as a fast fallback:

```python
from backend.application.engines.router import LLMRouter, RouteEndpoint
from backend.application.providers import openai_provider, groq_provider

router = LLMRouter(strategy=LoadBalanceStrategy.LEAST_LATENCY)
router.add_route("llama-70b", [
    RouteEndpoint(provider=groq_provider, priority=0),    # Fastest
    RouteEndpoint(provider=openai_provider, priority=1),  # Fallback
])
```

## Rate Limits

Groq has rate limits based on your plan:

| Plan | Requests/min | Tokens/min |
|------|-------------|------------|
| Free | 30 | 14,400 |
| Developer | 100 | 100,000 |
| Enterprise | Custom | Custom |

TensorWall handles rate limit errors with automatic retry and fallback.
