from pathlib import Path

from fastapi import HTTPException, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.schemas.rag import IngestedDocument


def clean_text(text: str) -> str:
    """Normalize excessive whitespace, reduce repeated newlines."""
    lines = text.splitlines()
    cleaned_lines = [line.strip() for line in lines]
    # keep empty lines but limit to 2 max? Simple approach: single newline for now.
    return "\n".join(line for line in cleaned_lines if line)


def extract_pdf(file_path: Path) -> tuple[str, dict[str, str | int]]:
    try:
        reader = PdfReader(str(file_path))
    except (PdfReadError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unreadable PDF file",
        ) from e

    text_content = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text and page_text.strip():
            text_content.append(f"--- Page {i+1} ---\n" + page_text)

    content = clean_text("\n".join(text_content))
    if not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF contains no extractable text or is image-only. OCR is outside the MVP.",
        )

    return content, {"pages": len(reader.pages), "format": "pdf"}


def extract_text(file_path: Path) -> tuple[str, dict[str, str | int]]:
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid text encoding, only valid UTF-8 is allowed",
        ) from e

    return clean_text(content), {"format": "text"}


def parse_document(file_path: Path, filename: str, file_hash: str) -> IngestedDocument:
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        content, metadata = extract_pdf(file_path)
    elif ext in {".txt", ".md"}:
        content, metadata = extract_text(file_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file extension for ingestion",
        )

    return IngestedDocument(
        filename=filename,
        content=content,
        sha256=file_hash,
        metadata=metadata,
    )
