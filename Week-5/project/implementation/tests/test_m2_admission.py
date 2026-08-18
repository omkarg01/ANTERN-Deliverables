"""M2 acceptance tests — admission gate, PII tagging, confidential retrieval filter."""

from __future__ import annotations

import pytest

from cmis.formation.admission import AdmissionService
from cmis.formation.extraction import AdmissionDecision
from cmis.models import EventType, MemoryType, SensitivityLevel
from cmis.retrieval.service import RetrievalService

pytestmark = pytest.mark.integration


def test_m2_t1_reject_query(admission: AdmissionService) -> None:
    """Queries are not stored as memories."""
    result = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="What do I drink?",
    )
    assert result.decision == AdmissionDecision.REJECTED
    assert result.memory is None
    assert admission.repository.count_for_scope(tenant_id="acme", user_id="alice") == 0


def test_m2_t2_pii_admitted_and_tagged(admission: AdmissionService) -> None:
    """ADR-004: PII content is admitted with contains_pii and CONFIDENTIAL."""
    result = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="My SSN is 123-45-6789",
    )
    assert result.decision == AdmissionDecision.ADMITTED
    assert result.memory is not None
    assert result.memory.contains_pii is True
    assert result.memory.sensitivity_level == SensitivityLevel.CONFIDENTIAL


def test_m2_t3_confidential_hidden_from_general_retrieval(
    admission: AdmissionService,
    retrieval: RetrievalService,
) -> None:
    """Layer 2: general queries must not surface CONFIDENTIAL memories."""
    admission.repository.truncate_all()
    retrieval.repository.truncate_all()

    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="My SSN is 123-45-6789",
    )
    admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I enjoy hiking on weekends",
    )

    result = retrieval.retrieve(
        query="hobbies",
        tenant_id="acme",
        user_id="alice",
        top_k=5,
    )
    contents = [memory.content for memory in result.memories]
    assert any("hiking" in text for text in contents)
    assert not any("SSN" in text for text in contents)


def test_m2_t4_preference_classification(admission: AdmissionService) -> None:
    """Preference utterances map to memory_type=PREFERENCE."""
    result = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="I prefer oat milk in my coffee",
    )
    assert result.decision == AdmissionDecision.ADMITTED
    assert result.memory is not None
    assert result.memory.memory_type == MemoryType.PREFERENCE


def test_m2_t5_admission_creates_audit_event(admission: AdmissionService) -> None:
    """Admission writes MemoryEvent audit trail on admit."""
    result = admission.admit(
        tenant_id="acme",
        user_id="alice",
        content="My favorite color is blue",
    )
    assert result.decision == AdmissionDecision.ADMITTED
    assert result.memory is not None

    events = admission.repository.list_events_for_memory(result.memory.memory_id)
    assert len(events) == 1
    assert events[0].event_type == EventType.CREATED
    assert events[0].content_after == result.memory.content
