"""Database migration commands (Alembic wrapper)."""

import os
import typer
from rich.console import Console

console = Console()
app = typer.Typer(help="Database migration management.")


def get_alembic_config():
    """Get Alembic configuration."""
    from alembic.config import Config

    # Find alembic.ini
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")

    if not os.path.exists(ini_path):
        console.print(f"[red]Error:[/red] alembic.ini not found at {ini_path}")
        raise typer.Exit(1)

    config = Config(ini_path)
    return config


@app.command()
def upgrade(
    revision: str = typer.Argument("head", help="Target revision"),
    sql: bool = typer.Option(False, "--sql", help="Show SQL without applying"),
):
    """Apply database migrations."""
    from alembic import command

    config = get_alembic_config()

    if sql:
        console.print(f"[cyan]Generating SQL for upgrade to {revision}...[/cyan]")
        command.upgrade(config, revision, sql=True)
    else:
        console.print(f"[cyan]Upgrading database to {revision}...[/cyan]")
        command.upgrade(config, revision)
        console.print("[green]Migration complete.[/green]")


@app.command()
def downgrade(
    revision: str = typer.Argument(..., help="Target revision (use -1 for previous)"),
    sql: bool = typer.Option(False, "--sql", help="Show SQL without applying"),
):
    """Rollback database migrations."""
    from alembic import command

    config = get_alembic_config()

    if sql:
        console.print(f"[cyan]Generating SQL for downgrade to {revision}...[/cyan]")
        command.downgrade(config, revision, sql=True)
    else:
        console.print(f"[yellow]Downgrading database to {revision}...[/yellow]")
        command.downgrade(config, revision)
        console.print("[green]Downgrade complete.[/green]")


@app.command()
def current():
    """Show current migration revision."""
    from alembic import command

    config = get_alembic_config()
    console.print("[cyan]Current revision:[/cyan]")
    command.current(config, verbose=True)


@app.command()
def history():
    """Show migration history."""
    from alembic import command

    config = get_alembic_config()
    console.print("[cyan]Migration history:[/cyan]")
    command.history(config, verbose=True)


@app.command()
def revision(
    message: str = typer.Option(..., "-m", "--message", help="Revision message"),
    autogenerate: bool = typer.Option(
        True, "--autogenerate/--no-autogenerate", help="Auto-detect model changes"
    ),
):
    """Create a new migration revision."""
    from alembic import command

    config = get_alembic_config()
    console.print(f"[cyan]Creating revision: {message}[/cyan]")
    command.revision(config, message=message, autogenerate=autogenerate)
    console.print("[green]Revision created.[/green]")
