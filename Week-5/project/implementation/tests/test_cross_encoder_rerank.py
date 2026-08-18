"""Cross-encoder rerank score normalization — single-candidate regression."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cmis.models import MemoryRecord, MemoryStatus, MemoryType, SensitivityLevel
from cmis.rerank.cross_encoder import normalize_rerank_scores


def _memory(*, content: str, similarity: float) -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        memory_id=uuid4(),
        tenant_id="acme",
        user_id="alice",
        content=content,
        memory_type=MemoryType.PREFERENCE,
        status=MemoryStatus.ACTIVE,
        importance=0.8,
        confidence=1.0,
        embedding_model="test",
        contains_pii=False,
        sensitivity_level=SensitivityLevel.INTERNAL,
        created_at=now,
        similarity=similarity,
    )


def test_single_candidate_preserves_dense_similarity() -> None:
    """One memory must not get similarity=0 after min-max normalization."""
    memory = _memory(content="I prefer coffee every morning", similarity=0.82)
    ranked = normalize_rerank_scores([(memory, 4.5)])

    assert len(ranked) == 1
    assert ranked[0].similarity == 0.82


def test_two_candidates_min_max_spreads_scores() -> None:
    high = _memory(content="coffee morning", similarity=0.7)
    low = _memory(content="unrelated hiking", similarity=0.3)
    ranked = normalize_rerank_scores([(high, 5.0), (low, 1.0)])

    assert ranked[0].similarity == 1.0
    assert ranked[1].similarity == 0.0


def test_tied_raw_scores_preserve_dense_similarity() -> None:
    a = _memory(content="coffee", similarity=0.9)
    b = _memory(content="tea", similarity=0.4)
    ranked = normalize_rerank_scores([(a, 3.0), (b, 3.0)])

    assert ranked[0].similarity == 0.9
    assert ranked[1].similarity == 0.4
