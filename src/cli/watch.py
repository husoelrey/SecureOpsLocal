"""Daemon Watcher CLI Command."""

import asyncio
import datetime
import uuid
from pathlib import Path
from typing import List, Optional

import typer
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.cli.analyze import (
    display_assessment,
    display_deterministic_facts,
    get_parser_for_log_type,
)
from src.llm.analyzer import IncidentAnalyzer
from src.llm.base import LocalLLMProvider
from src.llm.foundry import FoundryLocalProvider
from src.llm.ollama import OllamaProvider
from src.parser.aggregator import aggregate_logs
from src.rag.packing import pack_context
from src.rag.query import build_retrieval_query
from src.rag.retriever import TFIDFRetriever
from src.rag.service import load_all_rag_chunks
from src.schemas.parsed_log_line import ParsedLogLineCreate
from src.watcher.engine import LogWatcherEngine
from src.watcher.window import SlidingWindowEventTracker

console = Console()


def print_massive_alert_banner(
    incident_id: str,
    log_type: str,
    event_count: int,
    threshold: int,
    window_seconds: int,
) -> None:
    """Render a massive, high-impact terminal security alert header."""
    header_text = Text()
    header_text.append("🚨 🚨 🚨  CRITICAL SECURITY INCIDENT DETECTED  🚨 🚨 🚨\n", style="bold white on red blink")
    header_text.append(f"INCIDENT ID: {incident_id}  |  LOG SOURCE: {log_type.upper()}\n", style="bold yellow")
    header_text.append(
        f"THRESHOLD BREACHED: {event_count} failure/attack events recorded within {window_seconds}s (Threshold: {threshold})\n",
        style="bold white",
    )
    header_text.append(
        f"TIMESTAMP: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        style="dim white",
    )

    alert_panel = Panel(
        Align.center(header_text),
        title="[bold red]─── SECUREOPS LOCAL REAL-TIME SURVEILLANCE ALERT ───[/bold red]",
        subtitle="[bold red]─── AUTOMATIC TRIAGE PIPELINE TRIGGERED ───[/bold red]",
        border_style="bold red",
        padding=(1, 2),
        expand=False,
    )
    console.print("")
    console.print(alert_panel)
    console.print("")


def handle_incident_breach(
    window_events: List[ParsedLogLineCreate],
    logfile: Path,
    log_type: str,
    threshold: int,
    window_seconds: int,
    model: str,
    provider_name: str,
    base_url: Optional[str],
    top_k: int,
) -> None:
    """Full incident response handler when the failure threshold is breached."""
    incident_id = f"inc_live_{uuid.uuid4().hex[:8]}"

    # 1. Print Massive Alert Banner
    print_massive_alert_banner(
        incident_id=incident_id,
        log_type=log_type,
        event_count=len(window_events),
        threshold=threshold,
        window_seconds=window_seconds,
    )

    # 2. Deterministic Fact Aggregation
    analysis = aggregate_logs(window_events)
    display_deterministic_facts(analysis, logfile, log_type=log_type)

    # 3. RAG Retrieval
    packed_chunks = []
    with console.status("[bold green]Retrieving relevant security guidance (NIST/CISA/OWASP)...[/bold green]", spinner="dots"):
        all_chunks = load_all_rag_chunks()
        if all_chunks:
            retrieval_query = build_retrieval_query(analysis)
            retriever = TFIDFRetriever(all_chunks)
            retrieved = retriever.retrieve(retrieval_query, top_k=top_k)
            packed_chunks = pack_context(retrieved, max_words=1500, max_chunks_per_source=2)

    # 4. LLM Cautious Assessment
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
            f"[bold green]Synthesizing cautious incident assessment with {model}...[/bold green]",
            spinner="dots",
        ):
            report = asyncio.run(
                analyzer.analyze_incident(
                    incident_id=incident_id,
                    analysis=analysis,
                    chunks=packed_chunks,
                )
            )
        display_assessment(report, packed_chunks)
    except Exception as e:
        console.print(
            Panel(
                f"[bold yellow][!] Local LLM Runtime Warning:[/bold yellow]\n"
                f"Could not reach {provider_name.upper()} at [cyan]{effective_url}[/cyan].\n"
                f"[dim]Reason: {e}[/dim]\n\n"
                f"[bold green]Note:[/bold green] Deterministic facts and threshold breach logs remain fully preserved above.",
                title="[bold yellow]Local LLM Runtime Offline[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

    console.print("\n[bold cyan]⚡ Resuming continuous log surveillance...[/bold cyan]\n")


def watch_log_file(
    logfile: Path = typer.Argument(
        ...,
        help="Path to the security log file to tail and monitor.",
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
    threshold: int = typer.Option(
        5,
        "--threshold",
        "-n",
        help="Number of failure/attack events in the sliding window to trigger an incident.",
    ),
    window_seconds: int = typer.Option(
        60,
        "--window-seconds",
        "-w",
        help="Sliding window duration in seconds (default: 60s).",
    ),
    model: str = typer.Option(
        "foundation-sec-8b-reasoning:q4_k_m",
        "--model",
        "-m",
        help="Local LLM deployment profile name for incident synthesis.",
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
        help="Custom base URL for the local LLM runtime.",
    ),
    from_beginning: bool = typer.Option(
        False,
        "--from-beginning",
        "-b",
        help="If set, process existing lines from file start before tailing new additions.",
    ),
    top_k: int = typer.Option(
        5,
        "--top-k",
        "-k",
        help="Number of knowledge base chunks to retrieve.",
    ),
) -> None:
    """
    Continuously tail a security log file in background daemon mode.
    Maintains a sliding window of events and automatically triggers RAG and LLM analysis on anomaly bursts.
    """
    if not logfile.exists():
        console.print(f"[bold red][X] Error: File '{logfile}' does not exist.[/bold red]")
        raise typer.Exit(code=1)

    try:
        parser = get_parser_for_log_type(log_type)
    except ValueError as e:
        console.print(f"[bold red][X] Error: {e}[/bold red]")
        raise typer.Exit(code=1)

    tracker = SlidingWindowEventTracker(
        threshold=threshold,
        window_seconds=window_seconds,
    )

    console.print(
        Panel(
            f"[bold cyan]SecureOps Local — Continuous Log Surveillance Daemon[/bold cyan]\n"
            f"[bold]Monitoring Target:[/bold] {logfile.name} ({logfile.resolve()})\n"
            f"[bold]Log Source Type:[/bold] {log_type.upper()}  |  [bold]Threshold:[/bold] {threshold} failures / {window_seconds}s\n"
            f"[bold]AI Model Profile:[/bold] {model} ({provider_name})\n"
            f"[dim]Press Ctrl+C at any time to safely stop the daemon.[/dim]",
            title="[bold green]Daemon Active[/bold green]",
            border_style="green",
            expand=False,
        )
    )

    def on_breach_callback(events: List[ParsedLogLineCreate]) -> None:
        handle_incident_breach(
            window_events=events,
            logfile=logfile,
            log_type=log_type,
            threshold=threshold,
            window_seconds=window_seconds,
            model=model,
            provider_name=provider_name,
            base_url=base_url,
            top_k=top_k,
        )

    engine = LogWatcherEngine(
        file_path=logfile,
        parser=parser,
        tracker=tracker,
        on_breach=on_breach_callback,
        start_from_beginning=from_beginning,
    )

    try:
        engine.start(poll_interval=0.5, blocking=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping surveillance daemon...[/yellow]")
        engine.stop()
        console.print("[green]Surveillance daemon stopped safely.[/green]")
