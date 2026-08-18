"""M9 acceptance tests — Temporal workflows and in-process fallback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cmis.formation.admission import AdmissionService
from cmis.formation.extraction import AdmissionDecision
from cmis.lifecycle.jobs import run_decay_job
from cmis.models import MemoryCreate, MemoryStatus
from cmis.storage.repository import MemoryRepository
from cmis.workflows.activities import (
    process_conflict_job_activity,
    run_lifecycle_decay_activity,
    run_lifecycle_expiration_activity,
    run_lifecycle_sync,
)
from cmis.workflows.client import WorkflowDispatcher
from cmis.workflows.models import ConflictWorkflowInput, LifecycleWorkflowInput

pytestmark = pytest.mark.integration


def test_m9_t1_lifecycle_dispatcher_non_blocking(repo: MemoryRepository) -> None:
    """Lifecycle workflow returns immediately via in-process fallback."""
    old_time = datetime.now(UTC) - timedelta(days=400)
    record = repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="Old low-importance memory",
            importance=0.2,
        )
    )
    repo.set_memory_created_at(record.memory_id, old_time)

    dispatcher = WorkflowDispatcher()
    result = dispatcher.start_lifecycle(tenant_id="acme", user_id="alice")

    assert result.workflow_id == "lifecycle-acme-alice"
    assert "decay=1" in result.backend
    assert repo.count_for_scope(
        tenant_id="acme",
        user_id="alice",
        status=MemoryStatus.ARCHIVED,
    ) == 1


def test_m9_t2_conflict_idempotent_no_duplicate_supersession(
    admission: AdmissionService,
) -> None:
    """Retrying conflict activity does not supersede twice."""
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

    job = admission.conflicts.queue.drain()[0]
    payload = ConflictWorkflowInput(
        new_memory_id=str(job.new_memory_id),
        tenant_id=job.tenant_id,
        user_id=job.user_id,
        new_content=job.new_content,
        existing_memory_ids=tuple(str(memory.memory_id) for memory in job.existing),
    )

    first_result = process_conflict_job_activity(payload)
    second_result = process_conflict_job_activity(payload)

    assert first_result.processed is True
    assert second_result.processed is False
    assert (
        admission.repository.count_for_scope(
            tenant_id="acme",
            user_id="alice",
            status=MemoryStatus.SUPERSEDED,
        )
        == 1
    )


def test_m9_t3_m4_lifecycle_regression(repo: MemoryRepository) -> None:
    """M4 decay job still works alongside workflow activities."""
    old_time = datetime.now(UTC) - timedelta(days=400)
    for index in range(3):
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
    assert result.affected_count == 3

    sync_result = run_lifecycle_sync(
        LifecycleWorkflowInput(tenant_id="acme", user_id="alice"),
    )
    assert sync_result.decay_archived >= 0


def test_m9_t4_temporal_workflow_environment(repo: MemoryRepository) -> None:
    """Temporal workflow executes decay activity with retries (time-skipping env)."""
    pytest.importorskip("temporalio")
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    from cmis.workflows.workflows import LifecycleWorkflow

    old_time = datetime.now(UTC) - timedelta(days=400)
    record = repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="bob",
            content="Old low-importance memory",
            importance=0.2,
        )
    )
    repo.set_memory_created_at(record.memory_id, old_time)

    async def _run() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="cmis-test",
                workflows=[LifecycleWorkflow],
                activities=[run_lifecycle_decay_activity, run_lifecycle_expiration_activity],
                activity_executor=ThreadPoolExecutor(max_workers=2),
            ):
                result = await env.client.execute_workflow(
                    LifecycleWorkflow.run,
                    LifecycleWorkflowInput(tenant_id="acme", user_id="bob"),
                    id="test-lifecycle-bob",
                    task_queue="cmis-test",
                )
                assert result.decay_archived == 1

    asyncio.run(_run())
