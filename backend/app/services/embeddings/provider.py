"""Embedding providers.

The :class:`EmbeddingProvider` interface is the only contract the rest of the
application depends on. The concrete ``SentenceTransformer`` implementation is
loaded once and reused; a deterministic hash-based provider is provided for
tests and offline development so the pipeline can run without downloading a
model or a GPU.
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from typing import List

import numpy as np

from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
from app.core.text import content_tokens

logger = get_logger("sourcelens.embeddings")


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        ...

    @property
    @abstractmethod
    def dim(self) -> int:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    def is_loaded(self) -> bool:
        return True


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model_name: str,
        *,
        normalize: bool = True,
        batch_size: int = 32,
    ) -> None:
        self._model_name = model_name
        self._normalize = normalize
        self._batch_size = batch_size
        self._dim = 0
        self._model = None
        self._load()

    def _load(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("embedding.load_start", extra={"sl_model": self._model_name})
            self._model = SentenceTransformer(self._model_name)
            self._dim = int(self._model.get_sentence_embedding_dimension())
            logger.info("embedding.loaded", extra={"sl_dim": self._dim})
        except Exception as exc:  # noqa: BLE001 - surface as a clean error
            raise EmbeddingError(
                f"Failed to load embedding model '{self._model_name}': {exc}"
            ) from exc

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self._model is None:
            raise EmbeddingError("Embedding model is not loaded")
        try:
            batches: List[List[float]] = []
            for start in range(0, len(texts), self._batch_size):
                batch = texts[start : start + self._batch_size]
                vecs = self._model.encode(
                    batch,
                    normalize_embeddings=self._normalize,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                batches.extend(vecs.tolist())
            return batches
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(f"Embedding generation failed: {exc}") from exc

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name


class DeterministicHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic, dependency-free embeddings for tests/offline use.

    Similarity is lexical: texts sharing content words have a higher cosine
    similarity. This is NOT semantically meaningful, but it is stable and lets
    the retrieval / grounding logic be exercised without a model download.
    """

    def __init__(self, dim: int = 512, normalize: bool = True) -> None:
        self._dim = dim
        self._normalize = normalize
        self._model_name = "deterministic-hash-v1"

    def _vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self._dim, dtype=np.float64)
        tokens = list(content_tokens(text))
        if not tokens:
            return vec
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            vec[idx] += 1.0
        if self._normalize:
            norm = math.sqrt(float(np.dot(vec, vec)))
            if norm > 0:
                vec = vec / norm
        return vec

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._vector(t).tolist() for t in texts]

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name


def build_embedding_provider(
    model_name: str, *, dim: int = 384, normalize: bool = True, batch_size: int = 32
) -> EmbeddingProvider:
    """Factory used by the container. Swap this to replace the embedding backend."""
    return SentenceTransformerEmbeddingProvider(
        model_name, normalize=normalize, batch_size=batch_size
    )
