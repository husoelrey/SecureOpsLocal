"""Incident Analysis CLI Command."""

import asyncio
import datetime
import uuid
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.llm.analyzer import IncidentAnalyzer
from src.llm.base import LocalLLMProvider
from src.llm.foundry import FoundryLocalProvider
from src.llm.ollama import OllamaProvider
from src.parser.aggregator import aggregate_logs
from src.parser.aws import AWSCloudTrailParser
from src.parser.base import LogParser
from src.parser.nginx import NginxAccessParser
from src.parser.ssh import SSHAuthLogParser
from src.parser.windows import WindowsEventLogParser
from src.rag.packing import pack_context
from src.rag.query import build_retrieval_query
from src.rag.retriever import TFIDFRetriever
from src.rag.service import load_all_rag_chunks
from src.schemas.analysis import LogAnalysis
from src.schemas.incident_report import IncidentReportCreate
from src.schemas.rag import DocumentChunk

console = Console()

MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024  # 5 MiB
ALLOWED_LOG_EXTENSIONS = {".log", ".txt", ".json", ".evtx"}


def get_parser_for_log_type(log_type: str) -> LogParser:
    """Resolve the appropriate LogParser implementation for the specified log type."""
    normalized = (log_type or "").strip().lower()
    if normalized in ("ssh", "sshd", "auth"):
        return SSHAuthLogParser()
    elif normalized in ("windows", "win", "evtx", "eventlog"):
        return WindowsEventLogParser()
    elif normalized in ("nginx", "web", "apache", "waf"):
        return NginxAccessParser()
    elif normalized in ("aws", "cloudtrail", "aws_cloudtrail"):
        return AWSCloudTrailParser()
    else:
        raise ValueError(
            f"Unsupported log type '{log_type}'. Supported: ssh, windows, nginx, aws."
        )


def validate_log_file(logfile: Path) -> None:
    """Validate log file existence, extension, and size."""
    if not logfile.exists() or not logfile.is_file():
        console.print(
            f"[bold red][X] Error: File '{logfile}' does not exist or is not a regular file.[/bold red]"
        )
        raise typer.Exit(code=1)

    ext = logfile.suffix.lower()
    if ext not in ALLOWED_LOG_EXTENSIONS:
        console.print(
            f"[bold red][X] Error: Unsupported log file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_LOG_EXTENSIONS))}[/bold red]"
        )
        raise typer.Exit(code=1)

    file_size = logfile.stat().st_size
    if file_size > MAX_LOG_SIZE_BYTES:
        console.print(
            f"[bold red][X] Error: File size ({file_size / (1024 * 1024):.2f} MiB) exceeds the 5 MiB maximum limit.[/bold red]"
        )
        raise typer.Exit(code=1)

    if file_size == 0:
        console.print("[bold red][X] Error: Log file is empty.[/bold red]")
        raise typer.Exit(code=1)


