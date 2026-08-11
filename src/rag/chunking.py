import hashlib
import re

from src.schemas.rag import DocumentChunk


def generate_chunk_id(document_id: str, index: int, content: str) -> str:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
    return f"{document_id}_chk_{index}_{content_hash}"


def split_text_with_overlap(
    text: str, max_words: int = 400, overlap: int = 50
) -> list[str]:
    """Splits a block of text into smaller chunks based on word count with overlap."""
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += max_words - overlap
    return chunks


def chunk_document(
    content: str,
    document_id: str,
    source_title: str,
    max_words: int = 400,
    overlap: int = 50,
) -> list[DocumentChunk]:
    """
    Implements heading-aware chunking for documents.
    Preserves source metadata, page, and section references.
    """
    lines = content.splitlines()

    sections: list[tuple[str, str]] = []
    current_section = "General"
    current_lines: list[str] = []

    header_pattern = re.compile(r"^(#+)\s+(.+)$")
    page_pattern = re.compile(r"^---\s+(Page\s+\d+)\s+---$")

    for line in lines:
        header_match = header_pattern.match(line)
        page_match = page_pattern.match(line)

        is_boundary = bool(header_match or page_match)

        if is_boundary:
            # Only start a new section if current buffer has substantial text.
            # This prevents short headers from being orphaned.
            word_cnt = len(" ".join(current_lines).split())
            if word_cnt > 15:
                sections.append((current_section, "\n".join(current_lines)))
                current_lines = []

            if header_match:
                current_section = header_match.group(2).strip()
            elif page_match:
                current_section = page_match.group(1).strip()

            current_lines.append(line)
        else:
            if line.strip():
                current_lines.append(line)

    if current_lines:
        sections.append((current_section, "\n".join(current_lines)))

    chunks = []
    chunk_index = 0
    for section_name, section_text in sections:
        text_chunks = split_text_with_overlap(
            section_text, max_words=max_words, overlap=overlap
        )

        for t_chunk in text_chunks:
            word_count = len(t_chunk.split())
            if word_count == 0:
                continue

            chunk_id = generate_chunk_id(document_id, chunk_index, t_chunk)
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    source_title=source_title,
                    section_or_page=section_name,
                    content=t_chunk,
                    word_count=word_count,
                )
            )
            chunk_index += 1

    return chunks
