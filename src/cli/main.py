"""SecureOps Local — Main CLI Entry Point."""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

# Configure UTF-8 for standard output streams if running on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from src.cli.analyze import analyze_log_file
from src.cli.knowledge import knowledge_app

__version__ = "0.1.0"

app = typer.Typer(
    name="secureops",
    help="SecureOps Local — Cautious, local incident-review decision support for Linux SSH logs.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()

# Register subcommands and commands
app.add_typer(knowledge_app, name="knowledge")
app.command("analyze")(analyze_log_file)


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
