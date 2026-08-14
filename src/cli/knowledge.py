"""Knowledge Base CLI commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.rag.service import (
    DocumentAlreadyExistsError,
    InvalidDocumentError,
    ingest_knowledge_document,
    list_indexed_documents,
)

knowledge_app = typer.Typer(
    name="knowledge",
    help="Manage local security knowledge base documents (add, list).",
    no_args_is_help=True,
)

console = Console()


@knowledge_app.command("add")
def add_document(
    filepath: Path = typer.Argument(
        ...,
        help="Path to the PDF, Markdown, or text security document to ingest.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
) -> None:
    """Ingest a new PDF or Markdown file into the local RAG database."""
    with console.status(f"[bold green]Ingesting and indexing '{filepath.name}'...[/bold green]", spinner="dots"):
        try:
            doc, _ = ingest_knowledge_document(filepath)
        except DocumentAlreadyExistsError as e:
            console.print(f"[bold yellow][!] Duplicate document:[/bold yellow] {e}")
            raise typer.Exit(code=1)
        except InvalidDocumentError as e:
            console.print(f"[bold red][X] Validation error:[/bold red] {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[bold red][X] Ingestion failed:[/bold red] {e}")
            raise typer.Exit(code=1)

    table = Table(title="Document Ingestion Summary", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="bold")
    table.add_column("Value", style="green")

    table.add_row("Document ID", doc.document_id)
    table.add_row("Filename", doc.filename)
    table.add_row("Format", doc.file_format.upper())
    table.add_row("Size", f"{doc.byte_size / 1024:.1f} KB")
    table.add_row("Chunks Created", str(doc.chunk_count))
    table.add_row("SHA-256", f"{doc.sha256[:16]}...{doc.sha256[-8:]}")

    console.print(Panel(table, title="[bold green]Ingestion Complete[/bold green]", expand=False))


@knowledge_app.command("list")
def list_documents() -> None:
    """Display a rich table of all currently indexed documents."""
    docs = list_indexed_documents()

    if not docs:
        console.print(
            Panel(
                "[yellow]No documents currently indexed in the knowledge base.[/yellow]\n\n"
                "[dim]Use [bold]secureops knowledge add <filepath>[/bold] to add security guidance documents (e.g. NIST, CISA, OWASP).[/dim]",
                title="[bold blue]Knowledge Base Empty[/bold blue]",
                expand=False,
            )
        )
        return

    table = Table(
        title=f"Indexed Knowledge Base Documents ({len(docs)} total)",
        show_header=True,
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Doc ID", style="bold yellow", no_wrap=True)
    table.add_column("Filename", style="bold white")
    table.add_column("Format", style="green", justify="center")
    table.add_column("Chunks", style="magenta", justify="right")
    table.add_column("Size", style="cyan", justify="right")
    table.add_column("SHA-256 Digest", style="dim", no_wrap=True)
    table.add_column("Indexed At (UTC)", style="dim")

    for doc in docs:
        if doc.byte_size < 1024 * 1024:
            size_str = f"{doc.byte_size / 1024:.1f} KB"
        else:
            size_str = f"{doc.byte_size / (1024 * 1024):.2f} MB"

        created_str = doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "N/A"
        hash_short = f"{doc.sha256[:8]}...{doc.sha256[-8:]}"

        table.add_row(
            doc.document_id,
            doc.filename,
            doc.file_format.upper(),
            str(doc.chunk_count),
            size_str,
            hash_short,
            created_str,
        )

    console.print(table)
