import hashlib
import json
import os
from pathlib import Path
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import Base, SessionLocal, engine
from src.models.knowledge import KnowledgeChunk, KnowledgeDocument
from src.rag.chunking import chunk_document
from src.rag.ingestion import parse_document
from src.schemas.rag import DocumentChunk

MAX_KNOWLEDGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MiB
ALLOWED_KNOWLEDGE_EXTENSIONS = {".pdf", ".md", ".txt"}


class KnowledgeBaseError(Exception):
    """Base exception for knowledge base operations."""
    pass


class DocumentAlreadyExistsError(KnowledgeBaseError):
    """Raised when a document with identical hash already exists."""
    pass


class InvalidDocumentError(KnowledgeBaseError):
    """Raised when a document fails security, format, or size validation."""
    pass


def init_knowledge_db() -> None:
    """Ensure database tables for knowledge base exist."""
    Base.metadata.create_all(bind=engine)


def validate_file_path(path: Path) -> None:
    """Validate that the target file exists, is within size bounds, and is an allowed format."""
    if not path.exists() or not path.is_file():
        raise InvalidDocumentError(f"File '{path}' does not exist or is not a regular file.")

    ext = path.suffix.lower()
    if ext not in ALLOWED_KNOWLEDGE_EXTENSIONS:
        raise InvalidDocumentError(
            f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_KNOWLEDGE_EXTENSIONS))}"
        )

    file_size = path.stat().st_size
    if file_size > MAX_KNOWLEDGE_SIZE_BYTES:
        raise InvalidDocumentError(
            f"File size ({file_size / (1024 * 1024):.2f} MiB) exceeds the maximum allowed limit of 20 MiB."
        )

    if file_size == 0:
        raise InvalidDocumentError("File is empty.")

    # Check for archive magic bytes
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            if header.startswith(b"PK") or header.startswith(b"\x1f\x8b") or header.startswith(b"BZh"):
                raise InvalidDocumentError("Archive files (zip, gzip, bzip) are not allowed.")
    except OSError as e:
        raise InvalidDocumentError(f"Failed to read file: {e}") from e


def compute_sha256(path: Path) -> str:
    """Calculate the SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def ingest_knowledge_document(
    file_path: Path,
    db: Session | None = None,
) -> Tuple[KnowledgeDocument, list[KnowledgeChunk]]:
    """
    Ingests a PDF, Markdown, or text file into the knowledge base:
    1. Validates file security, extension, and size.
    2. Checks for duplicate hash.
    3. Extracts and cleans text content.
    4. Performs heading-aware chunking.
    5. Persists document metadata and chunks into SQLite.
    """
    init_knowledge_db()
    validate_file_path(file_path)

    file_hash = compute_sha256(file_path)
    filename = file_path.name
    file_size = file_path.stat().st_size
    ext = file_path.suffix.lower().lstrip(".")

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Check duplicate
        existing = db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.sha256 == file_hash)
        ).scalar_one_or_none()
        if existing is not None:
            raise DocumentAlreadyExistsError(
                f"Document '{filename}' with SHA-256 '{file_hash[:12]}...' is already indexed (Document ID: {existing.document_id})."
            )

        # Parse and extract text
        doc_parsed = parse_document(file_path, filename, file_hash)

        doc_id = f"doc_{file_hash[:12]}"
        chunks = chunk_document(
            content=doc_parsed.content,
            document_id=doc_id,
            source_title=filename,
            max_words=400,
            overlap=50,
        )

        meta_json = json.dumps(doc_parsed.metadata)

        db_doc = KnowledgeDocument(
            document_id=doc_id,
            filename=filename,
            sha256=file_hash,
            file_format=ext,
            byte_size=file_size,
            chunk_count=len(chunks),
            meta_info=meta_json,
        )
        db.add(db_doc)

        db_chunks = []
        for chk in chunks:
            db_chunk = KnowledgeChunk(
                chunk_id=chk.chunk_id,
                document_id=doc_id,
                source_title=chk.source_title,
                section_or_page=chk.section_or_page,
                content=chk.content,
                word_count=chk.word_count,
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

        db.commit()
        db.refresh(db_doc)
        return db_doc, db_chunks

    except Exception:
        db.rollback()
        raise
    finally:
        if close_session:
            db.close()


def list_indexed_documents(db: Session | None = None) -> list[KnowledgeDocument]:
    """Retrieve all indexed knowledge base documents ordered by creation date."""
    init_knowledge_db()
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        docs = db.execute(
            select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
        ).scalars().all()
        return list(docs)
    finally:
        if close_session:
            db.close()


def load_all_rag_chunks(db: Session | None = None) -> list[DocumentChunk]:
    """Load all chunk records from the database and convert them to Pydantic DocumentChunks."""
    init_knowledge_db()
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        db_chunks = db.execute(
            select(KnowledgeChunk).order_by(KnowledgeChunk.id.asc())
        ).scalars().all()

        return [
            DocumentChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                source_title=c.source_title,
                section_or_page=c.section_or_page,
                content=c.content,
                word_count=c.word_count,
            )
            for c in db_chunks
        ]
    finally:
        if close_session:
            db.close()
