from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cmis.admin.errors import MemoryNotFoundError, TenantIsolationViolationError
from cmis.models import ActorType
from cmis.observability.metrics import MetricsRegistry
from cmis.storage.repository import MemoryRepository


@dataclass(frozen=True)
class ErasureResult:
    memory_id: UUID
    hard_delete: bool
    events_erased: int
    cascaded_memory_ids: tuple[UUID, ...]
    trace_id: str | None


class ErasureService:
    """GDPR hard delete with cascading erasure (M5-T2)."""

    MAX_CONTENT_LENGTH = 10_000

    def __init__(
        self,
        repository: MemoryRepository,
        *,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self._repo = repository
        self._metrics = metrics or MetricsRegistry()

    def hard_delete(
        self,
        *,
        memory_id: UUID,
        tenant_id: str,
        user_id: str,
        trace_id: str | None = None,
        actor: ActorType = ActorType.ADMIN,
    ) -> ErasureResult:
        record = self._repo.get_memory(memory_id, tenant_id=tenant_id, user_id=user_id)
        if record is None:
            raise MemoryNotFoundError(
                f"Memory {memory_id} not found",
                trace_id=trace_id,
            )

        cascaded = self._repo.hard_delete_memory(
            memory_id=memory_id,
            tenant_id=tenant_id,
            user_id=user_id,
            actor=actor,
            trace_id=trace_id,
        )
        self._metrics.inc("hard_deletes_total")
        return ErasureResult(
            memory_id=memory_id,
            hard_delete=True,
            events_erased=cascaded.events_erased,
            cascaded_memory_ids=cascaded.cascaded_memory_ids,
            trace_id=trace_id,
        )

    @staticmethod
    def assert_tenant_scope(
        *,
        request_tenant_id: str,
        resource_tenant_id: str,
        trace_id: str | None = None,
    ) -> None:
        if request_tenant_id != resource_tenant_id:
            raise TenantIsolationViolationError(
                "Cross-tenant access denied",
                trace_id=trace_id,
            )
