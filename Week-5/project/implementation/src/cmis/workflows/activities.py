from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import psycopg

from cmis.conflict.llm import MockConflictLLMResolver, PendingConflictJob
from cmis.conflict.service import ConflictService
from cmis.config import get_database_url
from cmis.embedder import create_embedder
from cmis.lifecycle.jobs import run_decay_job, run_expiration_job
from cmis.models import MemoryStatus
from cmis.storage.repository import MemoryRepository
from cmis.workflows.models import (
    ConflictWorkflowInput,
    ConflictWorkflowResult,
    LifecycleWorkflowInput,
    LifecycleWorkflowResult,
)

try:
    from temporalio import activity
except ImportError:  # pragma: no cover
    activity = None  # type: ignore[assignment]


def _connect() -> psycopg.Connection:
    return psycopg.connect(get_database_url(), autocommit=False)


def _activity_defn(fn):  # type: ignore[no-untyped-def]
    if activity is None:
        return fn
    return activity.defn(fn)


@_activity_defn
def run_lifecycle_decay_activity(input: LifecycleWorkflowInput) -> int:
    with _connect() as conn:
        repo = MemoryRepository(conn, create_embedder())
        result = run_decay_job(
            repo,
            tenant_id=input.tenant_id,
            user_id=input.user_id,
            as_of=datetime.now(UTC),
        )
    return result.affected_count


@_activity_defn
def run_lifecycle_expiration_activity() -> int:
    with _connect() as conn:
        repo = MemoryRepository(conn, create_embedder())
        result = run_expiration_job(repo, as_of=datetime.now(UTC))
    return result.affected_count


@_activity_defn
def process_conflict_job_activity(input: ConflictWorkflowInput) -> ConflictWorkflowResult:
    with _connect() as conn:
        repo = MemoryRepository(conn, create_embedder())
        conflicts = ConflictService(repo, create_embedder(), llm_resolver=MockConflictLLMResolver())

        new_memory = repo.get_memory(
            UUID(input.new_memory_id),
            tenant_id=input.tenant_id,
            user_id=input.user_id,
        )
        if new_memory is None or new_memory.status != MemoryStatus.ACTIVE:
            return ConflictWorkflowResult(
                processed=False,
                reason="New memory missing or not active; skip idempotent retry",
            )

        existing = []
        for memory_id in input.existing_memory_ids:
            record = repo.get_memory(
                UUID(memory_id),
                tenant_id=input.tenant_id,
                user_id=input.user_id,
            )
            if record is not None and record.status == MemoryStatus.ACTIVE:
                existing.append(record)

        if not existing:
            return ConflictWorkflowResult(
                processed=False,
                reason="No active conflicting memories remain; skip duplicate supersession",
            )

        job = PendingConflictJob(
            new_memory_id=UUID(input.new_memory_id),
            tenant_id=input.tenant_id,
            user_id=input.user_id,
            new_content=input.new_content,
            existing=existing,
        )
        processed = conflicts.process_conflict_jobs([job])
        if processed:
            return ConflictWorkflowResult(processed=True, reason="Conflict resolved via LLM activity")
        return ConflictWorkflowResult(processed=False, reason="LLM chose no supersession")


def process_conflict_job_sync(input: ConflictWorkflowInput) -> ConflictWorkflowResult:
    return process_conflict_job_activity(input)


def run_lifecycle_sync(input: LifecycleWorkflowInput) -> LifecycleWorkflowResult:
    decay_archived = run_lifecycle_decay_activity(input)
    expiration_superseded = run_lifecycle_expiration_activity()
    return LifecycleWorkflowResult(
        decay_archived=decay_archived,
        expiration_superseded=expiration_superseded,
    )
