from __future__ import annotations

KEY_PREFIX = "cmis"


def build_key(tenant_id: str, user_id: str, suffix: str) -> str:
    """Tenant-scoped Redis key: cmis:{tenant_id}:{user_id}:{suffix}."""
    return f"{KEY_PREFIX}:{tenant_id}:{user_id}:{suffix}"
