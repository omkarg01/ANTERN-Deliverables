from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from cmis.cache.keys import build_key

if TYPE_CHECKING:
    from redis import Redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: int


class RateLimiterProtocol(Protocol):
    def check(
        self,
        *,
        tenant_id: str,
        user_id: str,
        bucket: str = "default",
    ) -> RateLimitResult: ...


_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local reset_at = now + window
  if oldest[2] then
    reset_at = tonumber(oldest[2]) + window
  end
  return {0, limit, 0, reset_at}
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, window + 1)
return {1, limit, limit - count - 1, now + window}
"""


class RateLimiter:
    """In-process sliding-window rate limiter (M5 fallback)."""

    def __init__(self, *, limit: int = 100, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def _scope_key(self, *, tenant_id: str, user_id: str, bucket: str) -> str:
        return f"{tenant_id}:{user_id}:{bucket}"

    def check(
        self,
        *,
        tenant_id: str,
        user_id: str,
        bucket: str = "default",
    ) -> RateLimitResult:
        scope = self._scope_key(tenant_id=tenant_id, user_id=user_id, bucket=bucket)
        now = time.time()
        window_start = now - self._window
        events = self._events[scope]
        while events and events[0] < window_start:
            events.popleft()

        if len(events) >= self._limit:
            reset_at = int(events[0] + self._window)
            return RateLimitResult(
                allowed=False,
                limit=self._limit,
                remaining=0,
                reset_at=reset_at,
            )

        events.append(now)
        remaining = self._limit - len(events)
        reset_at = int(now + self._window)
        return RateLimitResult(
            allowed=True,
            limit=self._limit,
            remaining=remaining,
            reset_at=reset_at,
        )


class RedisRateLimiter:
    """Distributed sliding-window rate limiter backed by Redis sorted sets."""

    def __init__(
        self,
        client: Redis,
        *,
        limit: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self._client = client
        self._limit = limit
        self._window = window_seconds
        self._script = client.register_script(_SLIDING_WINDOW_SCRIPT)

    def check(
        self,
        *,
        tenant_id: str,
        user_id: str,
        bucket: str = "default",
    ) -> RateLimitResult:
        key = build_key(tenant_id, user_id, f"rate:{bucket}")
        now = time.time()
        member = f"{now}:{time.time_ns()}"
        allowed, limit, remaining, reset_at = self._script(
            keys=[key],
            args=[now, self._window, self._limit, member],
        )
        return RateLimitResult(
            allowed=bool(allowed),
            limit=int(limit),
            remaining=max(0, int(remaining)),
            reset_at=int(reset_at),
        )


def create_rate_limiter(
    *,
    limit: int = 100,
    window_seconds: int = 60,
    redis_client: Redis | None = None,
) -> RateLimiterProtocol:
    """Factory: Redis limiter when client/url available, else in-process fallback."""
    if redis_client is not None:
        return RedisRateLimiter(redis_client, limit=limit, window_seconds=window_seconds)

    from cmis.cache.client import create_redis_client

    client = create_redis_client()
    if client is not None:
        try:
            client.ping()
        except Exception:
            return RateLimiter(limit=limit, window_seconds=window_seconds)
        return RedisRateLimiter(client, limit=limit, window_seconds=window_seconds)

    return RateLimiter(limit=limit, window_seconds=window_seconds)
