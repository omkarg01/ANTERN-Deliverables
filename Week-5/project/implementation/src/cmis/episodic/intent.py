from __future__ import annotations

from enum import Enum

_HISTORICAL_MARKERS = (
    "before",
    "after",
    "first",
    "then",
    "earlier",
    "previously",
    "when did",
    "what happened",
)

_CURRENT_STATE_MARKERS = (
    "currently",
    "current",
    "these days",
    "right now",
    "what do i prefer",
    "what do i drink",
    "what do i eat",
    "what is my preference",
)


class QueryIntent(str, Enum):
    CURRENT_STATE = "current_state"
    HISTORICAL = "historical"
    NEUTRAL = "neutral"


def classify_query_intent(query: str) -> QueryIntent:
    """Route read path: canonical state vs validated historical expansion."""
    lowered = query.strip().lower()
    if not lowered:
        return QueryIntent.NEUTRAL

    if any(marker in lowered for marker in _HISTORICAL_MARKERS):
        return QueryIntent.HISTORICAL

    if any(marker in lowered for marker in _CURRENT_STATE_MARKERS):
        return QueryIntent.CURRENT_STATE

    if "prefer" in lowered and "before" not in lowered and "after" not in lowered:
        return QueryIntent.CURRENT_STATE

    routine_current = ("morning", "afternoon", "evening", "every day")
    if any(marker in lowered for marker in routine_current):
        return QueryIntent.CURRENT_STATE

    if lowered.startswith("what do i ") and "before" not in lowered and "after" not in lowered:
        return QueryIntent.CURRENT_STATE

    return QueryIntent.NEUTRAL
