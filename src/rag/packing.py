from src.schemas.rag import DocumentChunk


def pack_context(
    retrieved_chunks: list[tuple[DocumentChunk, float]],
    max_words: int = 1500,
    max_chunks_per_source: int = 2,
) -> list[DocumentChunk]:
    """
    Packs the retrieved chunks into a bounded context package.
    Enforces source-diversity limits to prevent one document from dominating.
    """
    packed_chunks = []
    source_counts: dict[str, int] = {}
    current_words = 0

    for chunk, score in retrieved_chunks:
        # Check source diversity limit
        if source_counts.get(chunk.document_id, 0) >= max_chunks_per_source:
            continue

        # Check budget limit
        if current_words + chunk.word_count > max_words:
            continue

        packed_chunks.append(chunk)
        source_counts[chunk.document_id] = source_counts.get(chunk.document_id, 0) + 1
        current_words += chunk.word_count

    return packed_chunks


def validate_citations(
    cited_ids: list[str], packed_chunks: list[DocumentChunk]
) -> list[str]:
    """
    Validates that every citation resolves correctly to a retrieved chunk 
    in the supplied context package.
    
    Returns a list of invalid citation IDs, if any.
    """
    valid_ids = {chunk.chunk_id for chunk in packed_chunks}
    invalid_citations = []

    for cid in cited_ids:
        if cid not in valid_ids:
            invalid_citations.append(cid)

    return invalid_citations
