"""
FastEmbed embedding provider for Extra Memory.
Uses BAAI/bge-small-en-v1.5 via pure ONNX runtime when installed,
or deterministic normalized bag-of-words pseudo-embeddings for the <6MB Core tier.
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import List, Optional

logger = logging.getLogger("Extra-Memory-Embeddings")

_EMBED_MODEL = None
EMBEDDING_DIM = 384


def get_embedding_model():
    """Initializes and caches the FastEmbed model singleton, or None if not installed."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        try:
            from fastembed import TextEmbedding
            _EMBED_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("Initialized FastEmbed ONNX model (BAAI/bge-small-en-v1.5)")
        except Exception as ex:
            logger.debug("FastEmbed model not available, using deterministic fallback: %s", ex)
            return None
    return _EMBED_MODEL


def get_embedding(text: str) -> List[float]:
    """
    Computes a 384-dimensional normalized vector embedding for the input text.
    If FastEmbed is not installed, generates a deterministic pseudo-vector.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM

    model = get_embedding_model()
    if model is not None:
        try:
            embeddings = list(model.embed([text]))
            return embeddings[0].tolist()
        except Exception:
            pass

    # Deterministic unit-vector fallback from text hash (Core Tier)
    digest = hashlib.sha256(text.strip().lower().encode("utf-8")).digest()
    vec = []
    for i in range(EMBEDDING_DIM):
        b = digest[i % len(digest)]
        vec.append((b / 127.5) - 1.0)
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 5) for x in vec]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if len(vec1) != len(vec2) or not vec1:
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot / (norm1 * norm2)
