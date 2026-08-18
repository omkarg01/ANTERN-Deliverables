from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cmis.models import ContextBlock


@dataclass(frozen=True)
class ChatCompletion:
    text: str
    model: str


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    memory_ids: list[UUID]
    trace_id: str
    model: str
    abstention_reason: str | None
    context: ContextBlock

    @property
    def abstained(self) -> bool:
        return self.abstention_reason is not None
