from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from cmis.config import get_temporal_host, get_temporal_namespace, get_temporal_task_queue
from cmis.workflows.activities import (
    process_conflict_job_activity,
    run_lifecycle_decay_activity,
    run_lifecycle_expiration_activity,
)
from cmis.workflows.workflows import ConflictResolutionWorkflow, LifecycleWorkflow


async def run_worker() -> None:
    from temporalio.client import Client
    from temporalio.worker import Worker

    client = await Client.connect(
        get_temporal_host(),
        namespace=get_temporal_namespace(),
    )
    worker = Worker(
        client,
        task_queue=get_temporal_task_queue(),
        workflows=[LifecycleWorkflow, ConflictResolutionWorkflow],
        activities=[
            run_lifecycle_decay_activity,
            run_lifecycle_expiration_activity,
            process_conflict_job_activity,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=4),
    )
    await worker.run()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
