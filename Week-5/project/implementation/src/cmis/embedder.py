from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Protocol

from cmis.config import (
    BGE_MODEL_ID,
    BGE_QUERY_PREFIX,
    DETERMINISTIC_EMBEDDING_MODEL,
    EMBEDDING_DIM,
)

_WORD_RE = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    @property
    def model_name(self) -> str: ...

    def embed(self, text: str) -> list[float]: ...


class QueryEmbedder(Embedder, Protocol):
    def embed_query(self, query: str) -> list[float]: ...


class DeterministicEmbedder:
    """Word-hash embedder for reproducible tests without external API calls."""

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self._dim = dim

    @property
    def model_name(self) -> str:
        return DETERMINISTIC_EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        normalized = text.strip().lower()
        tokens = _WORD_RE.findall(normalized)
        vec = [0.0] * self._dim
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            for i in range(4):
                idx = int.from_bytes(digest[i * 2 : i * 2 + 2], "big") % self._dim
                vec[idx] += 1.0
        if not tokens:
            digest = hashlib.sha256(normalized.encode()).digest()
            for i in range(self._dim):
                vec[i] = (int.from_bytes(digest[i % 28 : i % 28 + 4], "big") / 2**32) * 2 - 1
        return _l2_normalize(vec)


class BGEEmbedder:
    """Production retrieval embedder (ADR-007 / I1)."""

    def __init__(self, model_id: str = BGE_MODEL_ID) -> None:
        self._model_id = model_id
        self._model = None

    @property
    def model_name(self) -> str:
        return self._model_id

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_id)
        return self._model

    def embed(self, text: str) -> list[float]:
        """Embed a stored memory document (no query prefix)."""
        vector = self._load_model().encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a search query with BGE retrieval prefix."""
        prefixed = f"{BGE_QUERY_PREFIX}{query}"
        vector = self._load_model().encode(prefixed, normalize_embeddings=True)
        return vector.tolist()


def create_embedder(kind: str | None = None) -> Embedder:
    """Factory: deterministic for tests; bge for API/runtime when CMIS_EMBEDDER=bge."""
    selected = (kind or os.environ.get("CMIS_EMBEDDER", "deterministic")).strip().lower()
    if selected == "bge":
        return BGEEmbedder()
    return DeterministicEmbedder()


def embed_query(embedder: Embedder, query: str) -> list[float]:
    """Encode a retrieval query, using embed_query when the embedder supports it."""
    embed_query_fn = getattr(embedder, "embed_query", None)
    if callable(embed_query_fn):
        return embed_query_fn(query)
    return embedder.embed(query)


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def cosine_similarity(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    if len(a) != len(b) or len(a) == 0:
        raise ValueError("vectors must be same non-zero length")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
