"""Health check commands."""

import asyncio
import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(help="System health checks.")


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command()
def health():
    """Full health check of all services."""
    table = Table(title="Health Check")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
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

    console.print(table)

    if not (db_ok and redis_ok):
        raise typer.Exit(1)


@app.command()
def db():
    """Check database connection."""
    ok, msg = run_async(_check_db())
    if ok:
        console.print(f"[green]Database OK:[/green] {msg}")
    else:
        console.print(f"[red]Database FAILED:[/red] {msg}")
        raise typer.Exit(1)


@app.command()
def redis():
    """Check Redis connection."""
    ok, msg = run_async(_check_redis())
    if ok:
        console.print(f"[green]Redis OK:[/green] {msg}")
    else:
        console.print(f"[red]Redis FAILED:[/red] {msg}")
        raise typer.Exit(1)


async def _check_db() -> tuple[bool, str]:
    """Check database connectivity."""
    try:
        from backend.db.session import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            return True, f"PostgreSQL {version.split()[1] if version else 'connected'}"
    except Exception as e:
        return False, str(e)


async def _check_redis() -> tuple[bool, str]:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as redis
        from backend.core.config import settings

        client = redis.from_url(settings.redis_url)
        await client.ping()
        info = await client.info("server")
        await client.close()
        return True, f"Redis {info.get('redis_version', 'connected')}"
    except Exception as e:
        return False, str(e)
