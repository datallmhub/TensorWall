"""Seed data commands."""

import asyncio
import typer
from rich.console import Console

console = Console()
app = typer.Typer(help="Seed data management.")


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command()
def dev():
    """Seed development data (test apps, users, sample data)."""
    console.print("[cyan]Seeding development data...[/cyan]")

    result = run_async(_seed_development())

    if result["success"]:
        console.print("[green]Development data seeded.[/green]")
        if result.get("api_key"):
            console.print(f"\n[yellow]API Key:[/yellow] {result['api_key']}")
            console.print("[dim]Save this key - it cannot be recovered.[/dim]")
    else:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)


@app.command()
def production():
    """Seed production data (LLM models only)."""
    console.print("[cyan]Seeding production data...[/cyan]")

    result = run_async(_seed_production())

    if result["success"]:
        console.print("[green]Production data seeded.[/green]")
    else:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)


@app.command()
def clean(
    confirm: bool = typer.Option(
        False, "--confirm", help="Confirm destructive operation"
    ),
):
    """Remove all seed data. DESTRUCTIVE!"""
    if not confirm:
        console.print("[red]This will delete all data![/red]")
        console.print("Use --confirm to proceed.")
        raise typer.Exit(1)

    console.print("[yellow]Cleaning all data...[/yellow]")

    result = run_async(_clean_data())

    if result["success"]:
        console.print("[green]Data cleaned.[/green]")
    else:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)


async def _seed_development() -> dict:
    """Seed development data."""
    import secrets
    import random
    from datetime import datetime

    try:
        from sqlalchemy import select
        from passlib.context import CryptContext
        from backend.db.session import AsyncSessionLocal
        from backend.db.models import (
            Application,
            ApiKey,
            Budget,
            PolicyRule,
            Feature,
            UsageRecord,
            Organization,
            User,
            UserRole,
            Environment,
            BudgetPeriod,
            PolicyAction,
            TenantStatus,
            TenantTier,
        )
        from backend.core.auth import hash_api_key

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        async with AsyncSessionLocal() as session:
            # Check if already seeded
            result = await session.execute(select(Application).limit(1))
            if result.scalar_one_or_none():
                return {"success": False, "error": "Data already exists. Use 'seed clean' first."}

            # Generate unique API key
            api_key_raw = f"gw_{secrets.token_urlsafe(24)}"

            # Organization
            org = Organization(
                org_id="org_default",
                name="Default Organization",
                slug="default-org",
                status=TenantStatus.ACTIVE,
                tier=TenantTier.PROFESSIONAL,
                owner_email="admin@example.com",
                created_at=datetime.utcnow(),
            )
            session.add(org)
            await session.flush()

            # Application
            app = Application(
                app_id="test-app",
                name="Test Application",
                owner="admin",
                description="Default test application",
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
                name="Development API Key",
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

            # Policy
            policy = PolicyRule(
                name="Default Policy",
                description="Allow all models for development",
                application_id=app.id,
                conditions={
                    "allowed_models": ["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022"]
                },
                action=PolicyAction.ALLOW,
                priority=100,
                is_enabled=True,
                created_at=datetime.utcnow(),
            )
            session.add(policy)

            # Feature
            feature = Feature(
                feature_id="default",
                app_id="test-app",
                name="Default Feature",
                description="Default feature for testing",
                allowed_actions=["generate", "analyze"],
                allowed_models=["gpt-4o-mini", "gpt-4o"],
                allowed_environments=["development", "staging", "production"],
                is_enabled=True,
            )
            session.add(feature)

            # Sample usage records for analytics
            for i in range(50):
                usage = UsageRecord(
                    request_id=f"req_{secrets.token_hex(8)}",
                    app_id="test-app",
                    feature="default",
                    environment=Environment.DEVELOPMENT,
                    provider="openai",
                    model="gpt-4o-mini",
                    input_tokens=random.randint(100, 1000),
                    output_tokens=random.randint(50, 500),
                    cost_usd=random.uniform(0.001, 0.05),
                    latency_ms=random.randint(5, 80),
                    created_at=datetime.utcnow(),
                )
                session.add(usage)

            await session.commit()

            return {"success": True, "api_key": api_key_raw}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _seed_production() -> dict:
    """Seed production data (minimal)."""
    try:
        # For production, we only seed LLM model definitions if needed
        # This is a placeholder for future model registry seeding
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _clean_data() -> dict:
    """Clean all data from database."""
    try:
        from sqlalchemy import text
        from backend.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Delete in order to respect foreign keys
            tables = [
                "usage_records",
                "audit_logs",
                "api_keys",
                "policy_rules",
                "budgets",
                "features",
                "applications",
                "users",
                "organizations",
            ]

            for table in tables:
                await session.execute(text(f"DELETE FROM {table}"))

            await session.commit()

            return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}
