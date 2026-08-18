"""I4 acceptance tests — fuzzy normalize, hybrid RRF, rerank stub."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from cmis.context.service import ContextService
from cmis.formation.admission import AdmissionService
from cmis.formation.extraction import extract
from cmis.models import MemoryCreate, MemoryRecord, MemoryStatus, MemoryType, SensitivityLevel
from cmis.retrieval.hybrid import reciprocal_rank_fusion
from cmis.retrieval.service import RetrievalService

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _i4_enable_stub_rerank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CMIS_RERANKER", "stub")
    monkeypatch.setenv("CMIS_HYBRID_RETRIEVAL", "1")


def test_i4_t1_fuzzy_admission_vegeterian(admission: AdmissionService) -> None:
    """I4-T1: vegeterian typo → PREFERENCE 0.8 canonical content."""
    result = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I am vegeterian",
    )
    assert result.memory is not None
    assert result.memory.memory_type == MemoryType.PREFERENCE
    assert result.memory.importance == 0.8
    assert "vegetarian" in result.memory.content


def test_i4_t1_extract_unit() -> None:
    parsed = extract("I am vegeterian")
    assert parsed is not None
    assert parsed.memory_type == MemoryType.PREFERENCE


def test_i4_t2_hybrid_mumbai_typo_query(
    admission: AdmissionService,
    retrieval: RetrievalService,
) -> None:
    """I4-T2: query Mubai retrieves Mumbai memory via normalize + FTS hybrid."""
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I live in Mumbai",
    )
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I prefer coffee every morning",
    )

    result = retrieval.retrieve(
        query="Which restaurant in Mubai?",
        tenant_id="acme",
        user_id="alice",
    )
    contents = [memory.content.lower() for memory in result.memories]
    assert any("mumbai" in text for text in contents)


def test_i4_t3_restaurant_query_prefers_vegetarian(context_service: ContextService) -> None:
    """I4-T3: restaurant + vegetarian query injects diet memory over mango juice."""
    repo = context_service.retrieval.repository
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I am vegetarian",
            memory_type=MemoryType.PREFERENCE,
            importance=0.8,
        )
    )
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I like to drink mango juice in evening",
            memory_type=MemoryType.PREFERENCE,
            importance=0.8,
        )
    )
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I live in Mumbai",
            memory_type=MemoryType.FACT,
            importance=0.7,
        )
    )

    block = context_service.build_context(
        query="Which vegetarian restaurant should I go?",
        tenant_id="acme",
        user_id="alice",
    )

    assert block.abstention_reason is None
    assert block.injected_count >= 1
    injected_text = " ".join(item.memory.content.lower() for item in block.memories)
    assert "vegetarian" in injected_text
    if block.injected_count > 1:
        assert block.memories[0].memory.content.lower().find("vegetarian") >= 0


def test_i4_t4_typo_query_ranks_vegetarian_first(context_service: ContextService) -> None:
    """Rerank uses normalized search_text so vegeterian query ranks diet memory first."""
    repo = context_service.retrieval.repository
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I am vegetarian",
            memory_type=MemoryType.PREFERENCE,
            importance=0.8,
        )
    )
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I live in Mumbai",
            memory_type=MemoryType.FACT,
            importance=0.7,
        )
    )

    block = context_service.build_context(
        query="Which vegeterian restaurant should I go?",
        tenant_id="acme",
        user_id="alice",
    )

    assert block.injected_count >= 1
    assert "vegetarian" in block.memories[0].memory.content.lower()


def test_rrf_merges_dense_and_sparse_lists() -> None:
    now = datetime.now(UTC)
    beta_id = uuid4()
    dense = [
        _memory(content="alpha", similarity=0.9, now=now),
        _memory(content="beta", similarity=0.8, now=now, memory_id=beta_id),
    ]
    sparse = [
        _memory(content="beta", similarity=0.7, now=now, memory_id=beta_id),
        _memory(content="gamma", similarity=0.6, now=now),
    ]
    merged = reciprocal_rank_fusion([dense, sparse], k=60)
    ids = [memory.content for memory in merged]
    assert ids[0] == "beta"
    assert set(ids) == {"alpha", "beta", "gamma"}


def _memory(
    *,
    content: str,
    similarity: float,
    now: datetime,
    memory_id: UUID | None = None,
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id or uuid4(),
        tenant_id="acme",
        user_id="alice",
        content=content,
        memory_type=MemoryType.FACT,
        status=MemoryStatus.ACTIVE,
        importance=0.7,
        confidence=1.0,
        embedding_model="test",
        contains_pii=False,
        sensitivity_level=SensitivityLevel.INTERNAL,
        created_at=now,
        similarity=similarity,
    )
