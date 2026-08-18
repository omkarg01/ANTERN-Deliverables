from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from cmis.cache.keys import build_key
from cmis.models import ContextBlock, MemoryRecord, RankedMemory

if TYPE_CHECKING:
    from redis import Redis


@dataclass(frozen=True)
class CachedContextSnapshot:
    formatted_block: str
    total_tokens: int
    overflow_truncated: bool
    abstention_reason: str | None
    retrieval_count: int
    ranking_count: int
    injected_count: int
    dropped_count: int
    memories: tuple[dict, ...]


class ContextCache:
    """Optional TTL cache for hot context builds (tenant-scoped keys)."""

    def __init__(
        self,
        client: Redis,
        *,
        ttl_seconds: int = 300,
    ) -> None:
        self._client = client
        self._ttl = ttl_seconds

    @staticmethod
    def _query_hash(*, query: str, max_tokens: int) -> str:
        payload = f"{query.strip().lower()}|{max_tokens}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def _key(self, *, tenant_id: str, user_id: str, query: str, max_tokens: int) -> str:
        digest = self._query_hash(query=query, max_tokens=max_tokens)
        return build_key(tenant_id, user_id, f"ctx:{digest}")

    @staticmethod
    def _serialize(block: ContextBlock) -> str:
        snapshot = CachedContextSnapshot(
            formatted_block=block.formatted_block,
            total_tokens=block.total_tokens,
            overflow_truncated=block.overflow_truncated,
            abstention_reason=block.abstention_reason,
            retrieval_count=block.retrieval_count,
            ranking_count=block.ranking_count,
            injected_count=block.injected_count,
            dropped_count=block.dropped_count,
            memories=tuple(
                {
                    "memory_id": str(item.memory.memory_id),
                    "tenant_id": item.memory.tenant_id,
                    "user_id": item.memory.user_id,
                    "content": item.memory.content,
                    "memory_type": item.memory.memory_type.value,
                    "status": item.memory.status.value,
                    "importance": item.memory.importance,
                    "confidence": item.memory.confidence,
                    "embedding_model": item.memory.embedding_model,
                    "contains_pii": item.memory.contains_pii,
                    "sensitivity_level": item.memory.sensitivity_level.value,
                    "created_at": item.memory.created_at.isoformat(),
                    "updated_at": (
                        item.memory.updated_at.isoformat() if item.memory.updated_at else None
                    ),
                    "valid_until": (
                        item.memory.valid_until.isoformat() if item.memory.valid_until else None
                    ),
                    "source_turn_id": (
                        str(item.memory.source_turn_id) if item.memory.source_turn_id else None
                    ),
                    "created_by": item.memory.created_by.value,
                    "similarity": item.memory.similarity,
                    "similarity_score": item.similarity_score,
                    "recency_score": item.recency_score,
                    "combined_rank": item.combined_rank,
                }
                for item in block.memories
            ),
        )
        return json.dumps(snapshot.__dict__)

    @staticmethod
    def _deserialize(payload: str) -> ContextBlock:
        from datetime import datetime
        from uuid import UUID

        from cmis.models import ActorType, MemoryStatus, MemoryType, SensitivityLevel

        raw = json.loads(payload)
        memories: list[RankedMemory] = []
        for item in raw["memories"]:
            record = MemoryRecord(
                memory_id=UUID(item["memory_id"]),
                tenant_id=item["tenant_id"],
                user_id=item["user_id"],
                content=item["content"],
                memory_type=MemoryType(item["memory_type"]),
                status=MemoryStatus(item["status"]),
                importance=item["importance"],
                confidence=item["confidence"],
                embedding_model=item["embedding_model"],
                contains_pii=item["contains_pii"],
                sensitivity_level=SensitivityLevel(item["sensitivity_level"]),
                created_at=datetime.fromisoformat(item["created_at"]),
                updated_at=(
                    datetime.fromisoformat(item["updated_at"]) if item["updated_at"] else None
                ),
                valid_until=(
                    datetime.fromisoformat(item["valid_until"]) if item["valid_until"] else None
                ),
                source_turn_id=(
                    UUID(item["source_turn_id"]) if item["source_turn_id"] else None
                ),
                created_by=ActorType(item["created_by"]),
                similarity=item["similarity"],
            )
            memories.append(
                RankedMemory(
                    memory=record,
                    similarity_score=item["similarity_score"],
                    recency_score=item["recency_score"],
                    combined_rank=item["combined_rank"],
                )
            )
        return ContextBlock(
            memories=memories,
            formatted_block=raw["formatted_block"],
            total_tokens=raw["total_tokens"],
            overflow_truncated=raw["overflow_truncated"],
            abstention_reason=raw["abstention_reason"],
            retrieval_count=raw["retrieval_count"],
            ranking_count=raw["ranking_count"],
            injected_count=raw["injected_count"],
            dropped_count=raw["dropped_count"],
        )

    def get(
        self,
        *,
        tenant_id: str,
        user_id: str,
        query: str,
        max_tokens: int,
    ) -> ContextBlock | None:
        key = self._key(
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            max_tokens=max_tokens,
        )
        payload = self._client.get(key)
        if payload is None:
            return None
        return self._deserialize(payload)

    def set(
        self,
        *,
        tenant_id: str,
        user_id: str,
        query: str,
        max_tokens: int,
        block: ContextBlock,
    ) -> None:
        key = self._key(
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            max_tokens=max_tokens,
        )
        self._client.setex(key, self._ttl, self._serialize(block))


class CacheMetrics(Protocol):
    def inc(self, metric: str, amount: int = 1) -> None: ...


def cache_get(
    cache: ContextCache | None,
    metrics: CacheMetrics | None,
    *,
    tenant_id: str,
    user_id: str,
    query: str,
    max_tokens: int,
) -> ContextBlock | None:
    if cache is None:
        return None
    block = cache.get(
        tenant_id=tenant_id,
        user_id=user_id,
        query=query,
        max_tokens=max_tokens,
    )
    if block is not None and metrics is not None:
        metrics.inc("cache_hits_total")
    elif metrics is not None:
        metrics.inc("cache_misses_total")
    return block


def cache_set(
    cache: ContextCache | None,
    *,
    tenant_id: str,
    user_id: str,
    query: str,
    max_tokens: int,
    block: ContextBlock,
) -> None:
    if cache is None:
        return
    cache.set(
        tenant_id=tenant_id,
        user_id=user_id,
        query=query,
        max_tokens=max_tokens,
        block=block,
    )
