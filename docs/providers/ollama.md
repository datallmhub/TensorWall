# Ollama Provider

TensorWall supports Ollama for running local LLMs without external API dependencies.

## Supported Models

Ollama supports hundreds of models. Common ones include:

| Model | Parameters | Description |
|-------|------------|-------------|
| `llama3.2` | 1B, 3B | Latest Llama 3.2 |
| `llama3.1` | 8B, 70B | Llama 3.1 |
| `codellama` | 7B, 13B, 34B | Code-focused Llama |
| `mistral` | 7B | Mistral 7B |
| `mixtral` | 8x7B | Mixtral MoE |
| `qwen2.5` | 0.5B-72B | Qwen 2.5 family |
| `deepseek-coder` | 1.3B-33B | DeepSeek Coder |
| `phi3` | 3.8B | Microsoft Phi-3 |
| `gemma2` | 2B, 9B, 27B | Google Gemma 2 |

## Configuration

### Environment Variables

```bash
# Required
OLLAMA_API_URL=http://localhost:11434

# Or remote Ollama server
OLLAMA_API_URL=http://gpu-server:11434
```

### Installing Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.2
```

### Request Format

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.2",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

Or without prefix if Ollama is detected:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
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
        "model": "ollama/llama3.2",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True,
    },
    stream=True,
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

### Local Inference

Benefits of Ollama:
- **No API costs** - Run unlimited requests
- **Data privacy** - Data never leaves your machine
- **Offline capable** - No internet required
- **Customizable** - Fine-tune and modify models

### Custom Models

Use custom Ollama models:

```bash
# Create a Modelfile
cat > Modelfile << 'EOF'
FROM llama3.2
SYSTEM You are a helpful coding assistant.
PARAMETER temperature 0.7
EOF

# Create the model
ollama create coding-assistant -f Modelfile

# Use in TensorWall
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_xxx" \
  -d '{"model": "ollama/coding-assistant", "messages": [...]}'
```

### Vision Models

Ollama supports vision models:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"X-API-Key": "gw_xxx"},
    json={
        "model": "ollama/llava",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
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

## API Translation

TensorWall translates OpenAI format to Ollama format:

### Request Translation

| OpenAI Field | Ollama Field |
|--------------|--------------|
| `messages` | `messages` |
| `max_tokens` | `num_predict` |
| `temperature` | `temperature` |
| `top_p` | `top_p` |
| `stream` | `stream` |

### Response Format

Ollama responses are converted to OpenAI format:

```json
{
  "id": "ollama-xxx",
  "object": "chat.completion",
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

## Cost Tracking

Ollama is free, but TensorWall still tracks:
- Token usage
- Request counts
- Latency metrics

This helps monitor usage even without cost.

## Performance Optimization

### GPU Acceleration

Ollama automatically uses GPU when available:

```bash
# Check GPU usage
nvidia-smi

# Ollama will show:
# "using CUDA"
```

### Model Loading

Models are loaded into memory on first request:
- First request: Slower (model loading)
- Subsequent requests: Fast (model cached)

Keep models loaded:

```bash
# Ollama keeps models loaded by default
# Set keep-alive time
OLLAMA_KEEP_ALIVE=24h ollama serve
```

### Multiple GPUs

For larger models:

```bash
# Use specific GPUs
CUDA_VISIBLE_DEVICES=0,1 ollama serve
```

## Load Balancing

Use multiple Ollama instances for scaling:

```python
from backend.application.engines.router import LLMRouter, RouteEndpoint
from backend.application.providers.ollama import OllamaProvider

ollama1 = OllamaProvider(base_url="http://gpu1:11434")
ollama2 = OllamaProvider(base_url="http://gpu2:11434")

router = LLMRouter(strategy=LoadBalanceStrategy.ROUND_ROBIN)
router.add_route("llama3.2", [
    RouteEndpoint(provider=ollama1, weight=50),
    RouteEndpoint(provider=ollama2, weight=50),
])
```

## Hybrid Architecture

Combine Ollama with cloud providers:

```python
from backend.application.engines.router import LLMRouter, RouteEndpoint
from backend.application.providers import openai_provider, ollama_provider

router = LLMRouter(strategy=LoadBalanceStrategy.WEIGHTED)

# Use local Ollama for most requests (free)
# Fallback to OpenAI for complex queries
router.add_route("gpt-4", [
    RouteEndpoint(provider=ollama_provider, weight=80, priority=0),
    RouteEndpoint(provider=openai_provider, weight=20, priority=1),
])
```

## Troubleshooting

### Connection Refused

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start if needed
ollama serve
```

### Model Not Found

```bash
# List available models
ollama list

# Pull the model
ollama pull llama3.2
```

### Slow Inference

- Ensure GPU is detected
- Use smaller models for faster responses
- Consider quantized versions (Q4, Q5)
