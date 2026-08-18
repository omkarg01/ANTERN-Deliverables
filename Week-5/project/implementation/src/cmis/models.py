from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class HardDeleteResult:
    events_erased: int
    cascaded_memory_ids: tuple[UUID, ...]


class MemoryType(str, Enum):
    PREFERENCE = "preference"
    FACT = "fact"
    CONSTRAINT = "constraint"
    CONTEXT = "context"
    REFLECTION = "reflection"
    EPISODIC = "episodic"


class EpisodeRelation(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    REPLACES = "replaces"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    DELETED = "deleted"


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class ActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    REFLECTION = "reflection"
    ADMIN = "admin"


class EventType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    DELETED = "deleted"
    RETRIEVED = "retrieved"
    INJECTED = "injected"


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: UUID
    tenant_id: str
    user_id: str
    content: str
    memory_type: MemoryType
    status: MemoryStatus
    importance: float
    confidence: float
    embedding_model: str | None
    contains_pii: bool
    sensitivity_level: SensitivityLevel
    created_at: datetime
    updated_at: datetime | None = None
    valid_until: datetime | None = None
    source_turn_id: UUID | None = None
    created_by: ActorType = ActorType.SYSTEM
    similarity: float | None = None


@dataclass(frozen=True)
class MemoryCreate:
    tenant_id: str
    user_id: str
    content: str
    memory_type: MemoryType = MemoryType.FACT
    importance: float = 0.5
    confidence: float = 1.0
    contains_pii: bool = False
    sensitivity_level: SensitivityLevel = SensitivityLevel.INTERNAL
    source_turn_id: UUID | None = None
    created_by: ActorType = ActorType.SYSTEM
    trace_id: str | None = None
    embedding: list[float] | None = None


@dataclass(frozen=True)
class MemoryEventRecord:
    event_id: UUID
    memory_id: UUID
    tenant_id: str
    user_id: str
    event_type: EventType
    status_after: MemoryStatus
    actor: ActorType
    event_time: datetime
    content_before: str | None = None
    content_after: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class RetrievalResult:
    memories: list[MemoryRecord]
    query: str
    tenant_id: str
    user_id: str
    candidate_count: int


@dataclass(frozen=True)
class RankingWeights:
    alpha_sim: float = 0.6
    alpha_imp: float = 0.3
    alpha_rec: float = 0.1


@dataclass(frozen=True)
class RankedMemory:
    memory: MemoryRecord
    similarity_score: float
    recency_score: float
    combined_rank: float

    @property
    def estimated_tokens(self) -> int:
        return max(1, len(self.memory.content) // 4)


@dataclass(frozen=True)
class RankingResult:
    ranked: list[RankedMemory]
    abstention_reason: str | None = None
    dropped_by_threshold: int = 0
    dropped_by_top_k: int = 0


@dataclass(frozen=True)
class ContextBlock:
    memories: list[RankedMemory]
    formatted_block: str
    total_tokens: int
    overflow_truncated: bool
    abstention_reason: str | None
    retrieval_count: int
    ranking_count: int
    injected_count: int
    dropped_count: int
