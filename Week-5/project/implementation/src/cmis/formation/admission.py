from __future__ import annotations

from uuid import UUID

import psycopg

from cmis.conflict.llm import PendingConflictJob
from cmis.conflict.resolver import ConflictAction
from cmis.conflict.service import ConflictService
from cmis.config import is_temporal_enabled
from cmis.embedder import Embedder
from cmis.episodic.semantics import infer_state_key, is_preference_state, is_routine_state
from cmis.formation.extraction import AdmissionDecision, AdmissionResult, extract
from cmis.models import ActorType, MemoryCreate
from cmis.privacy.pii import scan_pii
from cmis.storage.repository import MemoryRepository
from cmis.workflows.client import get_workflow_dispatcher


class AdmissionService:
    """Combined extraction + admission gate with conflict resolution (ADR-003/005)."""

    def __init__(self, conn: psycopg.Connection, embedder: Embedder) -> None:
        self._repo = MemoryRepository(conn, embedder)
        self._conflicts = ConflictService(self._repo, embedder)

    @property
    def repository(self) -> MemoryRepository:
        return self._repo

    @property
    def conflicts(self) -> ConflictService:
        return self._conflicts

    def admit(
        self,
        *,
        tenant_id: str,
        user_id: str,
        content: str,
        created_by: ActorType = ActorType.USER,
        trace_id: str | None = None,
        source_turn_id: UUID | None = None,
    ) -> AdmissionResult:
        extracted = extract(content)
        if extracted is None:
            return AdmissionResult(
                decision=AdmissionDecision.REJECTED,
                reason="Not memory-worthy: query or filler rejected",
            )

        pii = scan_pii(content.strip())
        related = self._conflicts.find_related(
            tenant_id=tenant_id,
            user_id=user_id,
            candidate=extracted,
        )
        conflict = self._conflicts.resolve(extracted, related)

        if conflict.action == ConflictAction.REJECT:
            return AdmissionResult(
                decision=AdmissionDecision.REJECTED,
                reason=conflict.reason,
            )

        record = self._repo.create_memory(
            MemoryCreate(
                tenant_id=tenant_id,
                user_id=user_id,
                content=extracted.content,
                memory_type=extracted.memory_type,
                importance=extracted.importance,
                confidence=extracted.confidence,
                contains_pii=pii.contains_pii,
                sensitivity_level=pii.sensitivity_level,
                created_by=created_by,
                trace_id=trace_id,
                source_turn_id=source_turn_id,
            )
        )

        state_key = infer_state_key(extracted.content)

        if conflict.action == ConflictAction.ADMIT_SUPERSEDE and conflict.supersede_ids:
            self._repo.supersede_memories(
                memory_ids=list(conflict.supersede_ids),
                superseded_by=record.memory_id,
                tenant_id=tenant_id,
                user_id=user_id,
                reason=conflict.reason,
                actor=created_by,
            )
            self._repo.upsert_canonical_state(
                tenant_id=tenant_id,
                user_id=user_id,
                state_key=state_key,
                memory_id=record.memory_id,
            )

        if conflict.action == ConflictAction.ADMIT_LINK and conflict.link_after_ids:
            for prior_id in conflict.link_after_ids:
                self._repo.create_episode_link(
                    from_memory_id=prior_id,
                    to_memory_id=record.memory_id,
                    relation=conflict.link_relation,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            self._repo.upsert_canonical_state(
                tenant_id=tenant_id,
                user_id=user_id,
                state_key=state_key,
                memory_id=record.memory_id,
            )
        elif is_preference_state(extracted.content):
            self._repo.upsert_canonical_state_if_absent(
                tenant_id=tenant_id,
                user_id=user_id,
                state_key=state_key,
                memory_id=record.memory_id,
            )
        elif is_routine_state(extracted.content):
            self._repo.upsert_canonical_state_if_absent(
                tenant_id=tenant_id,
                user_id=user_id,
                state_key=state_key,
                memory_id=record.memory_id,
            )

        reason = "Memory admitted"
        if pii.contains_pii:
            reason = f"Memory admitted with PII tags: {', '.join(pii.matched_patterns)}"
        elif conflict.action == ConflictAction.ADMIT_SUPERSEDE:
            reason = f"Memory admitted with supersession: {conflict.reason}"
        elif conflict.action == ConflictAction.ADMIT_LINK:
            reason = f"Memory admitted with validated episode link: {conflict.reason}"
        elif conflict.action == ConflictAction.DEFER_LLM:
            job = PendingConflictJob(
                new_memory_id=record.memory_id,
                tenant_id=tenant_id,
                user_id=user_id,
                new_content=extracted.content,
                existing=list(conflict.defer_existing),
            )
            if is_temporal_enabled():
                start = get_workflow_dispatcher().start_conflict_resolution(job)
                reason = (
                    "Memory admitted; conflict resolution workflow started: "
                    f"{start.workflow_id} ({start.backend})"
                )
            else:
                self._conflicts.queue.enqueue(job)
                reason = f"Memory admitted; LLM conflict resolution queued: {conflict.reason}"

        return AdmissionResult(
            decision=AdmissionDecision.ADMITTED,
            reason=reason,
            memory=record,
        )

    def process_conflict_queue(self) -> int:
        return self._conflicts.process_pending_llm_jobs()
