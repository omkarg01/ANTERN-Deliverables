from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cmis.models import MemoryRecord
from cmis.storage.repository import MemoryRepository


@dataclass(frozen=True)
class LifecycleJobResult:
    job: str
    affected_count: int


def run_decay_job(
    repository: MemoryRepository,
    *,
    tenant_id: str,
    user_id: str,
    as_of: datetime,
    min_age_days: int = 365,
    max_importance: float = 0.5,
) -> LifecycleJobResult:
    """Archive stale low-importance memories (uses created_at as inactivity proxy)."""
    candidates = repository.find_memories_for_decay(
        tenant_id=tenant_id,
        user_id=user_id,
        as_of=as_of,
        min_age_days=min_age_days,
        max_importance=max_importance,
    )
    archived = repository.archive_memories(
        memory_ids=[memory.memory_id for memory in candidates],
        tenant_id=tenant_id,
        user_id=user_id,
        reason="Lifecycle decay: inactive low-importance memory",
    )
    return LifecycleJobResult(job="decay", affected_count=archived)


def run_expiration_job(
    repository: MemoryRepository,
    *,
    as_of: datetime,
) -> LifecycleJobResult:
    expired = repository.expire_memories(as_of=as_of)
    return LifecycleJobResult(job="expiration", affected_count=expired)


def run_lifecycle_jobs(
    repository: MemoryRepository,
    *,
    tenant_id: str,
    user_id: str,
    as_of: datetime,
) -> list[LifecycleJobResult]:
    return [
        run_decay_job(repository, tenant_id=tenant_id, user_id=user_id, as_of=as_of),
        run_expiration_job(repository, as_of=as_of),
    ]
