"""TensorWall CLI - Main entry point."""

import typer
from rich.console import Console

from backend.cli.commands import setup, migrate, admin, seed, check

console = Console()

app = typer.Typer(
    name="tensorwall",
    help="TensorWall CLI - Administration and setup tools.",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(setup.app, name="setup")
app.add_typer(migrate.app, name="migrate")
app.add_typer(admin.app, name="admin")
app.add_typer(seed.app, name="seed")
app.add_typer(check.app, name="check")


@app.command()
def version():
    """Show version information."""
    console.print("[bold]TensorWall[/bold] v0.1.0")


if __name__ == "__main__":
    app()
