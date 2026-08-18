"""I2 acceptance tests — Redis cache and distributed rate limiting."""

from __future__ import annotations

import os
import uuid

import pytest

from cmis.admin.errors import RateLimitExceededError
from cmis.admin.gateway import CMISGateway
from cmis.admin.rate_limit import RedisRateLimiter, create_rate_limiter
from cmis.cache.client import create_redis_client, redis_available
from cmis.cache.keys import build_key
from cmis.formation.extraction import AdmissionDecision

pytestmark = pytest.mark.redis


@pytest.fixture(scope="module")
def redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="module")
def redis_client(redis_url: str):
    if not redis_available(url=redis_url):
        pytest.skip(
            "Redis unavailable — start Docker: "
            "docker compose -f implementation/docker-compose.yml up -d redis"
        )
    client = create_redis_client(url=redis_url)
    assert client is not None
    yield client
    client.flushdb()


@pytest.fixture
def redis_rate_limiter(redis_client) -> RedisRateLimiter:
    return RedisRateLimiter(redis_client, limit=3, window_seconds=60)


def test_i2_t1_rate_limit_shared_across_instances(
    db_conn,
    embedder,
    redis_client,
) -> None:
    """Two limiter instances share the same Redis bucket (simulates two API replicas)."""
    instance_a = RedisRateLimiter(redis_client, limit=3, window_seconds=60)
    instance_b = RedisRateLimiter(redis_client, limit=3, window_seconds=60)

    for index in range(3):
        result = instance_a.check(tenant_id="acme", user_id="alice", bucket="admit")
        assert result.allowed, f"request {index} should be allowed on instance A"

    blocked = instance_b.check(tenant_id="acme", user_id="alice", bucket="admit")
    assert not blocked.allowed
    assert blocked.remaining == 0


def test_i2_t2_tenant_scoped_redis_keys(
    db_conn,
    embedder,
    redis_client,
) -> None:
    """Same user in different tenants gets independent rate-limit buckets."""
    limiter = RedisRateLimiter(redis_client, limit=2, window_seconds=60)

    for _ in range(2):
        assert limiter.check(tenant_id="acme", user_id="alice", bucket="admit").allowed

    acme_blocked = limiter.check(tenant_id="acme", user_id="alice", bucket="admit")
    assert not acme_blocked.allowed

    beta_allowed = limiter.check(tenant_id="beta", user_id="alice", bucket="admit")
    assert beta_allowed.allowed

    assert build_key("acme", "alice", "rate:admit") != build_key("beta", "alice", "rate:admit")


def test_i2_t3_gateway_uses_redis_limiter_when_configured(
    db_conn,
    embedder,
    redis_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gateway wired with Redis limiter rejects after shared threshold."""
    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    limiter = create_rate_limiter(limit=2, window_seconds=60, redis_client=redis_client)
    gateway = CMISGateway(
        db_conn,
        embedder,
        rate_limiter=limiter,
        context_cache=None,
    )
    gateway.admission.repository.truncate_all()

    for index in range(2):
        result = gateway.admit(
            tenant_id="acme",
            user_id="bob",
            content=f"Redis gateway memory {index}",
        )
        assert result.decision == AdmissionDecision.ADMITTED

    with pytest.raises(RateLimitExceededError):
        gateway.admit(
            tenant_id="acme",
            user_id="bob",
            content="Should hit distributed limit",
        )


def test_i2_context_cache_hit_metrics(
    db_conn,
    embedder,
    redis_client,
) -> None:
    """Context cache records hit/miss metrics with tenant-scoped keys."""
    from cmis.cache.context_cache import ContextCache
    from cmis.models import MemoryCreate
    from cmis.observability.metrics import MetricsRegistry

    cache = ContextCache(redis_client, ttl_seconds=60)
    metrics = MetricsRegistry()
    gateway = CMISGateway(
        db_conn,
        embedder,
        context_cache=cache,
        metrics=metrics,
    )
    repo = gateway.admission.repository
    repo.truncate_all()
    repo.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I prefer morning tea over coffee",
        )
    )

    first = gateway.build_context(
        query="morning drink preference",
        tenant_id="acme",
        user_id="alice",
    )
    second = gateway.build_context(
        query="morning drink preference",
        tenant_id="acme",
        user_id="alice",
    )

    assert first.formatted_block == second.formatted_block
    assert metrics.cache_misses_total == 1
    assert metrics.cache_hits_total == 1

    key_prefix = build_key("acme", "alice", "ctx:")
    keys = [key for key in redis_client.scan_iter(match=f"{key_prefix}*")]
    assert len(keys) == 1


def test_i2_keys_include_unique_request_members(redis_client) -> None:
    """Concurrent requests use unique sorted-set members (no ZADD collisions)."""
    limiter = RedisRateLimiter(redis_client, limit=10, window_seconds=60)
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    user = f"user-{uuid.uuid4().hex[:8]}"

    for _ in range(5):
        assert limiter.check(tenant_id=tenant, user_id=user, bucket="probe").allowed

    key = build_key(tenant, user, "rate:probe")
    assert redis_client.zcard(key) == 5
