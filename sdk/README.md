# LLM Gateway SDK

Python SDK for [LLM Gateway](https://github.com/your-org/llm-gateway) - A unified API gateway for multiple LLM providers.

## Installation

```bash
pip install llm-gateway-sdk
```

## Quick Start

```python
from llm_gateway_sdk import LLMGateway

# Initialize client
client = LLMGateway(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    app_id="my-app",
)

# Chat completion
response = client.chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    model="gpt-4",
    temperature=0.7,
)

print(response.choices[0].message.content)
```

## Features

- **Multiple Providers**: OpenAI, Anthropic, AWS Bedrock, Ollama, LM Studio
- **Sync & Async**: Both synchronous and asynchronous clients
- **Streaming**: Full support for streaming responses
- **Type Safe**: Full Pydantic models for requests and responses
- **Error Handling**: Detailed exceptions for different error types

## Usage

### Synchronous Client

```python
from llm_gateway_sdk import LLMGateway

with LLMGateway(base_url="http://localhost:8000") as client:
    # Chat completion
    response = client.chat(
        messages=[{"role": "user", "content": "What is Python?"}],
        model="gpt-4",
        max_tokens=100,
    )
    print(response.choices[0].message.content)

    # Embeddings
    embeddings = client.embeddings(
        input="Hello, world!",
        model="text-embedding-ada-002",
    )
    print(f"Embedding dimension: {len(embeddings.data[0].embedding)}")

    # List available models
    models = client.models()
    for model in models:
        print(f"- {model['id']}")
```

### Asynchronous Client

```python
import asyncio
from llm_gateway_sdk import AsyncLLMGateway

async def main():
    async with AsyncLLMGateway(base_url="http://localhost:8000") as client:
        response = await client.chat(
            messages=[{"role": "user", "content": "Hello!"}],
            model="gpt-4",
        )
        print(response.choices[0].message.content)

asyncio.run(main())
```

### Streaming

```python
from llm_gateway_sdk import LLMGateway

client = LLMGateway(base_url="http://localhost:8000")

# Stream chat completion
for chunk in client.chat(
    messages=[{"role": "user", "content": "Write a short story."}],
    model="gpt-4",
    stream=True,
):
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Async Streaming

```python
import asyncio
from llm_gateway_sdk import AsyncLLMGateway

async def main():
    async with AsyncLLMGateway(base_url="http://localhost:8000") as client:
        async for chunk in await client.chat(
            messages=[{"role": "user", "content": "Write a poem."}],
            model="gpt-4",
            stream=True,
        ):
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)

asyncio.run(main())
```

### Error Handling

```python
from llm_gateway_sdk import LLMGateway
from llm_gateway_sdk.exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    PolicyDeniedError,
    BudgetExceededError,
)

client = LLMGateway(base_url="http://localhost:8000")

try:
    response = client.chat(
        messages=[{"role": "user", "content": "Hello"}],
        model="gpt-4",
    )
except AuthenticationError as e:
    print(f"Auth failed: {e}")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
except PolicyDeniedError as e:
    print(f"Policy denied: {e.policy_name}")
except BudgetExceededError as e:
    print(f"Budget exceeded: {e.limit} vs {e.current}")
except ValidationError as e:
    print(f"Invalid request: {e}")
```

### Using with Specific App/Org

```python
from llm_gateway_sdk import LLMGateway

# Set app_id and org_id at client level
client = LLMGateway(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    app_id="my-application",
    org_id="my-organization",
)

# Or override per request
response = client.chat(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4",
    app_id="different-app",
)
```

### Custom Headers

```python
from llm_gateway_sdk import LLMGateway

client = LLMGateway(
    base_url="http://localhost:8000",
    headers={
        "X-Custom-Header": "custom-value",
        "X-Request-ID": "req-123",
    },
)
```

## API Reference

### LLMGateway / AsyncLLMGateway

**Constructor Parameters:**
- `base_url` (str): Base URL of LLM Gateway (default: http://localhost:8000)
- `api_key` (str): API key for authentication
- `app_id` (str): Application ID for request tracking
- `org_id` (str): Organization ID for multi-tenancy
- `timeout` (float): Request timeout in seconds (default: 60)
- `headers` (dict): Additional headers

**Methods:**
- `chat(messages, model, **kwargs)`: Create chat completion
- `embeddings(input, model, **kwargs)`: Create embeddings
- `models()`: List available models
- `health()`: Check gateway health
- `close()`: Close the client

### Models

- `ChatMessage`: Message in a conversation
- `ChatCompletionRequest`: Chat request parameters
- `ChatCompletionResponse`: Chat response with choices
- `EmbeddingRequest`: Embedding request parameters
- `EmbeddingResponse`: Embedding response with vectors

### Exceptions

- `LLMGatewayError`: Base exception
- `AuthenticationError`: Auth failures (401/403)
- `RateLimitError`: Rate limit exceeded (429)
- `ValidationError`: Invalid request (400/422)
- `ServerError`: Server errors (5xx)
- `PolicyDeniedError`: Request denied by policy
- `BudgetExceededError`: Budget limit exceeded

## License

MIT
