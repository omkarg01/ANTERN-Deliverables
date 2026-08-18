from __future__ import annotations

from typing import TYPE_CHECKING

from cmis.config import get_redis_url

if TYPE_CHECKING:
    from redis import Redis


def create_redis_client(*, url: str | None = None) -> Redis | None:
    """Return a Redis client when REDIS_URL is configured, else None."""
    resolved = (url or get_redis_url()).strip()
    if not resolved:
        return None
    try:
        import redis
    except ImportError as exc:
        raise RuntimeError(
            "redis package required when REDIS_URL is set — pip install cmis[redis]"
        ) from exc
    return redis.Redis.from_url(resolved, decode_responses=True)


def redis_available(*, url: str | None = None) -> bool:
    client = create_redis_client(url=url)
    if client is None:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False
