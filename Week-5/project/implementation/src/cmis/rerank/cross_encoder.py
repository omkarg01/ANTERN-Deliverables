from __future__ import annotations

import re
from typing import Protocol

from cmis.config import get_reranker_kind
from cmis.models import MemoryRecord

_WORD_RE = re.compile(r"[a-z0-9]+")


class Reranker(Protocol):
    def rerank(
        self,
        *,
        query: str,
        candidates: list[MemoryRecord],
        top_k: int,
    ) -> list[MemoryRecord]: ...


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


class StubReranker:
    """Deterministic reranker for pytest — token overlap + dense similarity."""

    def rerank(
        self,
        *,
        query: str,
        candidates: list[MemoryRecord],
        top_k: int,
    ) -> list[MemoryRecord]:
        if not candidates:
            return []
        query_tokens = _tokenize(query)

        def score(memory: MemoryRecord) -> float:
            overlap = len(query_tokens & _tokenize(memory.content))
            base = memory.similarity if memory.similarity is not None else 0.0
            return base + 0.15 * overlap

        ranked = sorted(candidates, key=score, reverse=True)[:top_k]
        if not ranked:
            return []
        return [_with_similarity(item, min(1.0, score(item))) for item in ranked]


class CrossEncoderReranker:
    """Local cross-encoder reranker (I4-C production path)."""

    def __init__(self, model_id: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self._model_id = model_id
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_id)
        return self._model

    def rerank(
        self,
        *,
        query: str,
        candidates: list[MemoryRecord],
        top_k: int,
    ) -> list[MemoryRecord]:
        if not candidates:
            return []
        pairs = [(query, memory.content) for memory in candidates]
        raw_scores = self._load_model().predict(pairs)
        scored = list(zip(candidates, raw_scores, strict=True))
        scored.sort(key=lambda item: float(item[1]), reverse=True)
        top = scored[:top_k]
        return normalize_rerank_scores(top)


def normalize_rerank_scores(
    scored: list[tuple[MemoryRecord, float]],
) -> list[MemoryRecord]:
    """Map cross-encoder raw scores to [0, 1] similarity for rank_memories.

    Min-max over one candidate (or tied scores) collapses to 0 — preserve dense
    similarity from retrieval instead.
    """
    if not scored:
        return []

    if len(scored) == 1:
        memory, _raw = scored[0]
        dense = memory.similarity if memory.similarity is not None else 0.0
        return [_with_similarity(memory, dense)]

    max_score = float(scored[0][1])
    min_score = float(scored[-1][1])
    if max_score - min_score < 1e-6:
        return [
            _with_similarity(
                memory,
                memory.similarity if memory.similarity is not None else 0.0,
            )
            for memory, _raw in scored
        ]

    span = max_score - min_score
    return [
        _with_similarity(memory, (float(raw) - min_score) / span) for memory, raw in scored
    ]


class PassthroughReranker:
    """No reranking — return top-K by incoming similarity."""

    def rerank(
        self,
        *,
        query: str,
        candidates: list[MemoryRecord],
        top_k: int,
    ) -> list[MemoryRecord]:
        del query
        ordered = sorted(
            candidates,
            key=lambda memory: memory.similarity if memory.similarity is not None else 0.0,
            reverse=True,
        )
        return ordered[:top_k]


def _with_similarity(memory: MemoryRecord, similarity: float) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory.memory_id,
        tenant_id=memory.tenant_id,
        user_id=memory.user_id,
        content=memory.content,
        memory_type=memory.memory_type,
        status=memory.status,
        importance=memory.importance,
        confidence=memory.confidence,
        embedding_model=memory.embedding_model,
        contains_pii=memory.contains_pii,
        sensitivity_level=memory.sensitivity_level,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        valid_until=memory.valid_until,
        source_turn_id=memory.source_turn_id,
        created_by=memory.created_by,
        similarity=similarity,
    )


def create_reranker(kind: str | None = None) -> Reranker:
    selected = (kind or get_reranker_kind()).strip().lower()
    if selected in ("off", "none", "passthrough"):
        return PassthroughReranker()
    if selected == "local":
        return CrossEncoderReranker()
    return StubReranker()
