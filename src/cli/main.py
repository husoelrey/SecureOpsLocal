"""SecureOps Local — Main CLI Entry Point."""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

__version__ = "0.1.0"

app = typer.Typer(
    name="secureops",
    help="SecureOps Local — Cautious, local incident-review decision support for Linux SSH logs.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(
            Panel(
                f"[bold cyan]SecureOps Local[/bold cyan] [green]v{__version__}[/green]\n"
                "[dim]Local incident-review decision-support CLI for Linux SSH authentication logs.[/dim]",
                title="[bold blue]Version Info[/bold blue]",
                expand=False,
            )
        )
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show SecureOps Local version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """SecureOps Local CLI root callback."""
    pass


@app.command("version")
def show_version() -> None:
    """Display the current version of SecureOps Local."""
    console.print(
        Panel(
            f"[bold cyan]SecureOps Local[/bold cyan] [green]v{__version__}[/green]\n"
            "[dim]Air-gapped ready, privacy-preserving incident analysis.[/dim]",
            title="[bold blue]Version Info[/bold blue]",
            expand=False,
        )
    )


if __name__ == "__main__":
    app()
