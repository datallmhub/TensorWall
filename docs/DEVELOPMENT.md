# TensorWall - Development Guide

Guide for contributors and developers.

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Git

---

## Quick Setup

```bash
# Clone
git clone https://github.com/datallmhub/TensorWall.git
cd tensorwall

# Start infrastructure
docker-compose up db redis -d

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run migrations & seed
python -m backend.cli setup wizard

# Start backend
uvicorn backend.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
tensorwall/
├── backend/
│   ├── adapters/          # External service adapters
│   │   ├── cache/         # Redis adapter
│   │   └── llm/           # LLM provider adapters
│   ├── api/               # FastAPI routes
│   │   ├── admin/         # Admin endpoints
│   │   └── v1/            # Public API (OpenAI compatible)
│   ├── application/       # Use cases & business logic
│   ├── cli/               # CLI commands (Typer)
│   ├── core/              # Config, auth, security
│   ├── db/                # Models, migrations, seeds
│   │   ├── alembic/       # Alembic migrations
│   │   ├── seeds/         # Seed data
│   │   └── models.py      # SQLAlchemy models
│   ├── domain/            # Domain entities
│   └── tests/             # Test suite
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   └── lib/           # Utilities
│   └── e2e/               # Playwright tests
├── docs/                  # Documentation
└── docker-compose.yml
```

---

## Backend Development

### Running Tests

```bash
cd backend

# All tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Specific test file
pytest tests/unit/test_policies.py

# Watch mode
pytest-watch
```

### Code Quality

```bash
# Format code
ruff format .

# Lint
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Type checking
mypy backend
```

### Database Migrations

```bash
# Create new migration
python -m backend.cli migrate revision -m "add_new_table"

# Apply migrations
python -m backend.cli migrate upgrade

# Rollback
python -m backend.cli migrate downgrade -1

# Show SQL without applying
python -m backend.cli migrate upgrade --sql
```

### Adding a New API Endpoint

1. Create route in `backend/api/admin/` or `backend/api/v1/`
2. Add use case in `backend/application/`
3. Add tests in `backend/tests/`
4. Register router in `backend/main.py`

Example:

```python
# backend/api/admin/widgets.py
from fastapi import APIRouter, Depends
from backend.core.auth import require_permission

router = APIRouter(prefix="/widgets", tags=["widgets"])

@router.get("/")
@require_permission("widgets:read")
async def list_widgets():
    return {"widgets": []}
```

```python
# backend/main.py
from backend.api.admin import widgets
app.include_router(widgets.router, prefix="/admin")
```

---

## Frontend Development

### Running Development Server

```bash
cd frontend
npm run dev
```

Open http://localhost:3000

### Building for Production

```bash
npm run build
npm start
```

### Running E2E Tests

```bash
# Start backend first
docker-compose up -d

# Run Playwright tests
npx playwright test

# With UI
npx playwright test --ui
```

### Code Quality

```bash
# Lint
npm run lint

# Type check
npm run type-check

# Format
npm run format
```

---

## CLI Development

The CLI uses [Typer](https://typer.tiangolo.com/).

### Adding a New Command

```python
# backend/cli/commands/mycommand.py
import typer

app = typer.Typer(help="My new command group")

@app.command()
def action(
    name: str = typer.Argument(..., help="Name to process"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Do something with a name."""
    if verbose:
        typer.echo(f"Processing: {name}")
    typer.echo(f"Done: {name}")
```

```python
# backend/cli/main.py
from backend.cli.commands import mycommand
app.add_typer(mycommand.app, name="mycommand")
```

### Testing CLI

```bash
# Run command
python -m backend.cli mycommand action "test" --verbose

# Help
python -m backend.cli mycommand --help
```

---

## Docker Development

### Rebuild Backend Image

```bash
docker-compose build backend
docker-compose up -d backend
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Shell Access

```bash
# Backend container
docker-compose exec backend bash

# Database
docker-compose exec db psql -U postgres -d tensorwall
```

### Reset Everything

```bash
docker-compose down -v
docker-compose up -d
```

---

## Environment Variables

### Backend (.env)

```env
# Required
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tensorwall
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=dev-secret-key-change-in-production

# Optional
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Testing Strategy

### Unit Tests

- Located in `backend/tests/unit/`
- Fast, isolated, mock external dependencies
- Run frequently during development

```python
# Example
async def test_policy_allows_request():
    policy = PolicyRule(action=PolicyAction.ALLOW)
    result = await policy.evaluate(request)
    assert result.allowed is True
```

### Integration Tests

- Located in `backend/tests/integration/`
- Test real database interactions
- Use test fixtures

```python
# Example
async def test_create_application(test_db):
    app = Application(name="test", app_id="test-app")
    test_db.add(app)
    await test_db.commit()

    result = await test_db.get(Application, app.id)
    assert result.name == "test"
```

### E2E Tests

- Located in `frontend/e2e/`
- Full browser testing with Playwright
- Test user flows

```typescript
// Example
test('admin can create application', async ({ page }) => {
  await page.goto('/applications');
  await page.click('text=New Application');
  await page.fill('[name=name]', 'Test App');
  await page.click('text=Create');
  await expect(page.locator('text=Test App')).toBeVisible();
});
```

---

## Git Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code improvements

### Commit Messages

```
type: short description

Longer description if needed.

Closes #123
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Process

1. Create feature branch
2. Make changes
3. Run tests & linting
4. Open PR with description
5. Address review feedback
6. Squash and merge

---

## Debugging

### Backend Debugging

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use debugpy for VS Code
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

### SQL Query Logging

```env
# In .env
DEBUG=true  # Enables SQLAlchemy echo
```

### Request Debugging

Add `X-Debug: true` header to see full decision trace:

```bash
curl -H "X-Debug: true" http://localhost:8000/v1/chat/completions ...
```

---

## Common Issues

### Import Errors

```bash
# Ensure you're in the right directory
cd tensorwall

# Ensure PYTHONPATH
export PYTHONPATH=$PWD
```

### Database Connection Issues

```bash
# Check if DB is running
docker-compose ps db

# Check connection
python -m backend.cli check db
```

### Port Already in Use

```bash
# Find process
lsof -i :8000

# Kill it
kill -9 <PID>
```

---

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Typer Docs](https://typer.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [Playwright Docs](https://playwright.dev/)
