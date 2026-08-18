from __future__ import annotations

from datetime import timedelta

from cmis.workflows.activities import (
    process_conflict_job_activity,
    run_lifecycle_decay_activity,
    run_lifecycle_expiration_activity,
)
from cmis.workflows.models import (
    ConflictWorkflowInput,
    ConflictWorkflowResult,
    LifecycleWorkflowInput,
    LifecycleWorkflowResult,
)

try:
    from temporalio import workflow
    from temporalio.common import RetryPolicy
except ImportError:  # pragma: no cover
    workflow = None  # type: ignore[assignment]
    RetryPolicy = None  # type: ignore[assignment,misc]

if workflow is not None:

    @workflow.defn
    class LifecycleWorkflow:
        """Durable decay + expiration for a tenant/user scope (M9)."""

        @workflow.run
        async def run(self, input: LifecycleWorkflowInput) -> LifecycleWorkflowResult:
            decay_archived = await workflow.execute_activity(
                run_lifecycle_decay_activity,
                input,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            expiration_superseded = await workflow.execute_activity(
                run_lifecycle_expiration_activity,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            return LifecycleWorkflowResult(
                decay_archived=decay_archived,
                expiration_superseded=expiration_superseded,
            )

    @workflow.defn
    class ConflictResolutionWorkflow:
        """Async LLM conflict resolution with idempotent activity (M9)."""

        @workflow.run
        async def run(self, input: ConflictWorkflowInput) -> ConflictWorkflowResult:
            return await workflow.execute_activity(
                process_conflict_job_activity,
                input,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

else:  # pragma: no cover
    LifecycleWorkflow = None  # type: ignore[misc, assignment]
    ConflictResolutionWorkflow = None  # type: ignore[misc, assignment]
