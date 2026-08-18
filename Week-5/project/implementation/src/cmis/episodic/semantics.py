from __future__ import annotations

from cmis.models import MemoryType

_STATE_TRANSITION_MARKERS = (
    "switched from",
    "switch from",
    "changed from",
    "instead of",
    "no longer",
    "used to",
)

_ROUTINE_MARKERS = (
    "every morning",
    "every evening",
    "every day",
    "switch to",
    "switch my",
    "switched to",
    "changed to",
)

_EPISODIC_EVENT_MARKERS = (
    "tried",
    "visited",
    "watched",
    "went to",
    "yesterday i",
    "last week i",
    "last night i",
)

_PREFERENCE_MARKERS = (
    "prefer",
    "like",
    "favorite",
    "favourite",
    "love",
)

_STATE_KEY_BY_TERMS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("morning", "tea", "coffee", "drink", "beverage", "juice", "soda", "water"), "drink"),
    (("vegetarian", "vegan", "meat", "steak", "dinner", "eat", "food", "lunch"), "food"),
    (("hobby", "hobbies", "painting", "sculpture"), "hobby"),
)

_TOPIC_GROUPS: tuple[tuple[str, ...], ...] = tuple(terms for terms, _ in _STATE_KEY_BY_TERMS) + (
    ("hobby", "hobbies", "painting", "sculpture", "favorite"),
)


def shares_topic(content_a: str, content_b: str) -> bool:
    a = content_a.strip().lower()
    b = content_b.strip().lower()
    for group in _TOPIC_GROUPS:
        a_hits = any(term in a for term in group)
        b_hits = any(term in b for term in group)
        if a_hits and b_hits:
            return True
    return False


def infer_state_key(content: str) -> str:
    lowered = content.strip().lower()
    for terms, key in _STATE_KEY_BY_TERMS:
        if any(term in lowered for term in terms):
            return key
    if is_preference_state(content):
        return "preference"
    return "general"


def infer_query_state_keys(query: str) -> tuple[str, ...]:
    lowered = query.strip().lower()
    keys = [key for terms, key in _STATE_KEY_BY_TERMS if any(term in lowered for term in terms)]
    if is_preference_state(query) or "prefer" in lowered:
        keys.append("preference")
    return tuple(dict.fromkeys(keys))


def is_episodic_event(content: str) -> bool:
    """One-off experience — not an evolving preference or routine state."""
    lowered = content.strip().lower()
    if any(marker in lowered for marker in _ROUTINE_MARKERS):
        return False
    if is_preference_state(content) and not any(
        marker in lowered for marker in _EPISODIC_EVENT_MARKERS
    ):
        return False
    return any(marker in lowered for marker in _EPISODIC_EVENT_MARKERS)


def is_preference_state(content: str) -> bool:
    lowered = content.strip().lower()
    return any(marker in lowered for marker in _PREFERENCE_MARKERS)


def is_routine_state(content: str) -> bool:
    lowered = content.strip().lower()
    return any(marker in lowered for marker in _ROUTINE_MARKERS)


def is_state_transition(content: str) -> bool:
    lowered = content.strip().lower()
    if is_episodic_event(content):
        return False
    if any(marker in lowered for marker in _STATE_TRANSITION_MARKERS):
        return True
    return is_routine_state(content) and ("switch" in lowered or "changed" in lowered)


def uses_explicit_from_transition(content: str) -> bool:
    lowered = content.strip().lower()
    return any(
        marker in lowered
        for marker in ("switched from", "switch from", "changed from", "instead of")
    )


def _is_state_bearing_memory(content: str, memory_type: MemoryType) -> bool:
    if is_episodic_event(content):
        return False
    if memory_type == MemoryType.PREFERENCE:
        return True
    if memory_type == MemoryType.CONSTRAINT:
        return True
    return is_preference_state(content) or is_routine_state(content)


def valid_state_transition(
    candidate_content: str,
    prior_content: str,
    *,
    candidate_type: MemoryType,
    prior_type: MemoryType,
) -> bool:
    """True when candidate evidence supports changing the same state domain."""
    if is_episodic_event(prior_content):
        return False
    if not _is_state_bearing_memory(prior_content, prior_type):
        return False
    if is_episodic_event(candidate_content):
        return False
    if not is_state_transition(candidate_content):
        return False
    if infer_state_key(candidate_content) != infer_state_key(prior_content):
        if not shares_topic(candidate_content, prior_content):
            return False
    return shares_topic(candidate_content, prior_content) or infer_state_key(
        candidate_content
    ) == infer_state_key(prior_content)


def valid_temporal_relationship(
    prior_content: str,
    later_content: str,
    *,
    prior_type: MemoryType,
    later_type: MemoryType,
) -> bool:
    """Follow a stored temporal edge only when semantics support same evolving state."""
    return valid_state_transition(
        later_content,
        prior_content,
        candidate_type=later_type,
        prior_type=prior_type,
    )
