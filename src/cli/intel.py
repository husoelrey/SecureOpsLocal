"""Threat Intelligence Management CLI Commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from src.database import SessionLocal
from src.integrations.intel_feed import (
    ingest_threat_intel_file,
    init_threat_intel_db,
    lookup_ip_intel,
)
from src.models.threat_intel import ThreatIntel

console = Console()
intel_app = typer.Typer(
    name="intel",
    help="Manage local offline threat intelligence feeds (STIX, MISP, CSV, JSON).",
)


@intel_app.command("add")
def add_threat_intel_feed(
    feed_path: Path = typer.Argument(
        ...,
        help="Path to a local threat intelligence feed file (.csv, .json, .stix, .misp).",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
) -> None:
    """Ingest a local threat feed file (CSV, JSON, STIX 2.1, or MISP) into the local database."""
    try:
        count = ingest_threat_intel_file(feed_path)
        console.print(
            f"[bold green]✓ Successfully ingested {count} threat indicator(s) from:[/bold green] [cyan]{feed_path.name}[/cyan]"
        )
    except Exception as e:
        console.print(f"[bold red][X] Failed to ingest threat feed: {e}[/bold red]")
        raise typer.Exit(code=1)


@intel_app.command("list")
def list_threat_intel(
    limit: int = typer.Option(
        50, "--limit", "-l", help="Maximum number of threat indicators to display."
    ),
) -> None:
    """List threat intelligence indicators stored in the local SQLite database."""
    init_threat_intel_db()
    db = SessionLocal()
    try:
        indicators = (
            db.query(ThreatIntel)
            .order_by(ThreatIntel.created_at.desc())
            .limit(limit)
            .all()
        )

        if not indicators:
            console.print(
                "[yellow]No threat intelligence indicators found in local database.[/yellow]\n"
                "[dim]Use 'secureops intel add <feed_path>' to ingest local STIX/MISP/CSV feeds.[/dim]"
            )
            return

        table = Table(
            title=f"Offline Threat Intelligence Indicators (Showing top {len(indicators)})",
            show_header=True,
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("IP Address", style="bold yellow")
        table.add_column("Threat Type", style="bold magenta")
        table.add_column("Severity", style="bold white")
        table.add_column("Source", style="dim")
        table.add_column("Description", style="white")

        for ind in indicators:
            sev_style = (
                "bold red"
                if ind.severity in ("critical", "high")
                else "yellow"
                if ind.severity == "medium"
                else "green"
            )
            table.add_row(
                ind.ip_address,
                ind.threat_type,
                f"[{sev_style}]{ind.severity.upper()}[/{sev_style}]",
                ind.source or "[local]",
                ind.description or "-",
            )

        console.print(table)
    finally:
        db.close()


@intel_app.command("lookup")
def lookup_threat_indicator(
    ip: str = typer.Argument(..., help="IP address to query in local threat database.")
) -> None:
    """Query an IP address against the local offline threat intelligence database."""
    match = lookup_ip_intel(ip.strip())
    if match:
        console.print(
            f"[bold green]✓ Threat Match Found:[/bold green] [bold yellow]{match.ip_address}[/bold yellow]\n"
            f"  [bold]Threat Type:[/bold] [bold magenta]{match.threat_type}[/bold magenta]\n"
            f"  [bold]Severity:[/bold] [bold red]{match.severity.upper()}[/bold red]\n"
            f"  [bold]Source:[/bold] {match.source or '[local]'}\n"
            f"  [bold]Description:[/bold] {match.description or '-'}"
        )
    else:
        console.print(
            f"[dim]No threat intelligence matches found for IP '{ip}' in local database.[/dim]"
        )
