import hashlib
import logging
import re
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class LocalEmbeddingService:
    """
    Local-only semantic embedding generator using sentence-transformers.
    Runs 100% locally and air-gapped without external cloud API calls.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None
        self._initialized = False

    def _load_model(self) -> None:
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            # Load model locally
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded local SentenceTransformer model '{self.model_name}'.")
        except Exception as e:
            logger.warning(
                f"Could not load local sentence-transformers model '{self.model_name}' ({e}). "
                "Using local deterministic dense vector projection fallback."
            )
            self._model = None

        self._initialized = True

    def _fallback_deterministic_embed(self, text: str) -> np.ndarray:
        """
        Deterministic, subword n-gram dense vector projection fallback (384-dimensional)
        for air-gapped testing and offline execution.
        """
        vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
        if not tokens:
            vec[0] = 1.0
            return vec

        for word in tokens:
            # Hash full word
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:8], 16)
            vec[h % EMBEDDING_DIM] += 1.0

            # Hash prefixes (stemming simulation: 3-char, 4-char, 5-char)
            if len(word) >= 4:
                prefix3 = word[:3]
                h3 = int(hashlib.md5(prefix3.encode("utf-8")).hexdigest()[:8], 16)
                vec[h3 % EMBEDDING_DIM] += 0.8

                prefix4 = word[:4]
                h4 = int(hashlib.md5(prefix4.encode("utf-8")).hexdigest()[:8], 16)
                vec[h4 % EMBEDDING_DIM] += 0.6

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0
        return vec

    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode a list of text strings into normalized 2D numpy array of embeddings (N x 384).
        """
        if not texts:
            return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

        self._load_model()

        if self._model is not None:
            try:
                embeddings = self._model.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return np.asarray(embeddings, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Error during SentenceTransformer encoding: {e}. Falling back to deterministic projection.")

        # Fallback path
        vectors = [self._fallback_deterministic_embed(t) for t in texts]
        return np.array(vectors, dtype=np.float32)
