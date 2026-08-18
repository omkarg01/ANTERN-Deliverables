from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LifecycleWorkflowInput:
    tenant_id: str
    user_id: str


@dataclass(frozen=True)
class LifecycleWorkflowResult:
    decay_archived: int
    expiration_superseded: int


@dataclass(frozen=True)
class ConflictWorkflowInput:
    new_memory_id: str
    tenant_id: str
    user_id: str
    new_content: str
    existing_memory_ids: tuple[str, ...]


@dataclass(frozen=True)
class ConflictWorkflowResult:
    processed: bool
    reason: str


@dataclass(frozen=True)
class WorkflowStartResult:
    workflow_id: str
    run_id: str
    backend: str
