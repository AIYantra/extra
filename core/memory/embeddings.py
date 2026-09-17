"""
FastEmbed embedding provider for Extra Memory.
Uses BAAI/bge-small-en-v1.5 via pure ONNX runtime for lightweight, sub-3ms vector generation.
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional

logger = logging.getLogger("Extra-Memory-Embeddings")

_EMBED_MODEL = None
EMBEDDING_DIM = 384


def get_embedding_model():
    """Initializes and caches the FastEmbed model singleton."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        try:
            from fastembed import TextEmbedding
            _EMBED_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("Initialized FastEmbed ONNX model (BAAI/bge-small-en-v1.5)")
        except Exception as ex:
            logger.error("Failed to load FastEmbed model: %s", ex)
            raise
    return _EMBED_MODEL


def get_embedding(text: str) -> List[float]:
    """
    Computes a 384-dimensional normalized vector embedding for the input text.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM

    model = get_embedding_model()
    embeddings = list(model.embed([text]))
    vec = embeddings[0].tolist()
    return vec


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if len(vec1) != len(vec2) or not vec1:
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a, b in zip(vec1, vec1)))
    norm2 = math.sqrt(sum(b * b for a, b in zip(vec2, vec2)))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot / (norm1 * norm2)
