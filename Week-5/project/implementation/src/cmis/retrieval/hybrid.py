from __future__ import annotations

from uuid import UUID

from cmis.models import MemoryRecord


def reciprocal_rank_fusion(
    ranked_lists: list[list[MemoryRecord]],
    *,
    k: int = 60,
) -> list[MemoryRecord]:
    """Merge ranked candidate lists with RRF; preserve dense similarity when available."""
    scores: dict[UUID, float] = {}
    records: dict[UUID, MemoryRecord] = {}

    for list_index, ranked in enumerate(ranked_lists):
        for rank, memory in enumerate(ranked, start=1):
            scores[memory.memory_id] = scores.get(memory.memory_id, 0.0) + 1.0 / (k + rank)
            existing = records.get(memory.memory_id)
            if existing is None:
                records[memory.memory_id] = memory
                continue
            # Prefer similarity from dense list (index 0), then sparse.
            if list_index == 0 and memory.similarity is not None:
                records[memory.memory_id] = memory
            elif (
                existing.similarity is None
                and memory.similarity is not None
            ):
                records[memory.memory_id] = memory

    ordered_ids = sorted(scores.keys(), key=lambda mid: scores[mid], reverse=True)
    merged: list[MemoryRecord] = []
    for memory_id in ordered_ids:
        memory = records[memory_id]
        merged.append(
            MemoryRecord(
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
                similarity=memory.similarity,
            )
        )
    return merged
