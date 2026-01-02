# Google Vertex AI Provider

TensorWall supports Google's Vertex AI for Gemini models.

## Supported Models

| Model | Type | Description |
|-------|------|-------------|
| `gemini-2.0-flash` | Chat | Latest Gemini Flash |
| `gemini-1.5-pro` | Chat | Advanced reasoning |
| `gemini-1.5-flash` | Chat | Fast responses |
| `gemini-1.0-pro` | Chat | Stable production |

## Configuration

### Environment Variables

```bash
# Required
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1

# Authentication (one of these)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# Or use gcloud auth application-default login
```

### Request Format

Use the `vertex/` or `gemini-` prefix:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "X-API-Key: gw_your_gateway_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-1.5-pro",
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
        "model": "gemini-1.5-pro",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True,
    },
    stream=True,
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

### Multimodal

Gemini supports images, audio, and video:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"X-API-Key": "gw_xxx"},
    json={
        "model": "gemini-1.5-pro",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "gs://bucket/image.jpg"}
                    }
                ]
            }
        ]
    },
)
```

### Function Calling

Gemini function calling is supported:

```python
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"X-API-Key": "gw_xxx"},
    json={
        "model": "gemini-1.5-pro",
        "messages": [{"role": "user", "content": "Book a flight to Paris"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "book_flight",
                    "description": "Book a flight",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string"},
                            "date": {"type": "string"}
                        }
                    }
                }
            }
        ]
    },
)
```

## API Translation

TensorWall translates OpenAI format to Vertex AI format:

### Request Translation

| OpenAI Field | Vertex AI Field |
|--------------|-----------------|
| `messages` | `contents` |
| `max_tokens` | `maxOutputTokens` |
| `temperature` | `temperature` |
| `top_p` | `topP` |

### Role Mapping

| OpenAI Role | Vertex AI Role |
|-------------|----------------|
| `system` | Prepended to first user message |
| `user` | `user` |
| `assistant` | `model` |

## Cost Tracking

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gemini-2.0-flash | $0.075 | $0.30 |
| gemini-1.5-pro | $1.25 | $5.00 |
| gemini-1.5-flash | $0.075 | $0.30 |

## Authentication

### Service Account

Create a service account with Vertex AI User role:

```bash
# Create service account
gcloud iam service-accounts create tensorwall \
  --display-name="TensorWall Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:tensorwall@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Create key
gcloud iam service-accounts keys create key.json \
  --iam-account=tensorwall@$PROJECT_ID.iam.gserviceaccount.com
```

### Workload Identity (GKE)

For GKE deployments, use Workload Identity:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tensorwall
  annotations:
    iam.gke.io/gcp-service-account: tensorwall@PROJECT_ID.iam.gserviceaccount.com
```

## Regional Deployment

Deploy Vertex AI in specific regions:

```python
from backend.application.providers.vertex import VertexAIProvider

provider = VertexAIProvider(
    project_id="my-project",
    region="europe-west1",  # For EU data residency
)
```

Available regions:
- `us-central1` (Iowa)
- `us-east4` (Virginia)
- `europe-west1` (Belgium)
- `europe-west4` (Netherlands)
- `asia-northeast1` (Tokyo)
- `asia-southeast1` (Singapore)
