import logging
from typing import Dict, List, Optional

import numpy as np

from src.rag.embeddings import EMBEDDING_DIM, LocalEmbeddingService
from src.schemas.rag import DocumentChunk, RetrievedChunk

logger = logging.getLogger(__name__)


class LocalVectorStore:
    """
    Local Vector Database using FAISS (IndexFlatIP for cosine similarity)
    with local NumPy fallback for pure air-gapped environments.
    """

    def __init__(
        self,
        embedding_service: Optional[LocalEmbeddingService] = None,
        dimension: int = EMBEDDING_DIM,
    ):
        self.dimension = dimension
        self.embedding_service = embedding_service or LocalEmbeddingService()
        self.chunks: List[DocumentChunk] = []
        self.chunk_id_map: Dict[str, DocumentChunk] = {}
        self._embeddings: Optional[np.ndarray] = None
        self._faiss_index = None
        self._init_index()

    def _init_index(self) -> None:
        try:
            import faiss  # type: ignore

            self._faiss_index = faiss.IndexFlatIP(self.dimension)
            logger.info("Initialized FAISS IndexFlatIP vector database.")
        except Exception as e:
            logger.warning(f"Could not initialize FAISS index ({e}). Using NumPy cosine similarity store.")
            self._faiss_index = None

    def add_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: Optional[np.ndarray] = None,
    ) -> None:
        """Add document chunks and their semantic vectors to the local vector store."""
        if not chunks:
            return

        if embeddings is None:
            texts = [f"{c.source_title} {c.section_or_page}\n{c.content}" for c in chunks]
            embeddings = self.embedding_service.encode(texts)

        # Ensure embeddings are normalized float32
        embeddings = np.asarray(embeddings, dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normed_embeddings = embeddings / norms

        if self._faiss_index is not None:
            self._faiss_index.add(normed_embeddings)

        if self._embeddings is None or self._embeddings.size == 0:
            self._embeddings = normed_embeddings
        else:
            self._embeddings = np.vstack([self._embeddings, normed_embeddings])

        for c in chunks:
            self.chunks.append(c)
            self.chunk_id_map[c.chunk_id] = c

    def search(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        """
        Perform semantic cosine-similarity search for the query against all indexed chunks.
        """
        if not self.chunks or self._embeddings is None or len(self.chunks) == 0:
            return []

        q_vec = self.embedding_service.encode([query])
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        top_k = min(top_k, len(self.chunks))

        if self._faiss_index is not None:
            try:
                distances, indices = self._faiss_index.search(q_vec, top_k)
                results: List[RetrievedChunk] = []
                for score, idx in zip(distances[0], indices[0]):
                    if idx >= 0 and idx < len(self.chunks):
                        chunk = self.chunks[idx]
                        results.append(
                            RetrievedChunk(
                                chunk_id=chunk.chunk_id,
                                document_id=chunk.document_id,
                                source_title=chunk.source_title,
                                section_or_page=chunk.section_or_page,
                                content=chunk.content,
                                score=float(score),
                            )
                        )
                return results
            except Exception as e:
                logger.warning(f"FAISS search failed ({e}). Falling back to NumPy search.")

        # NumPy Cosine Similarity fallback
        scores = np.dot(self._embeddings, q_vec.T).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    source_title=chunk.source_title,
                    section_or_page=chunk.section_or_page,
                    content=chunk.content,
                    score=float(scores[idx]),
                )
            )

        return results

    def clear(self) -> None:
        """Reset the vector index."""
        self.chunks.clear()
        self.chunk_id_map.clear()
        self._embeddings = None
        self._init_index()
