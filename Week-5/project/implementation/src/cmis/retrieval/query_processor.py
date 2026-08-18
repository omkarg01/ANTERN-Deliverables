from __future__ import annotations

from dataclasses import dataclass

from cmis.config import is_query_normalize_enabled
from cmis.formation.normalize import normalize_query


@dataclass(frozen=True)
class ProcessedQuery:
    original: str
    search_text: str


def process_query(query: str) -> ProcessedQuery:
    """Stage 1: query processing — search_text for retrieval + rerank; original kept for LLM (M7)."""
    original = query.strip()
    if not is_query_normalize_enabled() or not original:
        return ProcessedQuery(original=original, search_text=original)
    return ProcessedQuery(original=original, search_text=normalize_query(original))
