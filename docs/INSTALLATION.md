# Installation

## What is LLM Gateway?

A self-hosted LLM API gateway.
Drop-in compatible with OpenAI APIs. Route, control, and observe any LLM provider.

---

## Prerequisites

- Docker
- Docker Compose

---

## Quick Start

```bash
git clone https://github.com/your-org/llm-gateway.git
cd llm-gateway
docker compose up -d
```

That's it. The gateway is running.

No account, no signup, no cloud dependency.

---

## First-Time Setup

On first launch, the init container runs automatically:

1. Applies database migrations
2. Creates an admin account
3. Generates an API key
4. Displays credentials **once**

Check the logs to get your credentials:

```bash
docker compose logs init | grep -A5 "Setup Complete"
```

You'll see output like:

```
Admin Email   admin@example.com
API Key       gw_xxxxxxxxxxxxxxxxxxxx
```

**Save these credentials.** They are displayed once and cannot be recovered later.

### Custom Admin Email

To specify a custom admin email:

```bash
ADMIN_EMAIL=ops@mycompany.com docker compose up -d
```

---

## Verify Installation

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status": "healthy"}
```

---

## Your First API Call

The gateway forwards your provider API key. In production, keys can be stored and managed centrally.

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-generated-key>" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

Replace `<your-generated-key>` with the API key from setup.

---

## Access Points

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Dashboard | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |

---

## Next Steps

- [Production Deployment](./PRODUCTION.md) — HTTPS, secrets, scaling
- [CLI Reference](./CLI_REFERENCE.md) — All available commands
- [API Reference](./API_REFERENCE.md) — Endpoint documentation
