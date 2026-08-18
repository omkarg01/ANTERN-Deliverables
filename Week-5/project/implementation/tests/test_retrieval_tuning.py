"""Retrieval tuning — threshold and top-K injection cap."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cmis.config import get_max_inject_count, get_relevance_threshold
from cmis.models import MemoryRecord, MemoryStatus, MemoryType, SensitivityLevel
from cmis.ranking.ranker import rank_memories


def _memory(
    *,
    content: str,
    importance: float,
    similarity: float,
) -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        memory_id=uuid4(),
        tenant_id="acme",
        user_id="alice",
        content=content,
        memory_type=MemoryType.PREFERENCE if "prefer" in content else MemoryType.FACT,
        status=MemoryStatus.ACTIVE,
        importance=importance,
        confidence=1.0,
        embedding_model="test",
        contains_pii=False,
        sensitivity_level=SensitivityLevel.INTERNAL,
        created_at=now,
        similarity=similarity,
    )


def test_bge_default_threshold_excludes_mumbai_false_positive(monkeypatch) -> None:
    """Morning-drink query: Mumbai at ~0.597 should fail BGE default threshold 0.62."""
    monkeypatch.setenv("CMIS_EMBEDDER", "bge")
    monkeypatch.delenv("CMIS_RELEVANCE_THRESHOLD", raising=False)

    coffee = _memory(
        content="I prefer coffee every morning",
        importance=0.8,
        similarity=0.69,
    )
    mumbai = _memory(
        content="I live in Mumbai",
        importance=0.7,
        similarity=0.48,
    )

    threshold = get_relevance_threshold()
    assert threshold == 0.62

    ranking = rank_memories([coffee, mumbai], threshold=threshold, now=coffee.created_at)
    assert len(ranking.ranked) == 1
    assert ranking.ranked[0].memory.content == coffee.content
    assert ranking.dropped_by_threshold == 1


def test_top_k_caps_injection_after_threshold(monkeypatch) -> None:
    """Only the top max_inject memories pass even when several clear the threshold."""
    monkeypatch.setenv("CMIS_EMBEDDER", "bge")
    monkeypatch.setenv("CMIS_MAX_INJECT_COUNT", "2")

    memories = [
        _memory(content=f"Preference {index}", importance=0.8, similarity=0.9 - index * 0.05)
        for index in range(4)
    ]

    ranking = rank_memories(
        memories,
        threshold=0.3,
        max_inject=get_max_inject_count(),
        now=memories[0].created_at,
    )
    assert len(ranking.ranked) == 2
    assert ranking.dropped_by_top_k == 2


def test_bge_default_max_inject_count(monkeypatch) -> None:
    monkeypatch.setenv("CMIS_EMBEDDER", "bge")
    monkeypatch.delenv("CMIS_MAX_INJECT_COUNT", raising=False)
    assert get_max_inject_count() == 5


def test_deterministic_default_has_no_inject_cap(monkeypatch) -> None:
    monkeypatch.setenv("CMIS_EMBEDDER", "deterministic")
    monkeypatch.delenv("CMIS_MAX_INJECT_COUNT", raising=False)
    assert get_max_inject_count() is None
