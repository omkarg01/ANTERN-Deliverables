from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from cmis.episodic.intent import QueryIntent, classify_query_intent
from cmis.episodic.semantics import (
    infer_query_state_keys,
    is_episodic_event,
    is_preference_state,
    valid_temporal_relationship,
)
from cmis.models import MemoryRecord, MemoryType
from cmis.storage.repository import MemoryRepository


def resolve_memories_for_query(
    candidates: list[MemoryRecord],
    repository: MemoryRepository,
    *,
    tenant_id: str,
    user_id: str,
    query: str,
) -> list[MemoryRecord]:
    """Apply intent-specific episodic resolution — no blind chain walking."""
    if not candidates:
        return candidates

    intent = classify_query_intent(query)
    if intent == QueryIntent.CURRENT_STATE:
        return _resolve_current_state(
            candidates,
            repository,
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
        )
    if intent == QueryIntent.HISTORICAL:
        return _expand_validated_predecessors(
            candidates,
            repository,
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
        )
    return candidates


def _resolve_current_state(
    candidates: list[MemoryRecord],
    repository: MemoryRepository,
    *,
    tenant_id: str,
    user_id: str,
    query: str,
) -> list[MemoryRecord]:
    state_keys = infer_query_state_keys(query)
    canonical = repository.get_canonical_states(
        tenant_id=tenant_id,
        user_id=user_id,
        state_keys=state_keys or None,
    )
    if not canonical and state_keys:
        canonical = repository.get_canonical_states(
            tenant_id=tenant_id,
            user_id=user_id,
            state_keys=None,
        )

    if canonical:
        seen: set[UUID] = set()
        resolved: list[MemoryRecord] = []
        anchor_similarity = max(
            (memory.similarity for memory in candidates if memory.similarity is not None),
            default=0.9,
        )
        for memory in canonical:
            if memory.memory_id in seen:
                continue
            similarity = anchor_similarity
            for candidate in candidates:
                if candidate.memory_id == memory.memory_id and candidate.similarity is not None:
                    similarity = max(candidate.similarity, anchor_similarity)
                    break
            resolved.append(replace(memory, similarity=similarity))
            seen.add(memory.memory_id)
        return resolved

    filtered = [
        memory
        for memory in candidates
        if not is_episodic_event(memory.content)
        and memory.memory_type in (MemoryType.PREFERENCE, MemoryType.CONSTRAINT)
    ]
    return filtered or candidates


def _expand_validated_predecessors(
    candidates: list[MemoryRecord],
    repository: MemoryRepository,
    *,
    tenant_id: str,
    user_id: str,
    query: str,
) -> list[MemoryRecord]:
    preference_history = "prefer" in query.strip().lower()
    if preference_history:
        candidates = [
            memory
            for memory in candidates
            if not is_episodic_event(memory.content)
            or is_preference_state(memory.content)
        ]

    seen: set[UUID] = {memory.memory_id for memory in candidates}
    expanded = list(candidates)
    predecessor_ids: set[UUID] = set()
    anchor_similarity = max(
        (memory.similarity for memory in candidates if memory.similarity is not None),
        default=0.0,
    )

    for memory in candidates:
        predecessors = repository.get_linked_predecessors(
            memory.memory_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        for predecessor in predecessors:
            if not valid_temporal_relationship(
                predecessor.content,
                memory.content,
                prior_type=predecessor.memory_type,
                later_type=memory.memory_type,
            ):
                continue
            predecessor_ids.add(predecessor.memory_id)
            if predecessor.memory_id not in seen:
                expanded.append(replace(predecessor, similarity=anchor_similarity))
                seen.add(predecessor.memory_id)

    if not predecessor_ids:
        return expanded

    boosted: list[MemoryRecord] = []
    for memory in expanded:
        if memory.memory_id not in predecessor_ids:
            boosted.append(memory)
            continue
        current = memory.similarity if memory.similarity is not None else 0.0
        boosted.append(replace(memory, similarity=max(current, anchor_similarity)))
    return boosted
