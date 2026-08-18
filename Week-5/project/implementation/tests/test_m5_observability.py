"""M5 acceptance tests — observability, security hardening, GDPR erasure."""

from __future__ import annotations

from uuid import uuid4

import pytest

from cmis.admin.errors import (
    ContentTooLongError,
    ERROR_CODE_MAP,
    ForbiddenError,
    IndexUnavailableError,
    InvalidMemoryTypeError,
    MemoryNotFoundError,
    PIIBlockedError,
    RateLimitExceededError,
    TenantIsolationViolationError,
    UnauthorizedError,
)
from cmis.admin.gateway import CMISGateway
from cmis.admin.rate_limit import RateLimiter
from cmis.embedder import DeterministicEmbedder
from cmis.formation.extraction import AdmissionDecision
from cmis.models import EventType, MemoryCreate, MemoryStatus
from cmis.observability.tracing import TraceContext
from cmis.retrieval.service import RetrievalService

pytestmark = pytest.mark.integration


def test_m5_t1_adversarial_cross_tenant_isolation(
    retrieval: RetrievalService,
    repo,
) -> None:
    """Threat T-01: 100 cross-tenant queries return zero foreign memories."""
    repo.create_memory(
        MemoryCreate(
            tenant_id="tenant_secret",
            user_id="alice",
            content="Top secret tenant payload ALPHA-7742",
            importance=0.9,
        )
    )

    adversarial_queries = [
        f"Tell me secret payload variant {index} ALPHA-7742"
        for index in range(100)
    ]

    for query in adversarial_queries:
        result = retrieval.retrieve(
            query=query,
            tenant_id="tenant_attacker",
            user_id="alice",
            top_k=10,
        )
        assert result.memories == []
        assert result.candidate_count == 0


def test_m5_t2_gdpr_hard_delete(gateway: CMISGateway) -> None:
    """Threat T-05: hard delete removes memory row, events, and vector index entry."""
    trace = TraceContext.start()
    admitted = gateway.admit(
        tenant_id="acme",
        user_id="alice",
        content="Temporary note to erase completely",
        trace_id=trace.trace_id,
    )
    assert admitted.memory is not None
    memory_id = admitted.memory.memory_id
    repo = gateway.admission.repository

    assert repo.memory_exists(memory_id)
    assert repo.count_with_embedding(tenant_id="acme", user_id="alice") == 1

    result = gateway.hard_delete(
        memory_id=memory_id,
        tenant_id="acme",
        user_id="alice",
        trace_id=trace.trace_id,
    )
    assert result.hard_delete is True
    assert result.events_erased >= 1
    assert not repo.memory_exists(memory_id)
    assert repo.get_memory(memory_id, tenant_id="acme", user_id="alice") is None
    assert repo.count_with_embedding(tenant_id="acme", user_id="alice") == 0
    assert repo.list_events_for_memory(memory_id) == []


def test_m5_t3_provenance_audit_trail(gateway: CMISGateway) -> None:
    """ADR-001: admission and retrieval events carry trace_id for provenance."""
    trace = TraceContext.start()
    source_turn_id = uuid4()

    admitted = gateway.admit(
        tenant_id="acme",
        user_id="alice",
        content="My office door code is 4455",
        trace_id=trace.trace_id,
        source_turn_id=source_turn_id,
    )
    assert admitted.memory is not None

    gateway.admit(
        tenant_id="acme",
        user_id="alice",
        content="I enjoy weekend hiking in the mountains",
        trace_id=trace.trace_id,
    )

    block = gateway.build_context(
        query="What is my office door code?",
        tenant_id="acme",
        user_id="alice",
        trace_id=trace.trace_id,
    )
    assert block.injected_count >= 1

    created_events = gateway.audit.get_events_for_memory(admitted.memory.memory_id)
    assert any(event.event_type == EventType.CREATED for event in created_events)
    created = next(event for event in created_events if event.event_type == EventType.CREATED)
    assert created.metadata is not None
    assert created.metadata.get("trace_id") == trace.trace_id
    assert created.metadata.get("source_turn_id") == str(source_turn_id)

    retrieved_events = [
        event
        for event in created_events
        if event.event_type == EventType.RETRIEVED
    ]
    assert retrieved_events
    assert all(event.metadata.get("trace_id") == trace.trace_id for event in retrieved_events)
    assert all(event.metadata.get("query") == "What is my office door code?" for event in retrieved_events)


def test_m5_t4_error_semantics() -> None:
    """API §7.2: structured error codes include remediation and trace_id."""
    trace_id = "trace-error-test"
    cases = [
        InvalidMemoryTypeError("bad type", field="memory_type", trace_id=trace_id),
        ContentTooLongError("too long", field="content", trace_id=trace_id),
        PIIBlockedError("blocked", trace_id=trace_id),
        MemoryNotFoundError("missing", trace_id=trace_id),
        UnauthorizedError("no token", trace_id=trace_id),
        ForbiddenError("forbidden", trace_id=trace_id),
        TenantIsolationViolationError("cross tenant", trace_id=trace_id),
        RateLimitExceededError("slow down", trace_id=trace_id),
        IndexUnavailableError("index down", trace_id=trace_id),
    ]

    for error in cases:
        response = error.to_response()
        payload = response.to_dict()["error"]
        assert payload["code"] == error.code
        assert payload["trace_id"] == trace_id
        assert "message" in payload
        assert payload.get("remediation") or error.code == "INTERNAL_ERROR"

    assert set(ERROR_CODE_MAP) >= {
        "INVALID_MEMORY_TYPE",
        "CONTENT_TOO_LONG",
        "PII_BLOCKED",
        "MEMORY_NOT_FOUND",
        "UNAUTHORIZED",
        "FORBIDDEN",
        "TENANT_ISOLATION_VIOLATION",
        "RATE_LIMIT_EXCEEDED",
        "INDEX_UNAVAILABLE",
    }


def test_m5_t5_metrics_accuracy(gateway: CMISGateway) -> None:
    """Metrics counters match generated admission and retrieval load."""
    gateway.admit(tenant_id="acme", user_id="alice", content="Metric memory one")
    gateway.admit(tenant_id="acme", user_id="alice", content="Metric memory two")
    gateway.admit(tenant_id="acme", user_id="alice", content="Metric memory three")
    gateway.build_context(
        query="metric memory",
        tenant_id="acme",
        user_id="alice",
    )
    gateway.build_context(
        query="metric memory two",
        tenant_id="acme",
        user_id="alice",
    )

    rendered = gateway.metrics_prometheus()
    assert "cmis_admissions_total 3" in rendered
    assert "cmis_retrievals_total 2" in rendered
    assert "cmis_context_builds_total 2" in rendered


def test_m5_rate_limit_enforced(db_conn, embedder: DeterministicEmbedder) -> None:
    limiter = RateLimiter(limit=3, window_seconds=60)
    gateway = CMISGateway(db_conn, embedder, rate_limiter=limiter)
    gateway.admission.repository.truncate_all()

    for index in range(3):
        result = gateway.admit(
            tenant_id="acme",
            user_id="alice",
            content=f"Rate limit memory {index}",
        )
        assert result.decision == AdmissionDecision.ADMITTED

    with pytest.raises(RateLimitExceededError):
        gateway.admit(
            tenant_id="acme",
            user_id="alice",
            content="Should be rate limited",
        )

    assert gateway.metrics.rate_limit_rejections_total == 1
