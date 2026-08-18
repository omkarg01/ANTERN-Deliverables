from __future__ import annotations

from uuid import UUID

from cmis.conflict.llm import (
    AsyncConflictQueue,
    ConflictLLMResolver,
    LLMConflictChoice,
    MockConflictLLMResolver,
    PendingConflictJob,
)
from cmis.conflict.patterns import are_related, find_replacement_targets, is_full_replacement
from cmis.conflict.resolver import ConflictAction, ConflictDecision, ConflictResolver
from cmis.embedder import Embedder, cosine_similarity
from cmis.formation.extraction import ExtractionResult
from cmis.models import ActorType, MemoryRecord, MemoryStatus, MemoryType
from cmis.storage.repository import MemoryRepository


class ConflictService:
    """Detect and resolve memory conflicts at admission time (ADR-005)."""

    def __init__(
        self,
        repository: MemoryRepository,
        embedder: Embedder,
        *,
        llm_resolver: ConflictLLMResolver | None = None,
    ) -> None:
        self._repo = repository
        self._embedder = embedder
        self._resolver = ConflictResolver()
        self._llm = llm_resolver or MockConflictLLMResolver()
        self._queue = AsyncConflictQueue()

    @property
    def queue(self) -> AsyncConflictQueue:
        return self._queue

    def find_related(
        self,
        *,
        tenant_id: str,
        user_id: str,
        candidate: ExtractionResult,
    ) -> list[MemoryRecord]:
        active = self._repo.list_active_memories(
            tenant_id=tenant_id,
            user_id=user_id,
            memory_type=None
            if candidate.memory_type == MemoryType.EPISODIC or is_full_replacement(candidate.content)
            else candidate.memory_type,
        )
        candidate_vec = self._embedder.embed(candidate.content)
        related: list[MemoryRecord] = []
        seen: set[UUID] = set()
        if is_full_replacement(candidate.content):
            for memory in find_replacement_targets(candidate.content, active):
                if memory.memory_id not in seen:
                    related.append(memory)
                    seen.add(memory.memory_id)
        for memory in active:
            if memory.memory_id in seen:
                continue
            similarity = cosine_similarity(candidate_vec, self._embedder.embed(memory.content))
            if are_related(candidate.content, memory.content, similarity=similarity):
                related.append(memory)
                seen.add(memory.memory_id)
        return related

    def resolve(self, candidate: ExtractionResult, related: list[MemoryRecord]) -> ConflictDecision:
        return self._resolver.resolve(candidate, related)

    def process_pending_llm_jobs(
        self,
        *,
        llm_resolver: ConflictLLMResolver | None = None,
    ) -> int:
        return self.process_conflict_jobs(
            self._queue.drain(),
            llm_resolver=llm_resolver,
        )

    def process_conflict_jobs(
        self,
        jobs: list[PendingConflictJob],
        *,
        llm_resolver: ConflictLLMResolver | None = None,
    ) -> int:
        resolver = llm_resolver or self._llm
        processed = 0
        for job in jobs:
            if self._process_single_conflict_job(job, resolver=resolver):
                processed += 1
        return processed

    def _process_single_conflict_job(
        self,
        job: PendingConflictJob,
        *,
        resolver: ConflictLLMResolver,
    ) -> bool:
        active_existing = [
            memory for memory in job.existing if memory.status == MemoryStatus.ACTIVE
        ]
        if not active_existing:
            return False

        decision = resolver.resolve(
            new_content=job.new_content,
            existing=active_existing,
        )
        if decision.choice == LLMConflictChoice.SUPERSEDE_EXISTING and decision.supersede_ids:
            active_targets = [
                memory_id
                for memory_id in decision.supersede_ids
                if any(memory.memory_id == memory_id for memory in active_existing)
            ]
            if not active_targets:
                return False
            self._repo.supersede_memories(
                memory_ids=list(active_targets),
                superseded_by=job.new_memory_id,
                tenant_id=job.tenant_id,
                user_id=job.user_id,
                reason=f"LLM fallback: {decision.reasoning}",
                actor=ActorType.SYSTEM,
            )
            return True
        return False
