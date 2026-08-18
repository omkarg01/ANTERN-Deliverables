from __future__ import annotations

from datetime import UTC, datetime

from cmis.models import (
    MemoryRecord,
    MemoryStatus,
    RankedMemory,
    RankingResult,
    RankingWeights,
)

DEFAULT_RANKING_WEIGHTS = RankingWeights()
DEFAULT_RELEVANCE_THRESHOLD = 0.3


def compute_recency(
    *,
    created_at: datetime,
    updated_at: datetime | None = None,
    now: datetime | None = None,
) -> float:
    """Recency decay: 1 / (1 + days_since_update)."""
    reference = updated_at or created_at
    current = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    days = max(0.0, (current - reference).total_seconds() / 86_400)
    return 1.0 / (1.0 + days)


def compute_combined_rank(
    *,
    similarity: float,
    importance: float,
    recency: float,
    weights: RankingWeights = DEFAULT_RANKING_WEIGHTS,
) -> float:
    return (
        weights.alpha_sim * similarity
        + weights.alpha_imp * importance
        + weights.alpha_rec * recency
    )


def filter_ranking_candidates(
    candidates: list[MemoryRecord],
    *,
    now: datetime | None = None,
) -> list[MemoryRecord]:
    """Drop superseded or expired memories before ranking (ADR-002)."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    eligible: list[MemoryRecord] = []
    for memory in candidates:
        if memory.status != MemoryStatus.ACTIVE:
            continue
        if memory.valid_until is not None:
            valid_until = memory.valid_until
            if valid_until.tzinfo is None:
                valid_until = valid_until.replace(tzinfo=UTC)
            if valid_until <= current:
                continue
        eligible.append(memory)
    return eligible


def rank_memories(
    candidates: list[MemoryRecord],
    *,
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    max_inject: int | None = None,
    weights: RankingWeights = DEFAULT_RANKING_WEIGHTS,
    now: datetime | None = None,
) -> RankingResult:
    filtered = filter_ranking_candidates(candidates, now=now)
    ranked: list[RankedMemory] = []

    for memory in filtered:
        similarity = memory.similarity if memory.similarity is not None else 0.0
        recency = compute_recency(
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            now=now,
        )
        combined = compute_combined_rank(
            similarity=similarity,
            importance=memory.importance,
            recency=recency,
            weights=weights,
        )
        ranked.append(
            RankedMemory(
                memory=memory,
                similarity_score=similarity,
                recency_score=recency,
                combined_rank=combined,
            )
        )

    ranked.sort(key=lambda item: item.combined_rank, reverse=True)
    passing = [item for item in ranked if item.combined_rank >= threshold]
    dropped = len(ranked) - len(passing)
    dropped_by_top_k = 0

    if max_inject is not None and max_inject > 0 and len(passing) > max_inject:
        dropped_by_top_k = len(passing) - max_inject
        passing = passing[:max_inject]

    if not passing:
        return RankingResult(
            ranked=[],
            abstention_reason=f"No memories above threshold {threshold}",
            dropped_by_threshold=dropped,
            dropped_by_top_k=dropped_by_top_k,
        )

    return RankingResult(
        ranked=passing,
        dropped_by_threshold=dropped,
        dropped_by_top_k=dropped_by_top_k,
    )
