# TensorWall

**Developer-first API gateway for LLM services with built-in governance and security.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Features

| Feature | Description |
|---------|-------------|
| **OpenAI Compatible** | Drop-in replacement for `/v1/chat/completions` and `/v1/embeddings` |
| **Multi-Provider** | OpenAI, Anthropic, Ollama, LM Studio, AWS Bedrock |
| **Policy Engine** | Fine-grained access control before LLM calls |
| **Budget Control** | Per-app spending limits with alerts |
| **Audit Logging** | Full request/response traceability |
| **Cost Tracking** | Real-time usage analytics per app/feature |
| **Security Guards** | Prompt injection & secrets detection |

---

## Quick Start

```bash
# Clone & start
git clone https://github.com/datallmhub/TensorWall.git
cd tensorwall
docker-compose up -d
```

On first launch, credentials are generated and displayed in the logs:

```bash
docker-compose logs init | grep -A5 "Setup Complete"
```

Save these credentials immediately. They are displayed once and cannot be recovered.

```bash
# Verify
curl http://localhost:8000/health

# Make your first call (use your generated API key)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-generated-key>" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

**Access Points:**
- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Installation](docs/INSTALLATION.md) | Setup & deployment options |
| [Quickstart](docs/guides/QUICKSTART.md) | First API call in 60 seconds |
| [API Reference](docs/API_REFERENCE.md) | Full endpoint documentation |
| [Architecture](docs/ARCHITECTURE.md) | System design & components |
| [Security](docs/SECURITY.md) | Security model & hardening |
| [Development](docs/DEVELOPMENT.md) | Contributing guide |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client App                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       TensorWall                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │   Auth   │→ │  Policy  │→ │  Budget  │→ │  Audit   │    │
│  │  Check   │  │  Engine  │  │  Check   │  │   Log    │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
       ┌─────────┐       ┌─────────┐       ┌─────────┐
       │ OpenAI  │       │Anthropic│       │ Ollama  │
       └─────────┘       └─────────┘       └─────────┘
```

---

## CLI Commands

```bash
# Setup wizard
python -m backend.cli setup wizard

# Database migrations
python -m backend.cli migrate upgrade

# Create admin user
python -m backend.cli admin create --email admin@company.com

# Seed development data
python -m backend.cli seed dev

# Health check
python -m backend.cli check health
```

---

## API Endpoints

### LLM Proxy (OpenAI Compatible)

```
POST /v1/chat/completions    # Chat completion
POST /v1/embeddings          # Text embeddings
```

### Admin API

```
GET/POST   /admin/applications    # Manage apps
GET/POST   /admin/policies        # Manage policies
GET/POST   /admin/budgets         # Manage budgets
GET        /admin/analytics       # Usage analytics
GET        /admin/audit           # Audit logs
```

### Authentication

```
POST /auth/login              # Login (returns JWT)
POST /auth/logout             # Logout
GET  /auth/me                 # Current user
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | Yes | - | Redis connection string |
| `JWT_SECRET_KEY` | Yes | - | JWT signing key (64+ chars) |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | Allowed origins |
| `ENVIRONMENT` | No | `development` | `development`/`production` |

See [Installation Guide](docs/INSTALLATION.md) for complete reference.

---

## Tech Stack

**Backend:**
- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Redis
- Alembic (migrations)
- Typer (CLI)

**Frontend:**
- Next.js 14
- React
- TypeScript
- Tailwind CSS

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

See [Development Guide](docs/DEVELOPMENT.md) for setup instructions.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Support

- [Documentation](docs/)
- [Issues](https://github.com/datallmhub/TensorWall/issues)
- [Discussions](https://github.com/datallmhub/TensorWall/discussions)
