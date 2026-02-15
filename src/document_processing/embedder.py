"""
Embedding generation using sentence-transformers.

Uses a lightweight model (all-MiniLM-L6-v2, 384 dims) that runs on CPU.
Embeddings are used for vector search in both ChromaDB and Neo4j.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)

# Lazy-loaded model to avoid import overhead when not needed
_model = None
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Loaded embedding model: %s (%d dims)", MODEL_NAME, EMBEDDING_DIM)
    return _model


class Embedder:
    """Generate vector embeddings for text chunks."""

    @staticmethod
    def embed(texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Returns a list of float vectors (384 dimensions each).
        """
        model = _get_model()
        embeddings = model.encode(texts, show_progress_bar=len(texts) > 10)
        return [e.tolist() for e in embeddings]

    @staticmethod
    def embed_single(text: str) -> List[float]:
        """Generate embedding for a single text."""
        return Embedder.embed([text])[0]
