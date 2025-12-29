# CLI Reference

Command-line interface for TensorWall administration.

---

## Usage

```bash
python -m backend.cli <command> [options]
```

Or via Docker:

```bash
docker compose exec backend python -m backend.cli <command>
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| `setup` | First-time setup wizard |
| `migrate` | Database migrations |
| `admin` | User management |
| `seed` | Seed data |
| `check` | Health checks |

---

## setup

First-time installation and configuration.

### wizard

Interactive setup wizard.

```bash
python -m backend.cli setup wizard
```

Options:
| Flag | Description |
|------|-------------|
| `--no-interactive` | Non-interactive mode (CI/CD) |
| `--admin-email` | Admin email (required if non-interactive) |
| `--admin-password` | Admin password (required if non-interactive) |
| `--skip-seed` | Skip seed data |

Example:
```bash
python -m backend.cli setup wizard \
  --no-interactive \
  --admin-email admin@company.com \
  --admin-password "$ADMIN_PASSWORD"
```

### status

Check setup status.

```bash
python -m backend.cli setup status
```

---

## migrate

Database migration management (Alembic wrapper).

### upgrade

Apply migrations.

```bash
python -m backend.cli migrate upgrade
```

Options:
| Flag | Description |
|------|-------------|
| `--revision` | Target revision (default: `head`) |
| `--sql` | Show SQL without applying |

### downgrade

Rollback migrations.

```bash
python -m backend.cli migrate downgrade -1
```

### current

Show current revision.

```bash
python -m backend.cli migrate current
```

### history

Show migration history.

```bash
python -m backend.cli migrate history
```

---

## admin

User administration.

### create

Create admin user.

```bash
python -m backend.cli admin create \
  --email admin@example.com \
  --name "Admin User"
```

Password is prompted securely.

### list

List all users.

```bash
python -m backend.cli admin list
```

### reset-password

Reset user password.

```bash
python -m backend.cli admin reset-password --email admin@example.com
```

---

## seed

Seed data management.

### dev

Seed development data.

```bash
python -m backend.cli seed dev
```

Creates:
- Test application
- Sample API key
- Sample policies
- Usage records (for analytics testing)

### production

Seed production data.

```bash
python -m backend.cli seed production
```

Creates:
- LLM model registry only

### clean

Remove all seed data.

```bash
python -m backend.cli seed clean --confirm
```

**Warning:** Destructive operation.

---

## check

System health checks.

### health

Full health check.

```bash
python -m backend.cli check health
```

### db

Database connection check.

```bash
python -m backend.cli check db
```

### redis

Redis connection check.

```bash
python -m backend.cli check redis
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
| 2 | Invalid arguments |

---

## Environment Variables

The CLI respects the same environment variables as the application:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection |
| `REDIS_URL` | Redis connection |

Load from `.env` file:

```bash
export $(cat .env | xargs)
python -m backend.cli check health
```
