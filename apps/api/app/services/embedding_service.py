"""
Reusable Embedding Service for Acme Enterprise Assistant.
Generates 384-dimensional dense vectors using the approved sentence-transformers/all-MiniLM-L6-v2 model.
Implements singleton caching to prevent redundant model instantiations.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_EMBEDDER_INSTANCE: Optional["EmbeddingService"] = None


class EmbeddingServiceError(Exception):
    """Raised when embedding model loading or vector computation fails."""
    pass


class EmbeddingService:
    """
    Singleton embedding service wrapping sentence-transformers/all-MiniLM-L6-v2
    with graceful ONNX / ChromaDB fallback.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._onnx_ef = None
        self._init_model()

    def _init_model(self) -> None:
        """Initializes the underlying embedding model once using local ONNX or SentenceTransformer."""
        # Try local ONNXMiniLM_L6_V2 first (instant, deterministic, cached locally without network dependencies)
        try:
            import chromadb.utils.embedding_functions as ef
            self._onnx_ef = ef.ONNXMiniLM_L6_V2()
            logger.info("Initialized local ONNXMiniLM_L6_V2 engine for %s.", self.model_name)
            return
        except Exception as e:
            logger.info("Local ONNXMiniLM_L6_V2 fallback unavailable: %s", e)

        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Initializing SentenceTransformer with model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            return
        except Exception as e:
            raise EmbeddingServiceError(
                f"Failed to initialize embedding model '{self.model_name}': {e}"
            ) from e

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector embeddings for a list of text strings.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of 384-dimensional float vectors.
        """
        if not texts:
            return []

        try:
            if self._model is not None:
                embeddings = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings.tolist()
            elif self._onnx_ef is not None:
                return self._onnx_ef(texts)
            else:
                raise EmbeddingServiceError("No valid embedding backend is initialized.")
        except Exception as err:
            raise EmbeddingServiceError(f"Embedding computation failed: {err}") from err

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding for a single query string."""
        results = self.embed_texts([query])
        if not results:
            raise EmbeddingServiceError("Empty embedding generated for query.")
        return results[0]


def get_embedding_service(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> EmbeddingService:
    """Returns the process-wide cached singleton EmbeddingService instance."""
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None:
        _EMBEDDER_INSTANCE = EmbeddingService(model_name=model_name)
    return _EMBEDDER_INSTANCE
