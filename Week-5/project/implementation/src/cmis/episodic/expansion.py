"""Backward-compatible alias — use resolve_memories_for_query instead."""

from cmis.episodic.resolution import resolve_memories_for_query as expand_with_episode_links

__all__ = ["expand_with_episode_links"]
