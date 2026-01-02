# Embeddings API

The Embeddings API generates vector representations of text for semantic search, clustering, and similarity tasks.

## Endpoint

```
POST /v1/embeddings
```

## Authentication

| Header | Description | Required |
|--------|-------------|----------|
| `X-API-Key` | TensorWall application API key | Yes |
| `Authorization` | LLM provider API key | Depends on provider |

## Request

### Headers

```http
POST /v1/embeddings HTTP/1.1
Host: localhost:8000
X-API-Key: gw_xxxx
Authorization: Bearer sk-your-key
Content-Type: application/json
```

### Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Embedding model identifier |
| `input` | string/array | Yes | Text(s) to embed |
| `encoding_format` | string | No | `float` or `base64` |
| `dimensions` | integer | No | Output dimensions (if supported) |

### Single Input

```json
{
  "model": "text-embedding-3-small",
  "input": "Hello, world!"
}
```

### Multiple Inputs

```json
{
  "model": "text-embedding-3-small",
  "input": [
    "First document",
    "Second document",
    "Third document"
  ]
}
```

## Response

### Success Response

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.0023, -0.0094, 0.0156, ...]
    }
  ],
  "model": "text-embedding-3-small",
  "usage": {
    "prompt_tokens": 5,
    "total_tokens": 5
  }
}
```

### Multiple Embeddings

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.0023, -0.0094, ...]
    },
    {
      "object": "embedding",
      "index": 1,
      "embedding": [0.0045, -0.0012, ...]
    },
    {
      "object": "embedding",
      "index": 2,
      "embedding": [0.0089, -0.0034, ...]
    }
  ],
  "model": "text-embedding-3-small",
  "usage": {
    "prompt_tokens": 15,
    "total_tokens": 15
  }
}
```

## Supported Models

### OpenAI

| Model | Dimensions | Description |
|-------|------------|-------------|
| `text-embedding-3-small` | 1536 | Fast, cost-effective |
| `text-embedding-3-large` | 3072 | Higher quality |
| `text-embedding-ada-002` | 1536 | Legacy model |

### Mistral

| Model | Dimensions | Description |
|-------|------------|-------------|
| `mistral-embed` | 1024 | Mistral embeddings |

### Ollama

| Model | Dimensions | Description |
|-------|------------|-------------|
| `nomic-embed-text` | 768 | Nomic embeddings |
| `mxbai-embed-large` | 1024 | MixedBread embeddings |
| `all-minilm` | 384 | Fast local embeddings |

## Dimension Reduction

Some models support reducing output dimensions:

```json
{
  "model": "text-embedding-3-large",
  "input": "Hello, world!",
  "dimensions": 1024
}
```

## Cost Tracking

TensorWall tracks embedding costs:

| Model | Cost per 1M tokens |
|-------|-------------------|
| text-embedding-3-small | $0.02 |
| text-embedding-3-large | $0.13 |
| mistral-embed | $0.10 |

## Examples

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/embeddings",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-xxx",
    },
    json={
        "model": "text-embedding-3-small",
        "input": "Hello, world!",
    },
)

data = response.json()
embedding = data["data"][0]["embedding"]
print(f"Embedding dimensions: {len(embedding)}")
```

### Batch Embeddings

```python
import requests

documents = [
    "TensorWall provides LLM governance.",
    "Security features protect against prompt injection.",
    "Cost tracking monitors API spending.",
]

response = requests.post(
    "http://localhost:8000/v1/embeddings",
    headers={
        "X-API-Key": "gw_xxx",
        "Authorization": "Bearer sk-xxx",
    },
    json={
        "model": "text-embedding-3-small",
        "input": documents,
    },
)

data = response.json()
embeddings = [item["embedding"] for item in data["data"]]
```

### Semantic Search

```python
import numpy as np
from numpy.linalg import norm

def cosine_similarity(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))

# Get query embedding
query_response = requests.post(
    "http://localhost:8000/v1/embeddings",
    headers={"X-API-Key": "gw_xxx", "Authorization": "Bearer sk-xxx"},
    json={
        "model": "text-embedding-3-small",
        "input": "How does security work?",
    },
)
query_embedding = query_response.json()["data"][0]["embedding"]

# Compare with document embeddings
for i, doc_embedding in enumerate(embeddings):
    similarity = cosine_similarity(query_embedding, doc_embedding)
    print(f"Document {i}: {similarity:.4f}")
```

### OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-xxx",
    default_headers={"X-API-Key": "gw_xxx"},
)

response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Hello, world!",
)

embedding = response.data[0].embedding
```

## Error Responses

### Invalid Model

```json
{
  "error": {
    "code": "INVALID_MODEL",
    "message": "Model 'unknown-embed' is not supported for embeddings"
  }
}
```

### Input Too Long

```json
{
  "error": {
    "code": "CONTEXT_LENGTH_EXCEEDED",
    "message": "Input exceeds maximum token limit",
    "details": {
      "max_tokens": 8191,
      "input_tokens": 10000
    }
  }
}
```

## Best Practices

1. **Batch inputs** - Send multiple texts in one request for efficiency
2. **Cache embeddings** - Store embeddings to avoid recomputing
3. **Choose appropriate model** - Use smaller models for speed, larger for quality
4. **Normalize vectors** - Some use cases benefit from L2 normalization

## Security Considerations

TensorWall applies security checks to embedding inputs:

- PII detection still applies
- Secrets detection still applies
- Cost limits are enforced

However, prompt injection detection is less relevant for embeddings since the text is not used as instructions.
