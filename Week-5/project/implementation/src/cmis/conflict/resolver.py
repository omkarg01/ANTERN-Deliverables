from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from cmis.episodic.semantics import is_state_transition, valid_state_transition
from cmis.formation.extraction import ExtractionResult
from cmis.models import EpisodeRelation, MemoryRecord


class ConflictAction(str, Enum):
    ADMIT = "admit"
    ADMIT_SUPERSEDE = "admit_supersede"
    ADMIT_LINK = "admit_link"
    REJECT = "reject"
    DEFER_LLM = "defer_llm"


@dataclass(frozen=True)
class ConflictDecision:
    action: ConflictAction
    reason: str
    supersede_ids: tuple[UUID, ...] = ()
    link_after_ids: tuple[UUID, ...] = ()
    link_relation: EpisodeRelation = EpisodeRelation.BEFORE
    defer_existing: tuple[MemoryRecord, ...] = ()


class ConflictResolver:
    """Deterministic conflict resolution fast path (ADR-005)."""

    def resolve(
        self,
        candidate: ExtractionResult,
        related: list[MemoryRecord],
    ) -> ConflictDecision:
        if not related:
            return ConflictDecision(
                action=ConflictAction.ADMIT,
                reason="No related memories",
            )

        if is_complementary(candidate.content):
            return ConflictDecision(
                action=ConflictAction.ADMIT,
                reason="Complementary memory; no supersession",
            )

        if is_explicit_replacement(candidate.content):
            return ConflictDecision(
                action=ConflictAction.ADMIT_SUPERSEDE,
                reason="Temporal supersession keyword detected",
                supersede_ids=tuple(memory.memory_id for memory in related),
            )

        transition_targets = [
            memory
            for memory in related
            if valid_state_transition(
                candidate.content,
                memory.content,
                candidate_type=candidate.memory_type,
                prior_type=memory.memory_type,
            )
        ]
        if transition_targets and is_state_transition(candidate.content):
            relation = (
                EpisodeRelation.REPLACES
                if uses_explicit_from_transition(candidate.content)
                else EpisodeRelation.BEFORE
            )
            return ConflictDecision(
                action=ConflictAction.ADMIT_LINK,
                reason="Validated state transition; link without blind supersession",
                link_after_ids=tuple(memory.memory_id for memory in transition_targets),
                link_relation=relation,
            )

        contradictions = [
            memory
            for memory in related
            if detect_contradiction(candidate.content, memory.content)
        ]
        if contradictions:
            if candidate.confidence >= max(memory.confidence for memory in contradictions):
                return ConflictDecision(
                    action=ConflictAction.ADMIT_SUPERSEDE,
                    reason="Explicit contradiction; new memory wins",
                    supersede_ids=tuple(memory.memory_id for memory in contradictions),
                )
            return ConflictDecision(
                action=ConflictAction.REJECT,
                reason="Lower confidence than existing contradictory memory",
            )

        if shares_topic(candidate.content, related[0].content) and len(related) == 1:
            if is_explicit_replacement(candidate.content):
                return ConflictDecision(
                    action=ConflictAction.ADMIT_SUPERSEDE,
                    reason="Same topic replacement",
                    supersede_ids=(related[0].memory_id,),
                )

        if len(related) >= 1 and not is_complementary(candidate.content):
            return ConflictDecision(
                action=ConflictAction.DEFER_LLM,
                reason="Ambiguous conflict; defer to LLM fallback",
                defer_existing=tuple(related),
            )

        return ConflictDecision(
            action=ConflictAction.ADMIT,
            reason="No deterministic conflict",
        )


from cmis.conflict.patterns import (  # noqa: E402
    detect_contradiction,
    is_complementary,
    is_explicit_replacement,
    shares_topic,
)
from cmis.episodic.semantics import uses_explicit_from_transition  # noqa: E402
