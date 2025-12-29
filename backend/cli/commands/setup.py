"""Setup wizard commands."""

import asyncio
import secrets
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer(help="First-time setup wizard.")


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@app.command()
def wizard(
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="Non-interactive mode for automation"
    ),
    admin_email: str = typer.Option(None, "--admin-email", help="Admin email"),
    admin_password: str = typer.Option(None, "--admin-password", help="Admin password"),
    skip_seed: bool = typer.Option(False, "--skip-seed", help="Skip seed data"),
    seed: str = typer.Option("development", "--seed", help="Seed type: development, production"),
):
    """Interactive first-time setup wizard."""
    console.print(
        Panel.fit(
            "[bold cyan]LLM Gateway Setup Wizard[/bold cyan]\n"
            "This will configure your gateway for first use.",
            border_style="cyan",
        )
    )

    # Step 1: Check database
    console.print("\n[bold]Step 1:[/bold] Checking database connection...")
    db_ok, db_msg = run_async(_check_db())
    if not db_ok:
        console.print(f"[red]Database error:[/red] {db_msg}")
        console.print("\nPlease ensure PostgreSQL is running and DATABASE_URL is correct.")
        raise typer.Exit(1)
    console.print(f"  [green]✓[/green] {db_msg}")

    # Step 2: Check Redis
    console.print("\n[bold]Step 2:[/bold] Checking Redis connection...")
    redis_ok, redis_msg = run_async(_check_redis())
    if not redis_ok:
        console.print(f"[red]Redis error:[/red] {redis_msg}")
        console.print("\nPlease ensure Redis is running and REDIS_URL is correct.")
        raise typer.Exit(1)
    console.print(f"  [green]✓[/green] {redis_msg}")

    # Step 3: Run migrations
    console.print("\n[bold]Step 3:[/bold] Running database migrations...")
    migrate_result = run_async(_run_migrations())
    if not migrate_result["success"]:
        console.print(f"[red]Migration error:[/red] {migrate_result['error']}")
        raise typer.Exit(1)
    console.print("  [green]✓[/green] Migrations applied")

    # Step 4: Check if already setup
    is_setup = run_async(_check_setup_complete())
    if is_setup:
        console.print("\n[yellow]Setup already completed.[/yellow]")
        console.print("Use 'seed clean --confirm' to reset if needed.")
        raise typer.Exit(0)

    # Step 5: Create admin user
    console.print("\n[bold]Step 4:[/bold] Creating admin user...")

    if not non_interactive and not admin_email:
        admin_email = typer.prompt("  Admin email")
    elif not admin_email:
        console.print("[red]--admin-email required in non-interactive mode[/red]")
        raise typer.Exit(1)

    if not non_interactive and not admin_password:
        admin_password = typer.prompt("  Password", hide_input=True, confirmation_prompt=True)
    elif not admin_password:
        admin_password = generate_password()
        console.print(f"  [yellow]Generated password:[/yellow] {admin_password}")

    admin_result = run_async(_create_admin(admin_email, admin_password))
    if not admin_result["success"]:
        console.print(f"[red]Error:[/red] {admin_result['error']}")
        raise typer.Exit(1)
    console.print(f"  [green]✓[/green] Admin created: {admin_email}")

    # Step 6: Seed data
    api_key = None
    if not skip_seed:
        console.print("\n[bold]Step 5:[/bold] Seeding initial data...")
        seed_result = run_async(_seed_data())
        if seed_result["success"]:
            api_key = seed_result.get("api_key")
            console.print("  [green]✓[/green] Data seeded")
        else:
            console.print(f"  [yellow]Warning:[/yellow] {seed_result.get('error', 'Seed skipped')}")

    # Step 7: Mark setup complete
    run_async(_mark_setup_complete())

    # Summary
    console.print("\n")
    console.print(
        Panel.fit(
            "[bold green]Setup Complete![/bold green]",
            border_style="green",
        )
    )

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row("Admin Email", admin_email)
    table.add_row("Dashboard", "http://localhost:3000")
    table.add_row("API", "http://localhost:8000")
    table.add_row("API Docs", "http://localhost:8000/docs")
    if api_key:
        table.add_row("API Key", api_key)

    console.print(table)

    if api_key:
        console.print("\n[yellow]⚠ Save the API key now. It cannot be recovered.[/yellow]")


@app.command()
def status():
    """Check setup status."""
    console.print("[cyan]Checking setup status...[/cyan]\n")

    table = Table(title="Setup Status")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    # Database
    db_ok, db_msg = run_async(_check_db())
    table.add_row(
        "Database",
        "[green]OK[/green]" if db_ok else "[red]FAILED[/red]",
        db_msg,
    )

    # Redis
    redis_ok, redis_msg = run_async(_check_redis())
    table.add_row(
        "Redis",
        "[green]OK[/green]" if redis_ok else "[red]FAILED[/red]",
        redis_msg,
    )

    # Migrations
    if db_ok:
        migration_current = run_async(_get_migration_status())
        table.add_row(
            "Migrations",
            "[green]OK[/green]" if migration_current else "[yellow]Pending[/yellow]",
            migration_current or "Run 'migrate upgrade'",
        )

    # Setup complete
    if db_ok:
        is_setup = run_async(_check_setup_complete())
        table.add_row(
            "Setup Complete",
            "[green]Yes[/green]" if is_setup else "[yellow]No[/yellow]",
            "" if is_setup else "Run 'setup wizard'",
        )

    console.print(table)


