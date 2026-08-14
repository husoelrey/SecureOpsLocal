import logging
import math
import re
from collections import defaultdict
from typing import List, Optional, Tuple

from src.rag.embeddings import LocalEmbeddingService
from src.rag.vector_store import LocalVectorStore
from src.schemas.rag import DocumentChunk

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """
    Local Semantic Vector Retriever using sentence-transformers and FAISS
    (with cosine similarity fallback).
    """

    def __init__(
        self,
        chunks: List[DocumentChunk],
        vector_store: Optional[LocalVectorStore] = None,
        embedding_service: Optional[LocalEmbeddingService] = None,
    ):
        self.chunks = chunks
        if vector_store is not None:
            self.vector_store = vector_store
        else:
            self.vector_store = LocalVectorStore(embedding_service=embedding_service)
            if chunks:
                self.vector_store.add_chunks(chunks)

    def retrieve(
        self, query: str, top_k: int = 5, min_score: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Retrieve top-k relevant chunks based on dense semantic cosine similarity.
        """
        if not self.chunks:
            return []

        retrieved = self.vector_store.search(query, top_k=top_k)
        results: List[Tuple[DocumentChunk, float]] = []

        for r in retrieved:
            if r.score >= min_score:
                # Find matching chunk
                chunk = self.vector_store.chunk_id_map.get(r.chunk_id)
                if not chunk:
                    chunk = DocumentChunk(
                        chunk_id=r.chunk_id,
                        document_id=r.document_id,
                        source_title=r.source_title,
                        section_or_page=r.section_or_page,
                        content=r.content,
                        word_count=len(r.content.split()),
                    )
                results.append((chunk, r.score))

        return results


class TFIDFRetriever:
    """
    A deterministic, lightweight, and completely local TF-IDF retriever.
    Implements TF-IDF scoring and cosine similarity without external dependencies.
    """

    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self.doc_count = len(chunks)
        self.vocab: set[str] = set()
        self.idf: dict[str, float] = {}
        self.tf: list[dict[str, float]] = []
        self.doc_norms: list[float] = []

        if self.doc_count > 0:
            self._build_index()

    def _tokenize(self, text: str) -> list[str]:
        # Simple word tokenization: lowercase, alphanumeric
        text = text.lower()
        return re.findall(r"\b[a-z0-9]+\b", text)

    def _build_index(self) -> None:
        doc_freq: dict[str, int] = defaultdict(int)

        # 1. Calculate TF and document frequency
        for chunk in self.chunks:
            tokens = self._tokenize(chunk.content)
            tf_map: dict[str, int] = defaultdict(int)
            for token in tokens:
                tf_map[token] += 1
                self.vocab.add(token)

            # Term Frequency (TF): normalize by max frequency in doc
            max_freq = max(tf_map.values()) if tf_map else 1
            normalized_tf = {
                token: freq / max_freq for token, freq in tf_map.items()
            }
            self.tf.append(normalized_tf)

            # Document Frequency (DF)
            for token in set(tokens):
                doc_freq[token] += 1

        # 2. Calculate IDF (smooth IDF)
        for token, df in doc_freq.items():
            self.idf[token] = math.log(self.doc_count / (1 + df)) + 1.0

        # 3. Precompute document vector norms for faster cosine similarity
        for i in range(self.doc_count):
            norm_sq = 0.0
            for token, tf_val in self.tf[i].items():
                val = tf_val * self.idf[token]
                norm_sq += val ** 2
            self.doc_norms.append(math.sqrt(norm_sq))

    def _get_vector(self, text: str) -> dict[str, float]:
        tokens = self._tokenize(text)
        tf_map: dict[str, int] = defaultdict(int)
        for token in tokens:
            tf_map[token] += 1

        max_freq = max(tf_map.values()) if tf_map else 1
        vector = {}
        for token, freq in tf_map.items():
            if token in self.idf:
                vector[token] = (freq / max_freq) * self.idf[token]
        return vector

    def retrieve(
        self, query: str, top_k: int = 5, min_score: float = 0.05
    ) -> list[tuple[DocumentChunk, float]]:
        if self.doc_count == 0:
            return []

        query_vec = self._get_vector(query)
        if not query_vec:
            return []

        # query norm
        query_norm = math.sqrt(sum(val ** 2 for val in query_vec.values()))
        if query_norm == 0:
            return []

        scores: list[tuple[DocumentChunk, float]] = []
        for i, chunk in enumerate(self.chunks):
            doc_norm = self.doc_norms[i]
            if doc_norm == 0:
                continue

            # Dot product
            dot_product = 0.0
            # Only iterate over query tokens since non-matching tokens have 0 product
            for token, q_val in query_vec.items():
                if token in self.tf[i]:
                    d_val = self.tf[i][token] * self.idf[token]
                    dot_product += q_val * d_val

            score = dot_product / (query_norm * doc_norm)

            if score >= min_score:
                scores.append((chunk, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
