# Azure OpenAI Provider

TensorWall supports Azure OpenAI Service for enterprise deployments.

## Supported Models

Azure OpenAI provides access to OpenAI models through Azure infrastructure:

| Model | Deployment Name Example | Description |
|-------|------------------------|-------------|
| GPT-4o | `gpt-4o` | Latest flagship |
| GPT-4o mini | `gpt-4o-mini` | Cost-effective |
| GPT-4 Turbo | `gpt-4-turbo` | Previous generation |
| GPT-4 | `gpt-4` | Base GPT-4 |
| GPT-3.5 Turbo | `gpt-35-turbo` | Fast and affordable |

## Configuration

### Environment Variables

```bash
# Required
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key

# Optional
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Request Format

Use the `azure/` prefix with your deployment name:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "azure/gpt-4o-deployment",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

Or pass credentials in headers:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "X-Azure-Endpoint: https://your-resource.openai.azure.com" \
  -H "X-Azure-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "azure/gpt-4o",
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
    headers={"X-API-Key": "gw_xxx"},
    json={
        "model": "azure/gpt-4o",
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

Full function calling support:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"X-API-Key": "gw_xxx"},
    json={
        "model": "azure/gpt-4o",
        "messages": [{"role": "user", "content": "What's the weather?"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather data",
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

## Enterprise Benefits

### Regional Deployment

Deploy models in specific Azure regions for:
- Data residency compliance
- Lower latency
- Regional failover

### Private Endpoints

Configure Azure Private Endpoints for secure, private connectivity:

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.privatelink.openai.azure.com
```

### Managed Identity

Use Azure Managed Identity instead of API keys:

```python
from azure.identity import DefaultAzureCredential

# TensorWall can use DefaultAzureCredential
credential = DefaultAzureCredential()
token = credential.get_token("https://cognitiveservices.azure.com/.default")
```

## Load Balancing with Azure

Use TensorWall's load balancing across multiple Azure deployments:

```python
from backend.application.engines.router import LLMRouter, RouteEndpoint
from backend.application.providers.azure_openai import AzureOpenAIProvider

# Create providers for different regions
azure_eastus = AzureOpenAIProvider(
    endpoint="https://myapp-eastus.openai.azure.com",
    api_key="key1",
)

azure_westeu = AzureOpenAIProvider(
    endpoint="https://myapp-westeurope.openai.azure.com",
    api_key="key2",
)

# Configure router
router = LLMRouter(strategy=LoadBalanceStrategy.LEAST_LATENCY)
router.add_route("gpt-4o", [
    RouteEndpoint(provider=azure_eastus, priority=0),
    RouteEndpoint(provider=azure_westeu, priority=1),
])
```

## Cost Tracking

Azure OpenAI uses the same pricing as OpenAI. TensorWall tracks costs per deployment:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-35-turbo | $0.50 | $1.50 |

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid API key | Check AZURE_OPENAI_API_KEY |
| 404 Not Found | Deployment not found | Verify deployment name |
| 429 Rate Limited | Quota exceeded | Increase Azure quota or add fallback |

### Deployment Name vs Model

Azure uses deployment names, not model names directly:

```bash
# Wrong - using OpenAI model name
"model": "azure/gpt-4o"

# Correct - using your deployment name
"model": "azure/my-gpt4o-deployment"
```