async def _check_db() -> tuple[bool, str]:
    """Check database connectivity."""
    try:
        from backend.db.session import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            return True, f"PostgreSQL connected"
    except Exception as e:
        return False, str(e)


async def _check_redis() -> tuple[bool, str]:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis
        from backend.core.config import settings

        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.close()
        return True, "Redis connected"
    except Exception as e:
        return False, str(e)


async def _run_migrations() -> dict:
    """Run database migrations using Alembic."""
    import os
    import subprocess

    try:
        # Find alembic.ini - could be in backend/ or project root
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Try backend/alembic.ini first, then project root
        ini_path = os.path.join(backend_dir, "alembic.ini")
        if not os.path.exists(ini_path):
            project_root = os.path.dirname(backend_dir)
            ini_path = os.path.join(project_root, "alembic.ini")

        if os.path.exists(ini_path):
            # Use Alembic via subprocess to handle async properly
            result = subprocess.run(
                ["python", "-m", "alembic", "-c", ini_path, "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(ini_path),
            )

            if result.returncode == 0:
                return {"success": True, "method": "alembic"}
            else:
                # If Alembic fails, fall back to create_all
                console.print(f"  [yellow]Alembic warning:[/yellow] {result.stderr[:200] if result.stderr else 'Unknown error'}")
                console.print("  [yellow]Falling back to create_all...[/yellow]")

        # Fallback: use create_all if Alembic not configured or failed
        from backend.db.session import engine
        from backend.db.models import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return {"success": True, "method": "create_all"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _check_setup_complete() -> bool:
    """Check if setup has been completed."""
    try:
        from sqlalchemy import select
        from backend.db.session import AsyncSessionLocal
        from backend.db.models import SetupState

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SetupState).where(SetupState.key == "setup_completed")
            )
            row = result.scalar_one_or_none()
            return row is not None and row.value == "true"
    except Exception:
        return False


async def _get_migration_status() -> str:
    """Get current migration status."""
    try:
        from sqlalchemy import text
        from backend.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            row = result.first()
            return row[0] if row else None
    except Exception:
        return None


async def _create_admin(email: str, password: str) -> dict:
    """Create admin user."""
    try:
        from datetime import datetime
        from passlib.context import CryptContext
        from backend.db.session import AsyncSessionLocal
        from backend.db.models import User, UserRole

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        async with AsyncSessionLocal() as session:
            user = User(
                email=email,
                name=email.split("@")[0].title(),
                password_hash=pwd_context.hash(password),
                role=UserRole.ADMIN,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(user)
            await session.commit()

            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _seed_data() -> dict:
    """Seed initial data."""
    import random
    from datetime import datetime

    try:
        from sqlalchemy import select
        from backend.db.session import AsyncSessionLocal
        from backend.db.models import (
            Application,
            ApiKey,
            Budget,
            Organization,
            Environment,
            BudgetPeriod,
            TenantStatus,
            TenantTier,
        )
        from backend.core.auth import hash_api_key

        async with AsyncSessionLocal() as session:
            # Check if already seeded
            result = await session.execute(select(Application).limit(1))
            if result.scalar_one_or_none():
                return {"success": True, "api_key": None}

            # Generate API key
            api_key_raw = f"gw_{secrets.token_urlsafe(24)}"

            # Organization
            org = Organization(
                org_id="org_default",
                name="Default Organization",
                slug="default-org",
                status=TenantStatus.ACTIVE,
                tier=TenantTier.PROFESSIONAL,
                owner_email="admin@localhost",
                created_at=datetime.utcnow(),
            )
            session.add(org)
            await session.flush()

            # Application
            app = Application(
                app_id="default-app",
                name="Default Application",
                owner="admin",
                description="Default application",
                is_active=True,
                allowed_providers=["openai", "anthropic", "ollama"],
                allowed_models=["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022"],
                created_at=datetime.utcnow(),
            )
            session.add(app)
            await session.flush()

            # API Key
            api_key = ApiKey(
                key_hash=hash_api_key(api_key_raw),
                key_prefix=api_key_raw[:12],
                name="Default API Key",
                application_id=app.id,
                environment=Environment.DEVELOPMENT,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(api_key)

            # Budget
            budget = Budget(
                application_id=app.id,
                soft_limit_usd=800.0,
                hard_limit_usd=1000.0,
                period=BudgetPeriod.MONTHLY,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(budget)

            await session.commit()

            return {"success": True, "api_key": api_key_raw}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _mark_setup_complete() -> None:
    """Mark setup as complete in setup_state table."""
    try:
        from datetime import datetime
        from backend.db.session import AsyncSessionLocal
        from backend.db.models import SetupState

        async with AsyncSessionLocal() as session:
            setup_state = SetupState(
                key="setup_completed",
                value="true",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(setup_state)
            await session.commit()
    except Exception:
        pass  # Best effort
