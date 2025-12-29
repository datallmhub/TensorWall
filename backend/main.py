from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from backend.api.v1 import chat, embeddings
from backend.api import health, auth
from backend.api.admin import (
    applications,
    policies,
    features,
    settings as admin_settings,
    models,
    requests,
    users,
    budgets,
    security,
)
from backend.core.config import settings
from backend.db.session import close_db, AsyncSessionLocal
from backend.adapters.cache.redis_client import init_redis, close_redis
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def check_setup_state() -> bool:
    """Check if the gateway has been properly set up."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT value FROM setup_state WHERE key = 'setup_completed'")
            )
            row = result.fetchone()
            return row is not None and row[0] == "true"
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"TensorWall starting on {settings.environment} environment")

    # Check database connection (no auto-init)
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connected")

        # Check if setup has been completed
        setup_done = await check_setup_state()
        if not setup_done:
            logger.warning(
                "Gateway not initialized. Run 'python -m backend.cli setup wizard' to complete setup."
            )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Ensure PostgreSQL is running and DATABASE_URL is correct.")

    # Initialize Redis
    try:
        await init_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    yield

    # Shutdown
    logger.info("TensorWall shutting down")
    await close_db()
    await close_redis()


DESCRIPTION = """
## TensorWall

**Developer-first API gateway for LLM services with built-in governance and security.**

### Key Features

| Feature | Description |
|---------|-------------|
| **OpenAI Compatible** | Drop-in replacement for OpenAI API (`/v1/chat/completions`, `/v1/embeddings`) |
| **Multi-Provider** | OpenAI, Anthropic, Ollama, LM Studio, AWS Bedrock |
| **Policy Engine** | Fine-grained access control BEFORE LLM calls |
| **Security Guards** | Prompt injection & secrets detection |
| **Audit Logging** | Full request/response traceability |
| **Cost Estimation** | Per-request cost tracking |
| **Dry-Run Mode** | Policy simulation without LLM calls |

### Authentication

All requests require a valid API key via the `X-API-Key` header.

```bash
curl -X POST https://api.example.com/v1/chat/completions \\
  -H "X-API-Key: gw_your_key_here" \\
  -H "Authorization: Bearer sk-your-openai-key" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]}'
```

### Special Headers

| Header | Description |
|--------|-------------|
| `X-API-Key` | Gateway API key (required) |
| `Authorization` | `Bearer <LLM_KEY>` for real LLM calls |
| `X-Debug` | `true` to include full decision trace |
| `X-Dry-Run` | `true` to simulate without LLM call |
| `X-Feature-Id` | Feature/use-case identifier |

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `AUTH_MISSING_KEY` | 401 | No API key provided |
| `POLICY_MODEL_BLOCKED` | 403 | Model blocked by policy |
| `FEATURE_NOT_ALLOWED` | 403 | Use-case not permitted |
| `RATE_LIMITED` | 429 | Rate limit exceeded |

### Links

* [API Documentation](/docs)
* [ReDoc](/redoc)
* [OpenAPI Spec](/openapi.json)
"""

TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Health checks and readiness probes for monitoring and orchestration.",
    },
    {
        "name": "Chat",
        "description": """OpenAI-compatible Chat Completions API with governance.

**Features:** Streaming, dry-run mode, decision explainability, feature allowlisting.

**Required Headers:** `X-API-Key`, `Authorization: Bearer <LLM_KEY>`

**Optional Headers:** `X-Debug`, `X-Dry-Run`, `X-Feature-Id`""",
    },
    {
        "name": "Embeddings",
        "description": "OpenAI-compatible embeddings API with governance controls.",
    },
    {
        "name": "Admin - Applications",
        "description": """Manage applications and API keys.

Applications provide isolation for API keys, rate limits, and usage tracking.""",
    },
    {
        "name": "Admin - Policies",
        "description": """Configure governance policies.

**Policy types:** `model_restriction`, `token_limit`, `rate_limit`, `time_restriction`, `environment_restriction`""",
    },
    {
        "name": "Admin - Features",
        "description": """Manage feature/use-case allowlisting.

Define allowed actions, models, environments, and token limits per feature.""",
    },
    {
        "name": "Admin - Models",
        "description": """Manage LLM model registry.

Configure available models, providers, and pricing information.""",
    },
    {
        "name": "Admin - Requests",
        "description": """View recent request logs.

Debug gateway behavior, see policy decisions, and track request flow.""",
    },
    {
        "name": "Admin - Users",
        "description": """Manage admin users.

Create, update, and delete users with admin access to the gateway.""",
    },
    {
        "name": "Admin - Settings",
        "description": """System configuration settings.

Configure system-wide settings like token limits, latency thresholds, and audit retention.""",
    },
]

app = FastAPI(
    title="TensorWall",
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "TensorWall Team",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes - LLM API (OpenAI compatible) - Hexagonal Architecture
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(embeddings.router, prefix="/v1", tags=["Embeddings"])

# Routes - Authentication
app.include_router(auth.router, tags=["Authentication"])

# Routes - Admin API
ADMIN_PREFIX = "/admin"
app.include_router(applications.router, prefix=ADMIN_PREFIX, tags=["Admin - Applications"])
app.include_router(policies.router, prefix=ADMIN_PREFIX, tags=["Admin - Policies"])
app.include_router(features.router, prefix=ADMIN_PREFIX, tags=["Admin - Features"])
app.include_router(models.router, prefix=ADMIN_PREFIX, tags=["Admin - Models"])
app.include_router(requests.router, prefix=ADMIN_PREFIX, tags=["Admin - Requests"])
app.include_router(budgets.router, prefix=ADMIN_PREFIX, tags=["Admin - Budgets"])
app.include_router(users.router, prefix=ADMIN_PREFIX, tags=["Admin - Users"])
app.include_router(admin_settings.router, prefix=ADMIN_PREFIX, tags=["Admin - Settings"])
app.include_router(security.router, prefix=ADMIN_PREFIX, tags=["Admin - Security"])
