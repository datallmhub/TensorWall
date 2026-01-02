# Configuration

TensorWall is configured through environment variables and optional configuration files.

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | Secret for JWT tokens (32+ chars) | Random secure string |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | - | Redis connection for caching |
| `ENVIRONMENT` | `development` | `development`, `production`, `test` |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins (JSON array) |
| `DEBUG` | `true` | Enable debug mode |

### LLM Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_URL` | `https://api.openai.com/v1` | OpenAI API base URL |
| `ANTHROPIC_API_URL` | `https://api.anthropic.com/v1` | Anthropic API base URL |
| `OLLAMA_API_URL` | `http://localhost:11434` | Ollama API URL |
| `AZURE_OPENAI_ENDPOINT` | - | Azure OpenAI endpoint |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` | Azure API version |
| `GOOGLE_CLOUD_PROJECT` | - | GCP project for Vertex AI |
| `VERTEX_AI_LOCATION` | `us-central1` | Vertex AI region |

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | - | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | - | Langfuse secret key |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse API host |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `COOKIE_SECURE` | `false` | Use secure cookies (set `true` for HTTPS) |
| `COOKIE_SAMESITE` | `lax` | Cookie SameSite policy |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token TTL |

### Audit

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIT_RETENTION_DAYS` | `90` | Days to retain audit logs |
| `STORE_PROMPTS` | `false` | Store prompts in audit (GDPR consideration) |

## Docker Compose

Example `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/tensorwall
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - CORS_ORIGINS=["https://your-domain.com"]
      - COOKIE_SECURE=true
      # Langfuse (optional)
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
```

## Production Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production`
- [ ] Use a strong, random `JWT_SECRET_KEY` (32+ chars)
- [ ] Set `COOKIE_SECURE=true` (requires HTTPS)
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set `DEBUG=false`
- [ ] Use secure database credentials
- [ ] Configure SSL/TLS for database and Redis
- [ ] Set appropriate `AUDIT_RETENTION_DAYS`
- [ ] Consider `STORE_PROMPTS=false` for GDPR compliance
