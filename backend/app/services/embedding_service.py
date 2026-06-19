"""
Bower Ag CowCare Tool — Embedding Service
Sprint 4: Shared embedding generation for RAG pipeline.

Provides a singleton fastembed model for generating embeddings.
Used by both embed_documents.py (batch) and rag.py (query-time).

Model: BAAI/bge-small-en-v1.5 (384 dimensions)
Zero-padded to 1536 to match the document_chunks.embedding vector(1536) column.
"""

import threading
from typing import Optional

from fastembed import TextEmbedding

# ── Constants ────────────────────────────────────────────────────
MODEL_NAME = "BAAI/bge-small-en-v1.5"
NATIVE_DIM = 384
TARGET_DIM = 1536

# ── Singleton Model ──────────────────────────────────────────────
_model: Optional[TextEmbedding] = None
_lock = threading.Lock()


def _get_model() -> TextEmbedding:
    """Lazy-load the embedding model (thread-safe singleton)."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


def pad_embedding(embedding: list[float], target_dim: int = TARGET_DIM) -> list[float]:
    """
    Zero-pad an embedding to the target dimension.

    Cosine similarity is preserved under zero-padding:
      cos(a_padded, b_padded) == cos(a, b)
    because zero dimensions contribute 0 to both dot product and norms.
    """
    if len(embedding) >= target_dim:
        return embedding[:target_dim]
    return embedding + [0.0] * (target_dim - len(embedding))


def get_query_embedding(text: str) -> list[float]:
    """
    Generate a zero-padded embedding for a query string.
    Returns a list of TARGET_DIM floats ready for pgvector comparison.
    """
    model = _get_model()
    embeddings = list(model.embed([text]))
    raw = embeddings[0].tolist()
    return pad_embedding(raw)


def get_batch_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate zero-padded embeddings for multiple texts.
    Returns a list of TARGET_DIM-length float lists.
    """
    model = _get_model()
    embeddings = list(model.embed(texts))
    return [pad_embedding(emb.tolist()) for emb in embeddings]
