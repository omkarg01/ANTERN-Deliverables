from __future__ import annotations

import psycopg

from cmis.config import (
    get_rerank_top_k,
    get_retrieval_pool,
    get_rrf_k,
    is_hybrid_retrieval_enabled,
)
from cmis.embedder import Embedder, embed_query
from cmis.models import MemoryRecord, MemoryStatus, RetrievalResult, SensitivityLevel
from cmis.privacy.pii import allows_confidential_retrieval
from cmis.rerank.cross_encoder import Reranker, create_reranker
from cmis.retrieval.hybrid import reciprocal_rank_fusion
from cmis.retrieval.query_processor import process_query
from cmis.storage.repository import MemoryRepository


class RetrievalService:
    """Tenant-scoped hybrid retrieval with privacy filters (M1–M2, I4)."""

    def __init__(
        self,
        conn: psycopg.Connection,
        embedder: Embedder,
        reranker: Reranker | None = None,
    ) -> None:
        self._repo = MemoryRepository(conn, embedder)
        self._embedder = embedder
        self._reranker = reranker or create_reranker()

    @property
    def repository(self) -> MemoryRepository:
        return self._repo

    def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        user_id: str,
        top_k: int | None = None,
    ) -> RetrievalResult:
        processed = process_query(query)
        pool_size = top_k if top_k is not None else get_retrieval_pool()
        rerank_k = min(get_rerank_top_k(), pool_size)

        query_embedding = embed_query(self._embedder, processed.search_text)
        dense_candidates = self._repo.search_by_embedding(
            tenant_id=tenant_id,
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=pool_size,
        )

        if is_hybrid_retrieval_enabled():
            sparse_candidates = self._repo.search_by_fts(
                tenant_id=tenant_id,
                user_id=user_id,
                query=processed.search_text,
                top_k=pool_size,
            )
            if sparse_candidates:
                merged = reciprocal_rank_fusion(
                    [dense_candidates, sparse_candidates],
                    k=get_rrf_k(),
                )[:pool_size]
            elif dense_candidates:
                merged = dense_candidates[:pool_size]
            else:
                merged = []
        else:
            merged = dense_candidates[:pool_size]

        reranked = self._reranker.rerank(
            query=processed.search_text,
            candidates=merged,
            top_k=rerank_k,
        )
        filtered = self._apply_privacy_filter(reranked, query)
        return RetrievalResult(
            memories=filtered,
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            candidate_count=len(filtered),
        )

    @staticmethod
    def _apply_privacy_filter(
        candidates: list[MemoryRecord],
        query: str,
    ) -> list[MemoryRecord]:
        if allows_confidential_retrieval(query):
            return candidates
        return [
            memory
            for memory in candidates
            if memory.sensitivity_level != SensitivityLevel.CONFIDENTIAL
        ]
