from src.rag.packing import pack_context, validate_citations
from src.schemas.rag import DocumentChunk


def test_pack_context_diversity_limit():
    chunks = [
        (DocumentChunk(chunk_id="c1", document_id="d1", source_title="D1", section_or_page="1", content="test", word_count=10), 0.9),
        (DocumentChunk(chunk_id="c2", document_id="d1", source_title="D1", section_or_page="1", content="test", word_count=10), 0.8),
        (DocumentChunk(chunk_id="c3", document_id="d1", source_title="D1", section_or_page="1", content="test", word_count=10), 0.7),
        (DocumentChunk(chunk_id="c4", document_id="d2", source_title="D2", section_or_page="1", content="test", word_count=10), 0.6),
    ]

    packed = pack_context(chunks, max_chunks_per_source=2)
    
    # Even though c3 had a higher score than c4, it should be dropped due to the diversity limit of 2 per source.
    assert len(packed) == 3
    assert packed[0].chunk_id == "c1"
    assert packed[1].chunk_id == "c2"
    assert packed[2].chunk_id == "c4"


def test_pack_context_word_budget():
    chunks = [
        (DocumentChunk(chunk_id="c1", document_id="d1", source_title="D1", section_or_page="1", content="test", word_count=100), 0.9),
        (DocumentChunk(chunk_id="c2", document_id="d2", source_title="D2", section_or_page="1", content="test", word_count=150), 0.8),
        (DocumentChunk(chunk_id="c3", document_id="d3", source_title="D3", section_or_page="1", content="test", word_count=100), 0.7),
    ]

    # Budget allows c1 (100). c2 (150) is skipped because 100+150>200.
    # c3 (100) is added because 100+100=200.
    packed = pack_context(chunks, max_words=200)
    
    assert len(packed) == 2
    assert packed[0].chunk_id == "c1"
    assert packed[1].chunk_id == "c3"


def test_validate_citations():
    packed = [
        DocumentChunk(chunk_id="c1", document_id="d1", source_title="D1", section_or_page="1", content="test", word_count=10),
        DocumentChunk(chunk_id="c2", document_id="d2", source_title="D2", section_or_page="1", content="test", word_count=10),
    ]

    # All valid
    invalid = validate_citations(["c1", "c2"], packed)
    assert len(invalid) == 0

    # One invalid
    invalid2 = validate_citations(["c1", "c3"], packed)
    assert len(invalid2) == 1
    assert invalid2[0] == "c3"

    # All invalid
    invalid3 = validate_citations(["c99"], packed)
    assert len(invalid3) == 1
    assert invalid3[0] == "c99"
