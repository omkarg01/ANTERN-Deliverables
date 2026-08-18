from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Protocol

from cmis.config import get_posthog_api_key, get_posthog_host

logger = logging.getLogger("cmis.posthog")

ALLOWED_PROPERTY_KEYS = frozenset(
    {
        "tenant_id",
        "user_id",
        "trace_id",
        "decision",
        "injected_count",
        "abstained",
    }
)
BLOCKED_PROPERTY_KEYS = frozenset(
    {
        "content",
        "query",
        "text",
        "memory",
        "formatted_block",
        "reason",
        "abstention_reason",
    }
)


class AnalyticsClient(Protocol):
    def capture(self, event: str, *, distinct_id: str, properties: dict[str, Any]) -> None: ...


def sanitize_properties(properties: dict[str, Any]) -> dict[str, Any]:
    """Keep only non-PII product fields. Never include memory content or queries."""
    cleaned: dict[str, Any] = {}
    for key, value in properties.items():
        lowered = key.lower()
        if lowered in BLOCKED_PROPERTY_KEYS:
            continue
        if lowered not in ALLOWED_PROPERTY_KEYS:
            continue
        cleaned[key] = value
    return cleaned


class NullAnalytics:
    def capture(self, event: str, *, distinct_id: str, properties: dict[str, Any]) -> None:
        return None


class PostHogClient:
    """HTTP capture client. Failures are logged and swallowed so product analytics never block CMIS."""

    def __init__(self, *, api_key: str, host: str, timeout_seconds: float = 2.0) -> None:
        self._api_key = api_key
        self._host = host.rstrip("/")
        self._timeout = timeout_seconds

    def capture(self, event: str, *, distinct_id: str, properties: dict[str, Any]) -> None:
        payload = {
            "api_key": self._api_key,
            "event": event,
            "distinct_id": distinct_id,
            "properties": sanitize_properties(properties),
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._host}/capture/",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("PostHog capture failed for %s: %s", event, exc)


def create_analytics_client() -> AnalyticsClient:
    api_key = get_posthog_api_key()
    if not api_key:
        return NullAnalytics()
    return PostHogClient(api_key=api_key, host=get_posthog_host())


def distinct_id_for(tenant_id: str, user_id: str) -> str:
    return f"{tenant_id}:{user_id}"
