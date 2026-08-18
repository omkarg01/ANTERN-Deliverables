"""M4 acceptance tests — conflict resolution and lifecycle jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cmis.formation.admission import AdmissionService
from cmis.formation.extraction import AdmissionDecision
from cmis.lifecycle.jobs import run_decay_job
from cmis.models import EventType, MemoryCreate, MemoryStatus, MemoryType
from cmis.storage.repository import MemoryRepository

pytestmark = pytest.mark.integration


def test_m4_t1_contradiction_resolution(admission: AdmissionService) -> None:
    """D3 B-01: vegetarian vs steak — one memory superseded."""
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I am vegetarian and never eat meat",
    )
    result = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="My favorite dinner is grilled steak",
    )
    assert result.decision == AdmissionDecision.ADMITTED

    repo = admission.repository
    active = repo.list_active_memories(tenant_id="acme", user_id="alice")
    assert len(active) == 1
    assert "steak" in active[0].content.lower()
    assert repo.count_for_scope(
        tenant_id="acme",
        user_id="alice",
        status=MemoryStatus.SUPERSEDED,
    ) == 1


def test_m4_t2_temporal_supersession(admission: AdmissionService) -> None:
    """D3 C-01: explicit instead-of supersedes tea preference."""
    tea = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I prefer tea every morning",
    )
    assert tea.memory is not None

    coffee = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I drink coffee instead of tea every morning",
    )
    assert coffee.memory is not None

    tea_record = admission.repository.get_memory(
        tea.memory.memory_id,
        tenant_id="acme",
        user_id="alice",
    )
    assert tea_record is not None
    assert tea_record.status == MemoryStatus.SUPERSEDED

    active = admission.repository.list_active_memories(
        tenant_id="acme",
        user_id="alice",
    )
    assert len(active) == 1
    assert "coffee" in active[0].content.lower()


def test_m4_t3_llm_fallback_async_resolution(admission: AdmissionService) -> None:
    """ADR-005: ambiguous pair queued for LLM; async job supersedes with audit log."""
    first = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="My favorite hobby is painting landscapes",
    )
    assert first.memory is not None

    second = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="My favorite hobby is sculpture",
    )
    assert second.decision == AdmissionDecision.ADMITTED
    assert admission.conflicts.queue.pending_count == 1

    processed = admission.process_conflict_queue()
    assert processed == 1

    first_record = admission.repository.get_memory(
        first.memory.memory_id,
        tenant_id="acme",
        user_id="alice",
    )
    assert first_record is not None
    assert first_record.status == MemoryStatus.SUPERSEDED

    events = admission.repository.list_events_for_memory(first.memory.memory_id)
    assert any(event.event_type == EventType.SUPERSEDED for event in events)
    assert any("LLM fallback" in (event.reason or "") for event in events)


def test_m4_t4_superseded_event_recorded(admission: AdmissionService) -> None:
    """ADR-001: supersession writes SUPERSEDED MemoryEvent."""
    tea = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I prefer tea every morning",
    )
    assert tea.memory is not None

    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I drink coffee instead of tea every morning",
    )

    events = admission.repository.list_events_for_memory(tea.memory.memory_id)
    assert any(event.event_type == EventType.SUPERSEDED for event in events)
    assert any(event.status_after == MemoryStatus.SUPERSEDED for event in events)


def test_m4_t5_lifecycle_decay(repo: MemoryRepository) -> None:
    """Decay job archives 100 old low-importance memories."""
    old_time = datetime.now(UTC) - timedelta(days=400)
    for index in range(100):
        record = repo.create_memory(
            MemoryCreate(
                tenant_id="acme",
                user_id="alice",
                content=f"Old low-importance memory {index}",
                importance=0.2,
            )
        )
        repo.set_memory_created_at(record.memory_id, old_time)

    result = run_decay_job(
        repo,
        tenant_id="acme",
        user_id="alice",
        as_of=datetime.now(UTC),
    )
    assert result.affected_count == 100
    assert repo.count_for_scope(
        tenant_id="acme",
        user_id="alice",
        status=MemoryStatus.ACTIVE,
    ) == 0
    assert repo.count_for_scope(
        tenant_id="acme",
        user_id="alice",
        status=MemoryStatus.ARCHIVED,
    ) == 100
