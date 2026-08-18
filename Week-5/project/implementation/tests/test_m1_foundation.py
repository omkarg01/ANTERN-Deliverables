"""M1 acceptance tests — storage, dual-write, tenant isolation, pgvector retrieval."""

from __future__ import annotations

import pytest

from cmis.embedder import cosine_similarity
from cmis.models import EventType, MemoryCreate, MemoryType
from cmis.retrieval.service import RetrievalService
from cmis.storage.repository import MemoryRepository

pytestmark = pytest.mark.integration


def test_m1_t2_dual_representation_write(repo: MemoryRepository) -> None:
    """ADR-001: Memory + MemoryEvent both populated on write."""
    record = repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="My office door code is 4455",
            memory_type=MemoryType.FACT,
            importance=0.9,
        )
    )
    events = repo.list_events_for_memory(record.memory_id)
    assert len(events) == 1
    assert events[0].event_type == EventType.CREATED
    assert events[0].content_after == record.content
    assert events[0].tenant_id == "acme"
    assert events[0].user_id == "alice"


def test_m1_t1_alice_bob_isolation(retrieval: RetrievalService) -> None:
    """D3 E-01: Alice retrieval never returns Bob memories."""
    repo = retrieval.repository
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="Alice project codename: NEBULA",
            memory_type=MemoryType.CONTEXT,
        )
    )
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="bob",
            content="Bob project codename: ORION",
            memory_type=MemoryType.CONTEXT,
        )
    )

    alice_result = retrieval.retrieve(
        query="What is my project codename?",
        tenant_id="acme",
        user_id="alice",
        top_k=5,
    )
    bob_result = retrieval.retrieve(
        query="What is my project codename?",
        tenant_id="acme",
        user_id="bob",
        top_k=5,
    )

    alice_texts = [m.content for m in alice_result.memories]
    bob_texts = [m.content for m in bob_result.memories]

    assert any("NEBULA" in t for t in alice_texts)
    assert not any("ORION" in t for t in alice_texts)
    assert any("ORION" in t for t in bob_texts)
    assert not any("NEBULA" in t for t in bob_texts)


def test_m1_t3_cross_tenant_returns_zero(repo: MemoryRepository) -> None:
    """Cross-tenant scoped search returns 0 results."""
    repo.create_memory(
        MemoryCreate(
            tenant_id="tenant_a",
            user_id="alice",
            content="Secret from tenant A",
        )
    )
    assert repo.count_for_scope(tenant_id="tenant_b", user_id="alice") == 0

    embedder = repo._embedder  # noqa: SLF001 — test scope
    hits = repo.search_by_embedding(
        tenant_id="tenant_b",
        user_id="alice",
        query_embedding=embedder.embed("Secret"),
        top_k=10,
    )
    assert hits == []


def test_m1_t4_embeddings_searchable(retrieval: RetrievalService) -> None:
    """Semantic search returns relevant memory for query."""
    repo = retrieval.repository
    door = repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="My office door code is 4455",
            memory_type=MemoryType.FACT,
            importance=0.9,
        )
    )
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I enjoy weekend hiking in the mountains",
            memory_type=MemoryType.PREFERENCE,
            importance=0.3,
        )
    )

    result = retrieval.retrieve(
        query="What is my office door code?",
        tenant_id="acme",
        user_id="alice",
        top_k=2,
    )
    assert result.candidate_count >= 1
    assert result.memories[0].memory_id == door.memory_id
    assert result.memories[0].similarity is not None
    assert result.memories[0].similarity > 0.5


def test_bulk_embed_search(repo: MemoryRepository) -> None:
    """M1-T4 extended: 100 memories embedded and searchable."""
    embedder = repo._embedder  # noqa: SLF001
    for i in range(100):
        repo.create_memory(
            MemoryCreate(
                tenant_id="acme",
                user_id="alice",
                content=f"Memory number {i} about topic {i % 7}",
            )
        )
    query_vec = embedder.embed("topic 3")
    hits = repo.search_by_embedding(
        tenant_id="acme",
        user_id="alice",
        query_embedding=query_vec,
        top_k=5,
    )
    assert len(hits) == 5
    assert all(h.similarity is not None for h in hits)


def test_cosine_helper_matches_pgvector_order(repo: MemoryRepository) -> None:
    """Deterministic embedder produces consistent ranking."""
    embedder = repo._embedder  # noqa: SLF001
    a = repo.create_memory(
        MemoryCreate(tenant_id="t", user_id="u", content="coffee every morning")
    )
    b = repo.create_memory(
        MemoryCreate(tenant_id="t", user_id="u", content="random unrelated astronomy facts")
    )
    q = embedder.embed("morning coffee drink")
    sim_a = cosine_similarity(q, embedder.embed(a.content))
    sim_b = cosine_similarity(q, embedder.embed(b.content))
    assert sim_a > sim_b

    hits = repo.search_by_embedding(
        tenant_id="t", user_id="u", query_embedding=q, top_k=2
    )
    assert hits[0].memory_id == a.memory_id
