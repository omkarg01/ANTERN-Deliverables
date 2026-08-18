from __future__ import annotations

import psycopg

from cmis.config import get_max_inject_count, get_relevance_threshold
from cmis.context.builder import ContextBuilder
from cmis.embedder import Embedder
from cmis.episodic.resolution import resolve_memories_for_query
from cmis.models import ContextBlock
from cmis.ranking.ranker import rank_memories
from cmis.retrieval.service import RetrievalService


class ContextService:
    """End-to-end retrieval → ranking → context construction (M3)."""

    DEFAULT_RETRIEVAL_POOL = 50

    def __init__(
        self,
        conn: psycopg.Connection,
        embedder: Embedder,
    ) -> None:
        self._retrieval = RetrievalService(conn, embedder)
        self._builder = ContextBuilder()

    @property
    def retrieval(self) -> RetrievalService:
        return self._retrieval

    def build_context(
        self,
        *,
        query: str,
        tenant_id: str,
        user_id: str,
        max_tokens: int = 2000,
        max_chars: int | None = None,
        relevance_threshold: float | None = None,
        retrieval_pool: int = DEFAULT_RETRIEVAL_POOL,
    ) -> ContextBlock:
        threshold = (
            relevance_threshold if relevance_threshold is not None else get_relevance_threshold()
        )
        retrieval = self._retrieval.retrieve(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            top_k=retrieval_pool,
        )
        memories = resolve_memories_for_query(
            retrieval.memories,
            self._retrieval.repository,
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
        )
        retrieval_count = retrieval.candidate_count
        ranking = rank_memories(
            memories,
            threshold=threshold,
            max_inject=get_max_inject_count(),
        )
        return self._builder.build(
            ranking.ranked,
            max_tokens=max_tokens,
            max_chars=max_chars,
            query=query,
            retrieval_count=retrieval_count,
            abstention_reason=ranking.abstention_reason,
        )
