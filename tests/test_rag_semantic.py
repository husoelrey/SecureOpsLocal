from pathlib import Path

import numpy as np
import pytest
from src.rag.embeddings import EMBEDDING_DIM, LocalEmbeddingService
from src.rag.packing import pack_context
from src.rag.retriever import SemanticRetriever
from src.rag.service import (
    get_vector_store,
    ingest_knowledge_document,
    list_indexed_documents,
)
from src.rag.vector_store import LocalVectorStore
from src.schemas.rag import DocumentChunk


def test_local_embedding_service_shape_and_norm():
    service = LocalEmbeddingService()
    texts = [
        "SSH brute force authentication failure anomaly",
        "NIST incident handling guidelines for credential access",
    ]
    vectors = service.encode(texts)
    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (2, EMBEDDING_DIM)

    # Check normalization
    norm1 = np.linalg.norm(vectors[0])
    norm2 = np.linalg.norm(vectors[1])
    assert pytest.approx(norm1, abs=1e-3) == 1.0
    assert pytest.approx(norm2, abs=1e-3) == 1.0


def test_local_vector_store_add_and_search():
    store = LocalVectorStore()

    chunk1 = DocumentChunk(
        chunk_id="chk_ssh_001",
        document_id="doc_nist_sp800",
        source_title="NIST SP 800-61 Rev 3",
        section_or_page="Section 3.2",
        content="Detecting brute force attacks against SSH services and unauthorized login attempts.",
        word_count=13,
    )
    chunk2 = DocumentChunk(
        chunk_id="chk_web_002",
        document_id="doc_owasp_top10",
        source_title="OWASP Top 10",
        section_or_page="A03:2021",
        content="Injection attacks including SQL Injection (SQLi) and Cross-Site Scripting (XSS).",
        word_count=13,
    )

    store.add_chunks([chunk1, chunk2])
    assert len(store.chunks) == 2

    # Query for SSH brute force
    results_ssh = store.search("SSH password brute force", top_k=2)
    assert len(results_ssh) > 0
    assert results_ssh[0].chunk_id == "chk_ssh_001"

    # Query for SQLi / XSS
    results_web = store.search("SQL injection XSS web exploit", top_k=2)
    assert len(results_web) > 0
    assert results_web[0].chunk_id == "chk_web_002"


def test_semantic_retriever_packing_integration():
    chunk1 = DocumentChunk(
        chunk_id="chk_01",
        document_id="doc_01",
        source_title="Incident Response Guide",
        section_or_page="Page 1",
        content="Isolate compromised endpoints and preserve audit logs without modification.",
        word_count=11,
    )
    chunk2 = DocumentChunk(
        chunk_id="chk_02",
        document_id="doc_02",
        source_title="Network Security Best Practices",
        section_or_page="Page 5",
        content="Implement multi-factor authentication and limit SSH access to trusted bastions.",
        word_count=12,
    )

    retriever = SemanticRetriever(chunks=[chunk1, chunk2])
    retrieved = retriever.retrieve("log preservation and isolation", top_k=2)

    assert len(retrieved) > 0
    assert retrieved[0][0].chunk_id == "chk_01"

    packed = pack_context(retrieved, max_words=500, max_chunks_per_source=2)
    assert len(packed) > 0
    assert packed[0].chunk_id == "chk_01"


def test_knowledge_ingestion_with_vector_indexing(tmp_path: Path):
    import uuid
    unique_tag = uuid.uuid4().hex[:8]
    doc_path = tmp_path / f"nist_incident_guidance_{unique_tag}.md"
    doc_path.write_text(
        f"# NIST SP 800-61 Incident Handling {unique_tag}\n\n"
        "## Containment Strategy\n"
        "Organizations must identify infected systems and preserve forensic evidence.\n\n"
        "## Eradication and Recovery\n"
        "Eliminate threat components and restore services from trusted baselines.\n",
        encoding="utf-8",
    )

    doc, chunks = ingest_knowledge_document(doc_path)
    assert doc.chunk_count == len(chunks)
    assert len(chunks) > 0

    docs = list_indexed_documents()
    assert any(d.document_id == doc.document_id for d in docs)

    vector_store = get_vector_store()
    results = vector_store.search("forensic evidence preservation", top_k=1)
    assert len(results) > 0
