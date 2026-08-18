"""M8 acceptance tests — episodic memory, canonical state, validated temporal links."""

from __future__ import annotations

import pytest

from cmis.context.service import ContextService
from cmis.formation.admission import AdmissionService
from cmis.formation.extraction import AdmissionDecision, extract
from cmis.models import MemoryStatus, MemoryType

pytestmark = pytest.mark.integration


def test_m8_t1_before_tea_injects_coffee(
    admission: AdmissionService,
    context_service: ContextService,
) -> None:
    """Validated routine transition: coffee before tea for historical query."""
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="Every morning I drink coffee",
    )
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I switch my drink to tea",
    )

    block = context_service.build_context(
        query="What do I drink before tea?",
        tenant_id="acme",
        user_id="alice",
        relevance_threshold=0.62,
    )
    assert block.injected_count >= 2
    lowered = block.formatted_block.lower()
    assert "coffee" in lowered
    assert "tea" in lowered


def test_m8_t2_current_state_uses_canonical_not_chain_walk(
    admission: AdmissionService,
    context_service: ContextService,
) -> None:
    """Current-state query returns canonical tail, not all linked phases."""
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="Every morning I drink coffee",
    )
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I switch my drink to tea",
    )

    block = context_service.build_context(
        query="What do I drink in the morning?",
        tenant_id="acme",
        user_id="alice",
        relevance_threshold=0.62,
    )
    assert block.injected_count == 1
    lowered = block.formatted_block.lower()
    assert "tea" in lowered
    assert "coffee" not in lowered


def test_m8_t3_explicit_transition_and_replacement(
    admission: AdmissionService,
) -> None:
    """Explicit from-transition links; instead-of supersedes."""
    tea = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I prefer tea every morning",
    )
    assert tea.memory is not None

    coffee = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I switched from tea to coffee every morning",
    )
    assert coffee.decision == AdmissionDecision.ADMITTED

    tea_record = admission.repository.get_memory(
        tea.memory.memory_id,
        tenant_id="acme",
        user_id="alice",
    )
    assert tea_record is not None
    assert tea_record.status == MemoryStatus.ACTIVE

    predecessors = admission.repository.get_linked_predecessors(
        coffee.memory.memory_id,  # type: ignore[union-attr]
        tenant_id="acme",
        user_id="alice",
    )
    assert len(predecessors) == 1
    assert "tea" in predecessors[0].content.lower()

    soda = admission.admit(
        tenant_id="acme",
        user_id="bob",
        content="I like soda with lunch",
    )
    assert soda.memory is not None

    admission.admit(
        tenant_id="acme",
        user_id="bob",
        content="I drink water instead of soda",
    )

    soda_record = admission.repository.get_memory(
        soda.memory.memory_id,
        tenant_id="acme",
        user_id="bob",
    )
    assert soda_record is not None
    assert soda_record.status == MemoryStatus.SUPERSEDED


def test_m8_r1_preference_plus_unrelated_event(
    admission: AdmissionService,
    context_service: ContextService,
) -> None:
    """Episodic event must not become a false prior preference."""
    admission.admit(tenant_id="acme", user_id="alice", content="I prefer tea.")
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="Yesterday I tried coffee.",
    )

    current = context_service.build_context(
        query="What do I prefer?",
        tenant_id="acme",
        user_id="alice",
    )
    assert current.injected_count == 1
    assert "tea" in current.formatted_block.lower()
    assert "tried coffee" not in current.formatted_block.lower()

    historical = context_service.build_context(
        query="What did I prefer before tea?",
        tenant_id="acme",
        user_id="alice",
    )
    lowered = historical.formatted_block.lower()
    assert "tried coffee" not in lowered


def test_m8_r2_explicit_state_transition_queries(
    admission: AdmissionService,
    context_service: ContextService,
) -> None:
    admission.admit(tenant_id="acme", user_id="alice", content="I prefer tea.")
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I switched from tea to coffee.",
    )

    current = context_service.build_context(
        query="What do I prefer?",
        tenant_id="acme",
        user_id="alice",
    )
    assert current.injected_count == 1
    assert "coffee" in current.formatted_block.lower()

    historical = context_service.build_context(
        query="What did I prefer before coffee?",
        tenant_id="acme",
        user_id="alice",
        relevance_threshold=0.3,
    )
    lowered = historical.formatted_block.lower()
    assert "tea" in lowered
    assert "coffee" in lowered


def test_m8_r3_unrelated_events_not_traversed(
    admission: AdmissionService,
    context_service: ContextService,
) -> None:
    admission.admit(tenant_id="acme", user_id="alice", content="I prefer tea.")
    admission.admit(tenant_id="acme", user_id="alice", content="I tried coffee.")
    admission.admit(tenant_id="acme", user_id="alice", content="I visited Delhi.")
    admission.admit(tenant_id="acme", user_id="alice", content="I watched a movie.")

    block = context_service.build_context(
        query="What did I prefer before tea?",
        tenant_id="acme",
        user_id="alice",
    )
    lowered = block.formatted_block.lower()
    assert "delhi" not in lowered
    assert "movie" not in lowered
    assert "tried coffee" not in lowered


def test_m8_r4_episodic_classification_regression(
    admission: AdmissionService,
    context_service: ContextService,
) -> None:
    extracted = extract("Every morning I drink coffee")
    assert extracted is not None
    assert extracted.memory_type == MemoryType.EPISODIC

    event = extract("Yesterday I tried coffee")
    assert event is not None
    assert event.memory_type == MemoryType.EPISODIC

    preference = extract("I prefer tea.")
    assert preference is not None
    assert preference.memory_type == MemoryType.PREFERENCE

    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="My favorite color is blue",
    )

    block = context_service.build_context(
        query="What is my favorite color?",
        tenant_id="acme",
        user_id="alice",
    )
    assert block.injected_count == 1
    assert "blue" in block.formatted_block.lower()
