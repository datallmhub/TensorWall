# TensorWall

**Simplify LLM integration. Control cost, access and security.**

TensorWall is an open-source LLM governance gateway that sits between your applications and LLM providers. It provides a unified API with built-in security, policy enforcement, and cost control.

## Key Features

| Feature | Description |
|---------|-------------|
| **OpenAI-Compatible API** | Drop-in replacement for OpenAI API |
| **Multi-Provider** | OpenAI, Anthropic, Azure, Vertex AI, Groq, Mistral, Ollama |
| **Security Guard** | Prompt injection, PII, and secrets detection |
| **Policy Engine** | ALLOW/DENY/WARN rules before LLM calls |
| **Budget Control** | Soft/hard limits per application |
| **Observability** | Request tracing, decision explainability |
| **Load Balancing** | Weighted routing with automatic fallback |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/datallmhub/tensorwall.git
cd tensorwall

# Start with Docker
docker-compose up -d

# Access the dashboard
open http://localhost:3000
```

## Architecture

```
┌─────────────┐     ┌─────────────────────────────────────┐     ┌─────────────┐
│             │     │            TensorWall               │     │             │
│    Your     │────►│  ┌─────────┐  ┌──────────┐         │────►│    LLM      │
│    App      │     │  │Security │  │ Policy   │         │     │  Provider   │
│             │◄────│  │ Guard   │  │ Engine   │         │◄────│             │
└─────────────┘     │  └─────────┘  └──────────┘         │     └─────────────┘
                    │  ┌─────────┐  ┌──────────┐         │
                    │  │ Budget  │  │  Router  │         │
                    │  │ Engine  │  │ (LB/FF)  │         │
                    │  └─────────┘  └──────────┘         │
                    └─────────────────────────────────────┘
```

## Why TensorWall?

### Before TensorWall

```python
# Direct LLM calls - no control
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": user_input}]
)
# No security checks
# No policy enforcement
# No cost control
# No audit trail
```

### With TensorWall

```python
# Same API, full governance
response = requests.post(
    "http://tensorwall:8000/v1/chat/completions",
    headers={"X-API-Key": "gw_xxx"},
    json={
        "model": "gpt-4",
        "messages": [{"role": "user", "content": user_input}]
    }
)
# ✅ Prompt injection blocked
# ✅ Policy enforced (dev can't use GPT-4)
# ✅ Budget tracked
# ✅ Full audit trail
```

## Supported Providers

| Provider | Models | Status |
|----------|--------|--------|
| OpenAI | GPT-4, GPT-4o, o1, o3 | ✅ Stable |
| Anthropic | Claude 3.5, Claude 3 | ✅ Stable |
| Azure OpenAI | GPT-4, GPT-4o (Azure) | ✅ Stable |
| Google Vertex AI | Gemini Pro, Gemini Flash | ✅ Stable |
| Groq | Llama 3, Mixtral | ✅ Stable |
| Mistral | Mistral Large, Codestral | ✅ Stable |
| Ollama | Any local model | ✅ Stable |
| AWS Bedrock | Claude, Titan | ✅ Stable |
| LM Studio | Any local model | ✅ Stable |

## Security Features

TensorWall includes a built-in Security Guard that detects:

- **Prompt Injection** (OWASP LLM01) - 17+ patterns
- **PII Detection** (OWASP LLM06) - Email, phone, SSN, credit cards
- **Secrets Detection** (OWASP LLM06) - API keys, tokens, passwords
- **ML-Based Moderation** - LlamaGuard, OpenAI Moderation API

## License

TensorWall is open-source software licensed under the [MIT License](https://github.com/datallmhub/tensorwall/blob/main/LICENSE).

## Community

- [GitHub Issues](https://github.com/datallmhub/tensorwall/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/datallmhub/tensorwall/discussions) - Questions and community support
- [Contributing Guide](contributing.md) - How to contribute
