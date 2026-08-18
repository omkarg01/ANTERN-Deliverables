"""M3 acceptance tests — multi-signal ranking, abstention, context budgeting."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cmis.context.builder import ContextBuilder
from cmis.context.service import ContextService
from cmis.models import (
    MemoryCreate,
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    RankedMemory,
    SensitivityLevel,
)
from cmis.ranking.ranker import DEFAULT_RELEVANCE_THRESHOLD, rank_memories
from cmis.storage.repository import MemoryRepository

pytestmark = pytest.mark.integration


def _seed_door_vs_hiking(repo: MemoryRepository) -> tuple[MemoryRecord, MemoryRecord]:
    door = repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="My office door code is 4455",
            memory_type=MemoryType.FACT,
            importance=0.9,
        )
    )
    hiking = repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I enjoy weekend hiking in the mountains",
            memory_type=MemoryType.PREFERENCE,
            importance=0.3,
        )
    )
    return door, hiking


def test_m3_t1_importance_ranking(context_service: ContextService) -> None:
    """D3 A-01: door code (importance=0.9) outranks hiking (importance=0.3)."""
    repo = context_service.retrieval.repository
    door, hiking = _seed_door_vs_hiking(repo)

    block = context_service.build_context(
        query="What is my office door code?",
        tenant_id="acme",
        user_id="alice",
    )

    assert block.abstention_reason is None
    assert len(block.memories) >= 1
    assert block.memories[0].memory.memory_id == door.memory_id
    assert block.memories[0].memory.memory_id != hiking.memory_id


def test_m3_t2_abstention_when_no_relevant_memories(context_service: ContextService) -> None:
    """D3 G-02: unrelated query abstains with reason when all ranks below threshold."""
    repo = context_service.retrieval.repository
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I like cooking pasta with garlic and olive oil",
            importance=0.1,
        )
    )
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="My cat is named Whiskers and sleeps on the couch",
            importance=0.1,
        )
    )

    block = context_service.build_context(
        query="quantum mechanics wave function collapse",
        tenant_id="acme",
        user_id="alice",
    )

    assert block.memories == []
    assert block.injected_count == 0
    assert block.abstention_reason is not None
    assert str(DEFAULT_RELEVANCE_THRESHOLD) in block.abstention_reason


def test_m3_t3_context_budgeting(context_service: ContextService) -> None:
    """D3 D-01: char budget keeps top-ranked memory and drops overflow."""
    repo = context_service.retrieval.repository
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="Door code 4455",
            importance=0.95,
        )
    )
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="Office door keypad backup code 8899",
            importance=0.5,
        )
    )
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="Building door access panel instructions note",
            importance=0.4,
        )
    )

    block = context_service.build_context(
        query="What is my office door code?",
        tenant_id="acme",
        user_id="alice",
        max_chars=60,
    )

    assert block.overflow_truncated is True
    assert block.injected_count == 1
    assert block.ranking_count >= 2
    assert "Door code 4455" in block.memories[0].memory.content
    assert block.dropped_count == block.ranking_count - block.injected_count


def test_m3_t4_threshold_excludes_low_similarity() -> None:
    """ADR-002: combined_rank below threshold is excluded from context."""
    now = datetime.now(UTC)
    low_memory = MemoryRecord(
        memory_id=uuid4(),
        tenant_id="acme",
        user_id="alice",
        content="Unrelated astronomy nebula constellation facts",
        memory_type=MemoryType.FACT,
        status=MemoryStatus.ACTIVE,
        importance=0.2,
        confidence=1.0,
        embedding_model="test",
        contains_pii=False,
        sensitivity_level=SensitivityLevel.INTERNAL,
        created_at=now,
        similarity=0.2,
    )
    high_memory = MemoryRecord(
        memory_id=uuid4(),
        tenant_id="acme",
        user_id="alice",
        content="My office door code is 4455",
        memory_type=MemoryType.FACT,
        status=MemoryStatus.ACTIVE,
        importance=0.9,
        confidence=1.0,
        embedding_model="test",
        contains_pii=False,
        sensitivity_level=SensitivityLevel.INTERNAL,
        created_at=now,
        similarity=0.8,
    )

    ranking = rank_memories([high_memory, low_memory], threshold=0.3, now=now)
    assert len(ranking.ranked) == 1
    assert ranking.ranked[0].similarity_score == 0.8
    assert ranking.dropped_by_threshold == 1

    block = ContextBuilder().build(
        ranking.ranked,
        max_tokens=2000,
        retrieval_count=2,
    )
    assert len(block.memories) == 1
    assert block.memories[0].similarity_score == 0.8


def test_m3_t5_observability_counts(context_service: ContextService) -> None:
    """ContextBlock exposes retrieval, ranking, and injection counts."""
    repo = context_service.retrieval.repository
    _seed_door_vs_hiking(repo)

    block = context_service.build_context(
        query="What is my office door code?",
        tenant_id="acme",
        user_id="alice",
        max_chars=200,
    )

    assert block.retrieval_count >= 2
    assert block.ranking_count >= 1
    assert block.injected_count >= 1
    assert block.dropped_count == block.ranking_count - block.injected_count
