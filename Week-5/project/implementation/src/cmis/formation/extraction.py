from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from cmis.episodic.semantics import is_episodic_event, is_routine_state, is_state_transition
from cmis.formation.normalize import normalize_memory_content
from cmis.models import MemoryRecord, MemoryType, SensitivityLevel

_QUERY_STARTERS = (
    "what ",
    "when ",
    "where ",
    "who ",
    "whom ",
    "why ",
    "how ",
    "do ",
    "does ",
    "did ",
    "can ",
    "could ",
    "is ",
    "are ",
    "was ",
    "were ",
    "will ",
    "would ",
    "should ",
)

_FILLER = frozenset(
    {
        "thanks",
        "thank you",
        "ok",
        "okay",
        "i see",
        "got it",
        "sure",
        "hello",
        "hi",
        "bye",
        "cool",
    }
)

_PREFERENCE_MARKERS = (
    "prefer",
    "like",
    "favorite",
    "favourite",
    "love",
    "vegetarian",
    "vegan",
)
_EPISODIC_MARKERS = (
    "every morning",
    "every evening",
    "every day",
    "every night",
    "on monday",
    "on tuesday",
    "on wednesday",
    "on thursday",
    "on friday",
    "on saturday",
    "on sunday",
    "before ",
    "after ",
    "then ",
    "first ",
    "later ",
)
_CONSTRAINT_MARKERS = ("never ", "always ", "must not", "don't ever")
_CONTEXT_MARKERS = ("working on", "project", "codename")


class AdmissionDecision(str, Enum):
    ADMITTED = "admitted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ExtractionResult:
    content: str
    memory_type: MemoryType
    importance: float
    confidence: float


@dataclass(frozen=True)
class AdmissionResult:
    decision: AdmissionDecision
    reason: str
    memory: MemoryRecord | None = None


def is_query(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return True
    if normalized.endswith("?"):
        return True
    return any(normalized.startswith(prefix) for prefix in _QUERY_STARTERS)


def is_filler(text: str) -> bool:
    normalized = text.strip().lower().rstrip(".!?")
    return normalized in _FILLER


def classify_memory_type(content: str) -> MemoryType:
    lowered = content.strip().lower()
    if is_episodic_event(content):
        return MemoryType.EPISODIC
    if any(marker in lowered for marker in _PREFERENCE_MARKERS):
        return MemoryType.PREFERENCE
    if is_routine_state(content) or is_state_transition(content):
        return MemoryType.EPISODIC
    if any(marker in lowered for marker in _EPISODIC_MARKERS):
        return MemoryType.EPISODIC
    if any(marker in lowered for marker in _CONSTRAINT_MARKERS):
        return MemoryType.CONSTRAINT
    if any(marker in lowered for marker in _CONTEXT_MARKERS):
        return MemoryType.CONTEXT
    return MemoryType.FACT


def assign_importance(memory_type: MemoryType) -> float:
    if memory_type == MemoryType.CONSTRAINT:
        return 0.85
    if memory_type == MemoryType.PREFERENCE:
        return 0.8
    if memory_type == MemoryType.EPISODIC:
        return 0.75
    if memory_type == MemoryType.FACT:
        return 0.7
    return 0.5


def extract(content: str) -> ExtractionResult | None:
    """Rule-based extraction. Returns None if not memory-worthy."""
    text = content.strip()
    if not text:
        return None
    if is_query(text):
        return None
    if is_filler(text):
        return None

    text = normalize_memory_content(text)
    if not text:
        return None

    memory_type = classify_memory_type(text)
    return ExtractionResult(
        content=text,
        memory_type=memory_type,
        importance=assign_importance(memory_type),
        confidence=1.0,
    )
