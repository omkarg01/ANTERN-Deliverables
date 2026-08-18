from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID

from cmis.models import MemoryRecord


class LLMConflictChoice(str, Enum):
    NO_CONFLICT = "no_conflict"
    SUPERSEDE_EXISTING = "supersede_existing"
    REJECT_NEW = "reject_new"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True)
class LLMConflictDecision:
    choice: LLMConflictChoice
    reasoning: str
    supersede_ids: tuple[UUID, ...] = ()


class ConflictLLMResolver(Protocol):
    def resolve(
        self,
        *,
        new_content: str,
        existing: list[MemoryRecord],
    ) -> LLMConflictDecision: ...


class MockConflictLLMResolver:
    """Deterministic stand-in for async LLM fallback in tests and local dev."""

    def __init__(
        self,
        *,
        default_choice: LLMConflictChoice = LLMConflictChoice.SUPERSEDE_EXISTING,
    ) -> None:
        self._default_choice = default_choice

    def resolve(
        self,
        *,
        new_content: str,
        existing: list[MemoryRecord],
    ) -> LLMConflictDecision:
        del new_content
        if self._default_choice == LLMConflictChoice.SUPERSEDE_EXISTING:
            return LLMConflictDecision(
                choice=self._default_choice,
                reasoning="Mock LLM: supersede existing related memories",
                supersede_ids=tuple(memory.memory_id for memory in existing),
            )
        if self._default_choice == LLMConflictChoice.NO_CONFLICT:
            return LLMConflictDecision(
                choice=self._default_choice,
                reasoning="Mock LLM: no conflict detected",
            )
        if self._default_choice == LLMConflictChoice.REJECT_NEW:
            return LLMConflictDecision(
                choice=self._default_choice,
                reasoning="Mock LLM: reject new memory",
            )
        return LLMConflictDecision(
            choice=LLMConflictChoice.HUMAN_REVIEW,
            reasoning="Mock LLM: flagged for human review",
        )


@dataclass
class PendingConflictJob:
    new_memory_id: UUID
    tenant_id: str
    user_id: str
    new_content: str
    existing: list[MemoryRecord]


class AsyncConflictQueue:
    """In-process async queue for LLM conflict resolution (M4)."""

    def __init__(self) -> None:
        self._pending: list[PendingConflictJob] = []

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def enqueue(self, job: PendingConflictJob) -> None:
        self._pending.append(job)

    def drain(self) -> list[PendingConflictJob]:
        jobs = list(self._pending)
        self._pending.clear()
        return jobs
