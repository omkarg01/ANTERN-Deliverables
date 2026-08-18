from __future__ import annotations

_TEMPORAL_QUERY_MARKERS = (
    "before",
    "after",
    "then",
    "earlier",
    "later",
    "first",
    "morning",
    "afternoon",
    "evening",
    "previously",
    "next",
)


def has_temporal_intent(query: str) -> bool:
    """True when the query asks about order or routine timing (M8 read path)."""
    lowered = query.strip().lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in _TEMPORAL_QUERY_MARKERS)
