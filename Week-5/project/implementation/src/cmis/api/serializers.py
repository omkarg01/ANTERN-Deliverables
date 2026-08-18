from __future__ import annotations

from typing import Any
from uuid import UUID

from cmis.chat.models import ChatResponse
from cmis.formation.extraction import AdmissionDecision, AdmissionResult
from cmis.models import ContextBlock, MemoryRecord, RankedMemory


def _memory_to_dict(memory: MemoryRecord) -> dict[str, Any]:
    return {
        "memory_id": str(memory.memory_id),
        "tenant_id": memory.tenant_id,
        "user_id": memory.user_id,
        "content": memory.content,
        "memory_type": memory.memory_type.value,
        "status": memory.status.value,
        "importance": memory.importance,
        "confidence": memory.confidence,
        "contains_pii": memory.contains_pii,
        "sensitivity_level": memory.sensitivity_level.value,
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
        "similarity": memory.similarity,
    }


def admission_to_dict(result: AdmissionResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "decision": result.decision.value,
        "reason": result.reason,
    }
    if result.memory is not None:
        payload["memory"] = _memory_to_dict(result.memory)
    return payload


def ranked_memory_to_dict(item: RankedMemory) -> dict[str, Any]:
    return {
        "memory": _memory_to_dict(item.memory),
        "similarity_score": item.similarity_score,
        "recency_score": item.recency_score,
        "combined_rank": item.combined_rank,
        "estimated_tokens": item.estimated_tokens,
    }


def context_block_to_dict(block: ContextBlock) -> dict[str, Any]:
    return {
        "formatted_block": block.formatted_block,
        "total_tokens": block.total_tokens,
        "overflow_truncated": block.overflow_truncated,
        "abstention_reason": block.abstention_reason,
        "retrieval_count": block.retrieval_count,
        "ranking_count": block.ranking_count,
        "injected_count": block.injected_count,
        "dropped_count": block.dropped_count,
        "memories": [ranked_memory_to_dict(item) for item in block.memories],
    }


def memory_list_to_dict(memories: list[MemoryRecord]) -> dict[str, Any]:
    return {
        "count": len(memories),
        "memories": [_memory_to_dict(memory) for memory in memories],
    }


def erasure_to_dict(
    *,
    memory_id: UUID,
    events_erased: int,
    cascaded_memory_ids: tuple[UUID, ...],
) -> dict[str, Any]:
    return {
        "memory_id": str(memory_id),
        "events_erased": events_erased,
        "cascaded_memory_ids": [str(mid) for mid in cascaded_memory_ids],
    }


def chat_response_to_dict(response: ChatResponse) -> dict[str, Any]:
    return {
        "answer": response.answer,
        "memory_ids": [str(memory_id) for memory_id in response.memory_ids],
        "trace_id": response.trace_id,
        "model": response.model,
        "abstained": response.abstained,
        "abstention_reason": response.abstention_reason,
        "context": context_block_to_dict(response.context),
    }
