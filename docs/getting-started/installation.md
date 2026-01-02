# Installation

## Requirements

- Python 3.10+
- Node.js 18+ (for frontend)
- PostgreSQL 14+ (or SQLite for development)
- Redis (optional, for caching)
- Docker & Docker Compose (recommended)

## Docker Installation (Recommended)

The easiest way to run TensorWall is with Docker Compose:

```bash
# Clone the repository
git clone https://github.com/datallmhub/tensorwall.git
cd tensorwall

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

This starts:
- **Backend** (FastAPI) on port 8000
- **Frontend** (Next.js) on port 3000
- **PostgreSQL** on port 5432
- **Redis** on port 6379

## Manual Installation

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/tensorwall"
export REDIS_URL="redis://localhost:6379"
export JWT_SECRET_KEY="your-secret-key-here"

# Run database migrations
python -m backend.cli migrate up

# Create admin user
python -m backend.cli admin create --email admin@example.com --password admin123

# Start backend
uvicorn backend.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
export NEXT_PUBLIC_API_URL="http://localhost:8000"

# Start development server
npm run dev
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | Secret for JWT tokens | Random 32+ character string |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `ENVIRONMENT` | Environment name | `development` |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` |
| `OPENAI_API_URL` | OpenAI API base URL | `https://api.openai.com/v1` |
| `ANTHROPIC_API_URL` | Anthropic API base URL | `https://api.anthropic.com/v1` |
| `OLLAMA_API_URL` | Ollama API URL | `http://localhost:11434` |

## Verify Installation

```bash
# Check backend health
curl http://localhost:8000/health/live

# Check API docs
open http://localhost:8000/docs

# Access dashboard
open http://localhost:3000
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Make your first API call
- [Configuration](configuration.md) - Customize TensorWall
- [Security Features](../features/security.md) - Enable security checks
