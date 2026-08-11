from src.rag.retriever import TFIDFRetriever
from src.schemas.rag import DocumentChunk


def test_tfidf_retriever_basic():
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            document_id="d1",
            source_title="Apple Document",
            section_or_page="1",
            content="Apple is a fruit. A very tasty fruit.",
            word_count=8
        ),
        DocumentChunk(
            chunk_id="c2",
            document_id="d1",
            source_title="Banana Document",
            section_or_page="2",
            content="Banana is also a fruit, yellow and long.",
            word_count=8
        ),
        DocumentChunk(
            chunk_id="c3",
            document_id="d2",
            source_title="Car Document",
            section_or_page="1",
            content="Cars are vehicles used for transportation.",
            word_count=6
        ),
    ]

    retriever = TFIDFRetriever(chunks)
    
    # Query for fruit
    results = retriever.retrieve("fruit", top_k=2)
    assert len(results) == 2
    # c1 has 'fruit' twice, c2 has it once
    assert results[0][0].chunk_id == "c1"
    assert results[1][0].chunk_id == "c2"

    # Query for transportation
    results2 = retriever.retrieve("transportation", top_k=1)
    assert len(results2) == 1
    assert results2[0][0].chunk_id == "c3"
    
    # Query for something non-existent
    results3 = retriever.retrieve("spaceship", top_k=5)
    assert len(results3) == 0


def test_tfidf_retriever_empty():
    retriever = TFIDFRetriever([])
    assert retriever.retrieve("anything") == []
