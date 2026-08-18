from __future__ import annotations

import asyncio

from cmis.conflict.llm import PendingConflictJob
from cmis.config import (
    get_temporal_host,
    get_temporal_namespace,
    get_temporal_task_queue,
    is_temporal_enabled,
)
from cmis.workflows.activities import process_conflict_job_sync, run_lifecycle_sync
from cmis.workflows.models import (
    ConflictWorkflowInput,
    LifecycleWorkflowInput,
    WorkflowStartResult,
)


class WorkflowDispatcher:
    """Start background jobs via Temporal or in-process fallback."""

    def start_lifecycle(self, *, tenant_id: str, user_id: str) -> WorkflowStartResult:
        payload = LifecycleWorkflowInput(tenant_id=tenant_id, user_id=user_id)
        workflow_id = f"lifecycle-{tenant_id}-{user_id}"
        if is_temporal_enabled():
            return _run_async(self._start_temporal_lifecycle(payload, workflow_id=workflow_id))
        result = run_lifecycle_sync(payload)
        return WorkflowStartResult(
            workflow_id=workflow_id,
            run_id="in-process",
            backend=(
                f"in-process decay={result.decay_archived} "
                f"expired={result.expiration_superseded}"
            ),
        )

    def start_conflict_resolution(self, job: PendingConflictJob) -> WorkflowStartResult:
        payload = ConflictWorkflowInput(
            new_memory_id=str(job.new_memory_id),
            tenant_id=job.tenant_id,
            user_id=job.user_id,
            new_content=job.new_content,
            existing_memory_ids=tuple(str(memory.memory_id) for memory in job.existing),
        )
        workflow_id = f"conflict-{job.new_memory_id}"
        if is_temporal_enabled():
            return _run_async(self._start_temporal_conflict(payload, workflow_id=workflow_id))
        result = process_conflict_job_sync(payload)
        return WorkflowStartResult(
            workflow_id=workflow_id,
            run_id="in-process",
            backend=f"in-process processed={result.processed} reason={result.reason}",
        )

    async def _start_temporal_lifecycle(
        self,
        payload: LifecycleWorkflowInput,
        *,
        workflow_id: str,
    ) -> WorkflowStartResult:
        from temporalio.client import Client

        from cmis.workflows.workflows import LifecycleWorkflow

        client = await Client.connect(
            get_temporal_host(),
            namespace=get_temporal_namespace(),
        )
        handle = await client.start_workflow(
            LifecycleWorkflow.run,
            payload,
            id=workflow_id,
            task_queue=get_temporal_task_queue(),
        )
        return WorkflowStartResult(
            workflow_id=handle.id,
            run_id=handle.result_run_id or "",
            backend="temporal",
        )

    async def _start_temporal_conflict(
        self,
        payload: ConflictWorkflowInput,
        *,
        workflow_id: str,
    ) -> WorkflowStartResult:
        from temporalio.client import Client

        from cmis.workflows.workflows import ConflictResolutionWorkflow

        client = await Client.connect(
            get_temporal_host(),
            namespace=get_temporal_namespace(),
        )
        handle = await client.start_workflow(
            ConflictResolutionWorkflow.run,
            payload,
            id=workflow_id,
            task_queue=get_temporal_task_queue(),
        )
        return WorkflowStartResult(
            workflow_id=handle.id,
            run_id=handle.result_run_id or "",
            backend="temporal",
        )


def _run_async(coro):
    return asyncio.run(coro)


_dispatcher: WorkflowDispatcher | None = None


def get_workflow_dispatcher() -> WorkflowDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = WorkflowDispatcher()
    return _dispatcher
