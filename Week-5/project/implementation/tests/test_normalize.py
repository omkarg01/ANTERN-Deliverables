"""Unit tests for I4-A text normalization."""

from __future__ import annotations

from cmis.formation.extraction import extract
from cmis.formation.normalize import normalize_query, normalize_text
from cmis.models import MemoryType


def test_normalize_fixes_vegeterian_typo() -> None:
    assert "vegetarian" in normalize_text("I am vegeterian")


def test_normalize_fixes_mubai_typo() -> None:
    assert normalize_query("restaurant in Mubai") == "restaurant in mumbai"


def test_extract_classifies_normalized_vegeterian_as_preference() -> None:
    result = extract("I am vegeterian")
    assert result is not None
    assert result.content == "i am vegetarian"
    assert result.memory_type == MemoryType.PREFERENCE
    assert result.importance == 0.8
