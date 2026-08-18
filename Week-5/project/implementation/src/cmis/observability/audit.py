from __future__ import annotations

from uuid import UUID

from cmis.models import EventType
from cmis.observability.tracing import get_trace_id, log_structured
from cmis.storage.repository import MemoryRepository


class AuditLogger:
    """Provenance audit trail for admission and retrieval (ADR-001, M5-T3)."""

    def __init__(self, repository: MemoryRepository) -> None:
        self._repo = repository

    def record_admission(
        self,
        *,
        memory_id: UUID,
        tenant_id: str,
        user_id: str,
        trace_id: str | None = None,
        source_turn_id: UUID | None = None,
    ) -> None:
        effective_trace = trace_id or get_trace_id()
        log_structured(
            "memory.admitted",
            memory_id=str(memory_id),
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=effective_trace,
            source_turn_id=str(source_turn_id) if source_turn_id else None,
        )

    def record_retrieval(
        self,
        *,
        tenant_id: str,
        user_id: str,
        query: str,
        memory_ids: list[UUID],
        trace_id: str | None = None,
    ) -> None:
        effective_trace = trace_id or get_trace_id()
        for memory_id in memory_ids:
            self._repo.append_audit_event(
                memory_id=memory_id,
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=EventType.RETRIEVED,
                reason="Provenance audit: retrieval",
                metadata={
                    "trace_id": effective_trace,
                    "query": query,
                    "operation": "retrieve",
                },
            )
        log_structured(
            "memory.retrieved",
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            memory_ids=[str(mid) for mid in memory_ids],
            trace_id=effective_trace,
        )

    def get_events_for_memory(self, memory_id: UUID):
        return self._repo.list_events_for_memory(memory_id)
