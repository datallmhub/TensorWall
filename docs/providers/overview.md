# LLM Providers

TensorWall supports 9 LLM providers through a unified OpenAI-compatible API.

## Supported Providers

| Provider | Prefix | Models | Auth |
|----------|--------|--------|------|
| [OpenAI](openai.md) | `gpt-*`, `o1-*`, `o3-*` | GPT-4o, GPT-4, o1, o3 | API Key |
| [Anthropic](anthropic.md) | `claude-*` | Claude 3.5, Claude 3 | API Key |
| [Azure OpenAI](azure.md) | `azure-*`, `azure/*` | GPT-4, GPT-4o | API Key + Endpoint |
| [Vertex AI](vertex.md) | `gemini-*`, `vertex/*` | Gemini Pro, Flash, Ultra | GCP Token |
| [Groq](groq.md) | `llama*`, `mixtral*`, `groq/*` | Llama 3, Mixtral, Gemma | API Key |
| [Mistral](mistral.md) | `mistral-*`, `mistral/*` | Mistral Large, Codestral | API Key |
| AWS Bedrock | `bedrock/*` | Claude, Titan | AWS Credentials |
| Ollama | `ollama/*` | Any local model | None |
| LM Studio | `lmstudio/*` | Any local model | None |

## How Routing Works

TensorWall routes requests based on the model name:

```python
# Explicit prefix routing
"azure/gpt-4"       → Azure OpenAI
"vertex/gemini-pro" → Vertex AI
"groq/llama3-70b"   → Groq
"ollama/mistral"    → Ollama

# Pattern-based routing
"gpt-4o"            → OpenAI (starts with gpt-)
"claude-3-sonnet"   → Anthropic (starts with claude-)
"gemini-1.5-pro"    → Vertex AI (starts with gemini-)
"llama3-8b-8192"    → Groq (starts with llama)
```

## Authentication

Each provider requires its own API key passed via the `Authorization` header:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_tensorwall_key" \
  -H "Authorization: Bearer YOUR_PROVIDER_API_KEY" \
  -d '{"model": "gpt-4o", "messages": [...]}'
```

## Provider Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_URL=https://api.openai.com/v1

# Anthropic
ANTHROPIC_API_URL=https://api.anthropic.com/v1

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-02-01

# Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1

# Ollama
OLLAMA_API_URL=http://localhost:11434

# LM Studio
LMSTUDIO_API_URL=http://localhost:1234/v1
```

## Load Balancing Across Providers

Route the same model to multiple providers with fallback:

```python
from backend.application.engines.router import LLMRouter, RouteEndpoint
from backend.application.providers import openai_provider, azure_openai_provider

router = LLMRouter()
router.add_route("gpt-4", [
    RouteEndpoint(provider=openai_provider, weight=70, priority=0),
    RouteEndpoint(provider=azure_openai_provider, weight=30, priority=1),
])
```

This routes 70% of traffic to OpenAI, 30% to Azure, with automatic fallback if one fails.
