from __future__ import annotations

FULL_REPLACEMENT_KEYWORDS = (
    "no longer",
    "used to",
    "previously",
    "now prefer",
    "instead of",
)

SEQUENTIAL_PHASE_KEYWORDS = (
    "switch to",
    "switch my",
    "switched to",
    "changed to",
    "then ",
    "later",
    "in the afternoon",
    "in the evening",
    "after that",
    "every morning",
    "every evening",
    "every day",
)

COMPLEMENTARY_MARKERS = (
    "also like",
    "also enjoy",
    "sometimes",
    "as well",
)

CONTRADICTION_PAIRS: tuple[tuple[str, str], ...] = (
    ("vegetarian", "meat"),
    ("vegetarian", "steak"),
    ("vegan", "meat"),
    ("vegan", "steak"),
    ("never eat meat", "steak"),
    ("never eat meat", "grilled steak"),
)

RELATED_TOPIC_GROUPS: tuple[tuple[str, ...], ...] = (
    ("morning", "tea", "coffee", "drink", "beverage"),
    ("vegetarian", "vegan", "meat", "steak", "dinner", "eat", "food"),
    ("hobby", "hobbies", "painting", "sculpture", "favorite"),
)


def is_full_replacement(content: str) -> bool:
    lowered = content.strip().lower()
    return any(keyword in lowered for keyword in FULL_REPLACEMENT_KEYWORDS)


def is_sequential_phase(content: str) -> bool:
    lowered = content.strip().lower()
    if is_full_replacement(lowered):
        return False
    return any(keyword in lowered for keyword in SEQUENTIAL_PHASE_KEYWORDS)


def is_explicit_replacement(content: str) -> bool:
    """Alias for full replacement — sequential phases link instead of supersede (M8)."""
    return is_full_replacement(content)


def is_complementary(content: str) -> bool:
    lowered = content.strip().lower()
    return any(marker in lowered for marker in COMPLEMENTARY_MARKERS)


def detect_contradiction(content_a: str, content_b: str) -> bool:
    a = content_a.strip().lower()
    b = content_b.strip().lower()
    for left, right in CONTRADICTION_PAIRS:
        if (left in a and right in b) or (left in b and right in a):
            return True
    return _vegetarian_meat_contradiction(a, b)


def _vegetarian_meat_contradiction(a: str, b: str) -> bool:
    veg_markers = ("vegetarian", "vegan", "never eat meat")
    meat_markers = ("meat", "steak", "grilled steak")
    a_veg = any(marker in a for marker in veg_markers)
    b_veg = any(marker in b for marker in veg_markers)
    a_meat = any(marker in a for marker in meat_markers)
    b_meat = any(marker in b for marker in meat_markers)
    return (a_veg and b_meat) or (b_veg and a_meat)


def shares_topic(content_a: str, content_b: str) -> bool:
    a = content_a.strip().lower()
    b = content_b.strip().lower()
    for group in RELATED_TOPIC_GROUPS:
        a_hits = any(term in a for term in group)
        b_hits = any(term in b for term in group)
        if a_hits and b_hits:
            return True
    return False


def find_replacement_targets(
    candidate_content: str,
    active_memories: list,
) -> list:
    """Memories referenced by an explicit instead-of replacement phrase."""
    lowered = candidate_content.strip().lower()
    marker = "instead of"
    if marker not in lowered:
        return []
    target_phrase = lowered.split(marker, 1)[1].strip().rstrip(".!?")
    if not target_phrase:
        return []
    targets = []
    for memory in active_memories:
        memory_lower = memory.content.lower()
        if target_phrase in memory_lower:
            targets.append(memory)
            continue
        if any(token in memory_lower for token in target_phrase.split() if len(token) > 2):
            targets.append(memory)
    return targets


def are_related(
    content_a: str,
    content_b: str,
    *,
    similarity: float,
    similarity_threshold: float = 0.8,
) -> bool:
    if similarity >= similarity_threshold:
        return True
    if detect_contradiction(content_a, content_b):
        return True
    return shares_topic(content_a, content_b)
