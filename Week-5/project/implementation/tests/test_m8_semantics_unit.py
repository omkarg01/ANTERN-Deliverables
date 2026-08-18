"""Unit tests for M8 episodic semantics — no database."""

from __future__ import annotations

from cmis.episodic.intent import QueryIntent, classify_query_intent
from cmis.episodic.semantics import (
    is_episodic_event,
    is_preference_state,
    is_state_transition,
    valid_state_transition,
)
from cmis.models import MemoryType


def test_episodic_event_not_state_transition() -> None:
    assert is_episodic_event("Yesterday I tried coffee.")
    assert not is_state_transition("Yesterday I tried coffee.")


def test_preference_is_state_bearing() -> None:
    assert is_preference_state("I prefer tea.")
    assert valid_state_transition(
        "I switched from tea to coffee.",
        "I prefer tea.",
        candidate_type=MemoryType.EPISODIC,
        prior_type=MemoryType.PREFERENCE,
    )


def test_tried_coffee_not_valid_transition_from_tea() -> None:
    assert not valid_state_transition(
        "Yesterday I tried coffee.",
        "I prefer tea.",
        candidate_type=MemoryType.EPISODIC,
        prior_type=MemoryType.PREFERENCE,
    )


def test_query_intent_routing() -> None:
    assert classify_query_intent("What do I prefer?") == QueryIntent.CURRENT_STATE
    assert classify_query_intent("What did I prefer before tea?") == QueryIntent.HISTORICAL
    assert classify_query_intent("What is my favorite color?") == QueryIntent.NEUTRAL