def display_deterministic_facts(analysis: LogAnalysis, logfile: Path, log_type: str = "ssh") -> None:
    """Render deterministic parser findings into a clean Rich table."""
    time_str = "N/A"
    if analysis.start_time and analysis.end_time:
        time_str = (
            f"{analysis.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC -> "
            f"{analysis.end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

    summary_text = (
        f"[bold]Target File:[/bold] {logfile.name}  |  "
        f"[bold]Log Type:[/bold] {log_type.upper()}  |  "
        f"[bold]Total Events/Lines:[/bold] {analysis.total_lines}  |  "
        f"[bold]Unparsed:[/bold] {analysis.unparsed_lines}  |  "
        f"[bold]Unique Source IPs:[/bold] {len(analysis.ip_aggregations)}\n"
        f"[bold]Time Span:[/bold] {time_str}"
    )

    table = Table(
        title="Deterministic Facts (Parser Verifiable Truth)",
        show_header=True,
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Source IP", style="bold yellow", no_wrap=True)
    table.add_column("Failed / Attack Attempts", justify="right", style="bold red")
    table.add_column("Successful Events", justify="right", style="bold green")
    table.add_column("Targeted Accounts / Identifiers", style="white")
    table.add_column("First Activity (UTC)", style="dim")
    table.add_column("Last Activity (UTC)", style="dim")

    for agg in analysis.ip_aggregations:
        first_str = (
            agg.first_seen.strftime("%Y-%m-%d %H:%M:%S") if agg.first_seen else "N/A"
        )
        last_str = (
            agg.last_seen.strftime("%Y-%m-%d %H:%M:%S") if agg.last_seen else "N/A"
        )
        users_str = ", ".join(agg.users_attempted) if agg.users_attempted else "[none]"

        failed_style = "bold red" if agg.failed_attempts > 0 else "dim"
        success_style = "bold green" if agg.successful_attempts > 0 else "dim"

        table.add_row(
            agg.ip,
            f"[{failed_style}]{agg.failed_attempts}[/{failed_style}]",
            f"[{success_style}]{agg.successful_attempts}[/{success_style}]",
            users_str,
            first_str,
            last_str,
        )

    console.print(
        Panel(summary_text, title="[bold blue]Log Overview[/bold blue]", expand=False)
    )
    console.print(table)


def display_assessment(report: IncidentReportCreate, packed_chunks: list[DocumentChunk]) -> None:
    """Render the cautious LLM risk assessment, recommendations, and citations."""
    risk_level = report.risk_level.upper()
    if risk_level == "HIGH":
        risk_badge = "[bold white on red] HIGH RISK [/bold white on red]"
    elif risk_level == "MEDIUM":
        risk_badge = "[bold black on yellow] MEDIUM RISK [/bold black on yellow]"
    elif risk_level == "LOW":
        risk_badge = "[bold white on green] LOW RISK [/bold white on green]"
    else:
        risk_badge = f"[bold white on blue] {risk_level} [/bold white on blue]"

    status_badge = (
        "[green]COMPLETED[/green]"
        if report.status == "completed"
        else f"[yellow]{report.status.upper()}[/yellow]"
    )

    # Build assessment content
    content_lines = [
        f"[bold]Assessment Status:[/bold] {status_badge}    [bold]Assessed Risk Level:[/bold] {risk_badge}\n",
        f"[bold cyan]Executive Summary:[/bold cyan]\n{report.summary}\n",
    ]

    if report.possible_interpretations:
        content_lines.append(
            "[bold cyan]Possible Evidence-Supported Interpretations:[/bold cyan]"
        )
        for interp in report.possible_interpretations:
            content_lines.append(f"  [bold blue]*[/bold blue] {interp}")
        content_lines.append("")

    if report.risk_reasoning:
        content_lines.append(
            f"[bold cyan]Risk Reasoning:[/bold cyan]\n{report.risk_reasoning}\n"
        )

    if report.recommended_actions:
        content_lines.append(
            "[bold cyan]Recommended Defensive Actions (Non-Destructive):[/bold cyan]"
        )
        for action in report.recommended_actions:
            content_lines.append(f"  [bold green]+[/bold green] {action}")
        content_lines.append("")

    console.print(
        Panel(
            "\n".join(content_lines),
            title="[bold green]Cautious AI Incident Assessment[/bold green]",
            expand=False,
        )
    )

    # Citations section
    chunk_map = {chk.chunk_id: chk for chk in packed_chunks}
    if report.citations:
        cit_table = Table(
            title="Evidence & Security Guidance Citations",
            show_header=True,
            header_style="bold cyan",
            show_lines=True,
        )
        cit_table.add_column("Chunk ID", style="bold yellow")
        cit_table.add_column("Source Document", style="white")
        cit_table.add_column("Section / Reference", style="green")

        for cid in report.citations:
            chunk = chunk_map.get(cid)
            if chunk:
                cit_table.add_row(cid, chunk.source_title, chunk.section_or_page)
            else:
                cit_table.add_row(
                    cid, "[dim]Referenced Document[/dim]", "[dim]N/A[/dim]"
                )

        console.print(cit_table)
    else:
        console.print(
            "[dim]No external knowledge base citations were referenced in this assessment.[/dim]"
        )

    # Limitations
    if report.limitations:
        lim_panel = "\n".join(f"  [dim]- {lim}[/dim]" for lim in report.limitations)
        console.print(
            Panel(lim_panel, title="[dim]Analysis Limitations[/dim]", expand=False)
        )


def analyze_log_file(
    logfile: Path = typer.Argument(
        ...,
        help="Path to the security log file (.log, .txt, .json, .evtx).",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    log_type: str = typer.Option(
        "ssh",
        "--log-type",
        "-t",
        help="Type of security log source ('ssh', 'windows', 'nginx', 'aws').",
    ),
    model: str = typer.Option(
        "foundation-sec-8b-reasoning:q4_k_m",
        "--model",
        "-m",
        help="Local LLM deployment profile name to run for analysis.",
    ),
    provider_name: str = typer.Option(
        "ollama",
        "--provider",
        "-p",
        help="Local runtime provider ('ollama' or 'foundry').",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        "-u",
        help="Custom base URL for the local LLM runtime (e.g. http://localhost:11434).",
    ),
    year: Optional[int] = typer.Option(
        None,
        "--year",
        "-y",
        help="Year to assume for legacy syslog timestamps (default: current UTC year).",
    ),
    output_json: Optional[Path] = typer.Option(
        None,
        "--output-json",
        "-o",
        help="Optional path to export the structured IncidentReport to JSON.",
    ),
    top_k: int = typer.Option(
        5,
        "--top-k",
        "-k",
        help="Number of relevant knowledge base chunks to retrieve.",
    ),
) -> None:
    """Analyze a security log file (SSH, Windows, Nginx, AWS), retrieve RAG guidance, and generate a cautious risk report."""
    validate_log_file(logfile)

    try:
        parser = get_parser_for_log_type(log_type)
    except ValueError as e:
        console.print(f"[bold red][X] Error: {e}[/bold red]")
        raise typer.Exit(code=1)

    current_year = year or datetime.datetime.now(datetime.timezone.utc).year
    incident_id = f"inc_{uuid.uuid4().hex[:8]}"

    console.print(
        Panel(
            f"[bold cyan]SecureOps Local Incident Review[/bold cyan]\n"
            f"[bold]Incident ID:[/bold] {incident_id}  |  [bold]Target:[/bold] {logfile.name}\n"
            f"[bold]Log Type:[/bold] {log_type.upper()}  |  [bold]Model Profile:[/bold] {model} ({provider_name})",
            title="[bold blue]SecureOps Local[/bold blue]",
            expand=False,
        )
    )

    # 1. Deterministic Parsing
    with console.status(
        f"[bold green]Parsing {log_type.upper()} logs deterministically...[/bold green]",
        spinner="dots",
    ):
        try:
            parsed_lines = list(
                parser.parse_file(str(logfile), current_year=current_year)
            )
        except Exception as e:
            console.print(f"[bold red][X] Failed to parse log file: {e}[/bold red]")
            raise typer.Exit(code=1)

        analysis = aggregate_logs(parsed_lines)

    if analysis.total_lines == 0:
        console.print(
            "[bold yellow][!] No log lines were parsed from the input file.[/bold yellow]"
        )
        raise typer.Exit(code=0)

    # Display Deterministic Facts immediately
    display_deterministic_facts(analysis, logfile, log_type=log_type)

    # 2. RAG Retrieval
    packed_chunks = []
    with console.status(
        "[bold green]Retrieving security guidance from local knowledge base...[/bold green]",
        spinner="dots",
    ):
        all_chunks = load_all_rag_chunks()
        if all_chunks:
            retrieval_query = build_retrieval_query(analysis)
            retriever = TFIDFRetriever(all_chunks)
            retrieved = retriever.retrieve(retrieval_query, top_k=top_k)
            packed_chunks = pack_context(
                retrieved, max_words=1500, max_chunks_per_source=2
            )

    # 3. LLM Generation
    provider: LocalLLMProvider
    if provider_name.lower() == "foundry":
        effective_url = base_url or "http://localhost:39251"
        provider = FoundryLocalProvider(base_url=effective_url, model_name=model)
    else:
        effective_url = base_url or "http://localhost:11434"
        provider = OllamaProvider(base_url=effective_url, model_name=model)

    analyzer = IncidentAnalyzer(provider=provider, max_retries=1)

    try:
        with console.status(
            f"[bold green]Generating cautious risk assessment with {model}...[/bold green]",
            spinner="dots",
        ):
            report = asyncio.run(
                analyzer.analyze_incident(
                    incident_id=incident_id,
                    analysis=analysis,
                    chunks=packed_chunks,
                )
            )
    except Exception as e:
        console.print(
            Panel(
                f"[bold yellow][!] Local LLM Generation Warning:[/bold yellow]\n"
                f"Could not connect to {provider_name.upper()} at [cyan]{effective_url}[/cyan].\n"
                f"[dim]Reason: {e}[/dim]\n\n"
                f"[bold green]Note:[/bold green] Parser truth and deterministic findings remain completely intact above.",
                title="[bold yellow]Local LLM Runtime Offline[/bold yellow]",
                expand=False,
            )
        )
        return

    # 4. Render Assessment & Output
    display_assessment(report, packed_chunks)

    # 5. Export JSON if requested
    if output_json:
        try:
            output_json.parent.mkdir(parents=True, exist_ok=True)
            output_json.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            console.print(
                f"[bold green]✓ Structured incident report exported to:[/bold green] [cyan]{output_json}[/cyan]"
            )
        except Exception as e:
            console.print(f"[bold red][X] Failed to export JSON report: {e}[/bold red]")
