# Production Deployment

This guide covers deploying LLM Gateway in production environments.

---

## Prerequisites

- Docker & Docker Compose (or Kubernetes)
- PostgreSQL 14+
- Redis 7+
- HTTPS-enabled reverse proxy (nginx, Caddy, Traefik)
- Domain name

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET_KEY` | Signing key (64+ chars, generate with `openssl rand -base64 64`) |
| `CORS_ORIGINS` | JSON array of allowed origins |

### Security

| Variable | Default | Production Value |
|----------|---------|------------------|
| `ENVIRONMENT` | `development` | `production` |
| `DEBUG` | `true` | `false` |
| `COOKIE_SECURE` | `false` | `true` |
| `COOKIE_SAMESITE` | `lax` | `strict` |

### Example `.env`

```env
ENVIRONMENT=production
DEBUG=false

DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/llm_gateway
REDIS_URL=redis://:password@redis-host:6379/0

JWT_SECRET_KEY=<generate-with-openssl-rand-base64-64>
CORS_ORIGINS=["https://admin.example.com"]

COOKIE_SECURE=true
COOKIE_SAMESITE=strict
```

---

## Docker Compose Production

Create `docker-compose.prod.yml`:

```yaml
services:
  backend:
    image: llm-gateway-backend:latest
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
      - COOKIE_SECURE=true
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run:

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## Database Setup

### Migrations

```bash
# Apply all migrations
python -m backend.cli migrate upgrade

# Verify
python -m backend.cli migrate current
```

### Backups

```bash
# Backup
pg_dump -h localhost -U postgres llm_gateway > backup.sql

# Restore
psql -h localhost -U postgres llm_gateway < backup.sql
```

---

## HTTPS / Reverse Proxy

### Caddy (Recommended)

```
admin.example.com {
    reverse_proxy backend:8000
}

api.example.com {
    reverse_proxy backend:8000
}
```

### nginx

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/api.example.com.pem;
    ssl_certificate_key /etc/ssl/private/api.example.com-key.pem;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Monitoring

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Full health check |
| `/health/live` | Liveness probe (K8s) |
| `/health/ready` | Readiness probe (K8s) |

### Metrics

Export logs to your observability stack:

```bash
docker compose logs -f backend | your-log-shipper
```

---

## Security Checklist

- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] Strong `JWT_SECRET_KEY` (64+ chars)
- [ ] `COOKIE_SECURE=true`
- [ ] HTTPS only
- [ ] `CORS_ORIGINS` restricted to your domains
- [ ] Database credentials rotated
- [ ] Redis password set
- [ ] Firewall rules configured
- [ ] Rate limiting enabled

---

## Scaling

### Horizontal

Increase replicas:

```yaml
deploy:
  replicas: 4
```

### Vertical

Adjust resources:

```yaml
resources:
  limits:
    cpus: '2'
    memory: 1G
```

### Database Connection Pool

```env
# In DATABASE_URL or as separate vars
POOL_SIZE=10
MAX_OVERFLOW=20
```

---

## Troubleshooting

### Check Logs

```bash
docker compose logs backend --tail=100
```

### Database Connection

```bash
python -m backend.cli check db
```

### Redis Connection

```bash
python -m backend.cli check redis
```

### Reset Admin Password

```bash
python -m backend.cli admin reset-password --email admin@example.com
```
