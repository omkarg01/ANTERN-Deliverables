from __future__ import annotations

import re

# Domain typo map (I4-A) — extend as scenarios grow
_TYPO_MAP: dict[str, str] = {
    "mubai": "mumbai",
    "mumbay": "mumbai",
    "vegeterian": "vegetarian",
    "vegatarian": "vegetarian",
    "vegiterian": "vegetarian",
    "resturant": "restaurant",
    "restuarnt": "restaurant",
    "restaraunt": "restaurant",
}


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def normalize_text(text: str) -> str:
    """Lowercase cleanup + whole-word typo correction (preserves hyphens, e.g. SSN)."""
    collapsed = _collapse_whitespace(text)
    if not collapsed:
        return ""
    result = collapsed.lower()
    for typo, fix in _TYPO_MAP.items():
        result = re.sub(rf"\b{re.escape(typo)}\b", fix, result)
    return result


def normalize_memory_content(content: str) -> str:
    """Canonical memory text before classify + embed (write path)."""
    return normalize_text(content)


def normalize_query(query: str) -> str:
    """Search-ready query text before FTS + dense embed (read path)."""
    return normalize_text(query)
