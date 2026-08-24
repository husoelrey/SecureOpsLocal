"""Administrator Feedback CLI Command Module."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.feedback.service import get_all_feedback, init_feedback_db, record_feedback
from src.schemas.feedback import FeedbackCreate

console = Console()


def feedback_command(
    incident_id: Optional[str] = typer.Argument(
        None, help="The ID of the incident report (e.g. inc_fac3616a) or 'list'."
    ),
    false_positive: bool = typer.Option(
        True,
        "--false-positive/--true-positive",
        "-fp/-tp",
        help="Mark whether this incident activity was a False Positive.",
    ),
    reason: Optional[str] = typer.Option(
        None,
        "--reason",
        "-r",
        help="Administrator reasoning/context (e.g. 'Authorized vulnerability scanner').",
    ),
    ip: Optional[str] = typer.Option(
        None, "--ip", help="Associated Source IP address to link to this feedback."
    ),
    user: Optional[str] = typer.Option(
        None, "--user", help="Associated target user account to link to this feedback."
    ),
    list_entries: bool = typer.Option(
        False, "--list", "-l", help="List historical administrator review feedback entries."
    ),
) -> None:
    """Record administrator review feedback for an incident, or list historical feedback."""
    if (
        list_entries
        or (incident_id and incident_id.lower() == "list" and reason is None)
        or (incident_id is None and reason is None)
    ):
        init_feedback_db()
        records = get_all_feedback(limit=50)

        if not records:
            console.print("[yellow]No administrator feedback records found in database.[/yellow]")
            return

        table = Table(
            title=f"Administrator Review Feedback ({len(records)} entries)",
            show_header=True,
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("Incident ID", style="bold cyan")
        table.add_column("Classification", style="bold")
        table.add_column("Source IP", style="bold yellow")
        table.add_column("Target User", style="bold white")
        table.add_column("Admin Reasoning", style="white")
        table.add_column("Timestamp", style="dim")

        for r in records:
            fp_str = (
                "[green]False Positive[/green]"
                if r.is_false_positive
                else "[red]True Positive[/red]"
            )
            ts_str = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "-"
            table.add_row(
                r.incident_id,
                fp_str,
                r.source_ip or "-",
                r.target_user or "-",
                r.admin_notes,
                ts_str,
            )

        console.print(table)
        return

    if incident_id is None:
        console.print("[bold red][X] Error: Incident ID is required.[/bold red]")
        raise typer.Exit(code=1)

    if reason is None:
        console.print("[bold red][X] Error: --reason option is required.[/bold red]")
        raise typer.Exit(code=1)

    fb_create = FeedbackCreate(
        incident_id=incident_id.strip(),
        is_false_positive=false_positive,
        admin_notes=reason.strip(),
        source_ip=ip.strip() if ip else None,
        target_user=user.strip() if user else None,
    )

    try:
        record = record_feedback(fb_create)
        fp_label = (
            "[bold green]False Positive[/bold green]"
            if record.is_false_positive
            else "[bold red]True Positive[/bold red]"
        )
        console.print(
            f"[bold green]✓ Administrator feedback recorded for incident:[/bold green] [cyan]{record.incident_id}[/cyan]\n"
            f"  [bold]Classification:[/bold] {fp_label}\n"
            f"  [bold]Admin Reasoning:[/bold] {record.admin_notes}\n"
            f"  [bold]Linked IP:[/bold] {record.source_ip or '[any]'}\n"
            f"  [bold]Linked User:[/bold] {record.target_user or '[any]'}"
        )
    except Exception as e:
        console.print(f"[bold red][X] Failed to record feedback: {e}[/bold red]")
        raise typer.Exit(code=1)
