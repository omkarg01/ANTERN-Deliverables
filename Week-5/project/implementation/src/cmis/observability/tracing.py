from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)

logger = logging.getLogger("cmis")


def new_trace_id() -> str:
    return str(uuid4())


def set_trace_id(trace_id: str) -> None:
    _trace_id.set(trace_id)


def get_trace_id() -> str | None:
    return _trace_id.get()


@dataclass(frozen=True)
class TraceContext:
    trace_id: str

    @classmethod
    def start(cls) -> TraceContext:
        trace_id = new_trace_id()
        set_trace_id(trace_id)
        return cls(trace_id=trace_id)


def log_structured(event: str, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        "trace_id": get_trace_id(),
        **fields,
    }
    logger.info(json.dumps(payload, default=str))
