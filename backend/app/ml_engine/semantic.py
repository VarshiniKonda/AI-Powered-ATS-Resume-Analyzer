"""Lazy Sentence Transformer semantic similarity with explicit load failures."""

import logging
import re
from functools import lru_cache
from threading import Lock
from typing import Any

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)
_model_lock = Lock()


class SemanticModelUnavailable(RuntimeError):
    """The configured semantic model could not be loaded."""


@lru_cache(maxsize=1)
def _load_model() -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SemanticModelUnavailable(
            "Install the backend ML dependencies to enable semantic matching."
        ) from exc
    try:
        with _model_lock:
            return SentenceTransformer(settings.semantic_model_name, device="cpu")
    except Exception as exc:
        logger.error("Semantic model load failed: %s", type(exc).__name__)
        raise SemanticModelUnavailable(
            "The semantic model is unavailable. Retry after model access is restored."
        ) from exc


def _chunks(text: str, max_words: int = 180, max_chunks: int = 40) -> list[str]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    chunks = [" ".join(words[index : index + max_words]) for index in range(0, len(words), max_words)]
    return chunks[:max_chunks]


def semantic_similarity(first_text: str, second_text: str) -> float:
    """Return a normalized, best-aligned chunk similarity from 0 to 1."""
    first_chunks = _chunks(first_text)
    second_chunks = _chunks(second_text)
    if not first_chunks or not second_chunks:
        return 0.0
    model = _load_model()
    first_embeddings = model.encode(
        first_chunks, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
    )
    second_embeddings = model.encode(
        second_chunks, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
    )
    similarities = np.asarray(first_embeddings) @ np.asarray(second_embeddings).T
    best_for_first = similarities.max(axis=1)
    top_values = np.sort(best_for_first)[-min(3, len(best_for_first)) :]
    return float(np.clip(np.mean(top_values), 0.0, 1.0))