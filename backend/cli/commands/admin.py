"""Admin user management commands."""

import asyncio
import secrets
import string
import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(help="User administration.")


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@app.command()
def create(
    email: str = typer.Option(..., "--email", "-e", help="Admin email address"),
    name: str = typer.Option(None, "--name", "-n", help="Admin display name"),
    password: str = typer.Option(
        None, "--password", "-p", help="Password (prompted if not provided)"
    ),
    generate: bool = typer.Option(
        False, "--generate", "-g", help="Generate random password"
    ),
):
    """Create a new admin user."""
    if not name:
        name = email.split("@")[0].title()

    if generate:
        password = generate_password()
        console.print(f"[yellow]Generated password:[/yellow] {password}")
    elif not password:
        password = typer.prompt("Password", hide_input=True, confirmation_prompt=True)

    result = run_async(_create_admin(email, name, password))

    if result["success"]:
        console.print(f"[green]Admin user created:[/green] {email}")
    else:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)


@app.command("list")
def list_users():
    """List all admin users."""
    users = run_async(_list_users())

    table = Table(title="Admin Users")
    table.add_column("ID", style="dim")
    table.add_column("Email", style="cyan")
    table.add_column("Name")
    table.add_column("Role", style="green")
    table.add_column("Active")

    for user in users:
        table.add_row(
            str(user["id"]),
            user["email"],
            user["name"],
            user["role"],
            "[green]Yes[/green]" if user["is_active"] else "[red]No[/red]",
        )

    console.print(table)


@app.command()
def reset_password(
    email: str = typer.Option(..., "--email", "-e", help="User email"),
    generate: bool = typer.Option(
        False, "--generate", "-g", help="Generate random password"
    ),
):
    """Reset user password."""
    if generate:
        password = generate_password()
        console.print(f"[yellow]Generated password:[/yellow] {password}")
    else:
        password = typer.prompt("New password", hide_input=True, confirmation_prompt=True)

    result = run_async(_reset_password(email, password))

    if result["success"]:
        console.print(f"[green]Password reset for:[/green] {email}")
    else:
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)


async def _create_admin(email: str, name: str, password: str) -> dict:
    """Create admin user in database."""
    try:
        from passlib.context import CryptContext
        from sqlalchemy import select
        from backend.db.session import AsyncSessionLocal
        from backend.db.models import User, UserRole

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        async with AsyncSessionLocal() as session:
            # Check if user exists
            result = await session.execute(select(User).where(User.email == email))
            if result.scalar_one_or_none():
                return {"success": False, "error": "User already exists"}

            user = User(
                email=email,
                name=name,
                password_hash=pwd_context.hash(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(user)
            await session.commit()

            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_users() -> list[dict]:
    """List all users."""
    try:
        from sqlalchemy import select
        from backend.db.session import AsyncSessionLocal
        from backend.db.models import User

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).order_by(User.id))
            users = result.scalars().all()

            return [
                {
                    "id": u.id,
                    "email": u.email,
                    "name": u.name,
                    "role": u.role.value if hasattr(u.role, "value") else str(u.role),
                    "is_active": u.is_active,
                }
                for u in users
            ]
    except Exception:
        return []


async def _reset_password(email: str, password: str) -> dict:
    """Reset user password."""
    try:
        from passlib.context import CryptContext
        from sqlalchemy import select
        from backend.db.session import AsyncSessionLocal
        from backend.db.models import User

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

            user.password_hash = pwd_context.hash(password)
            await session.commit()

            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
