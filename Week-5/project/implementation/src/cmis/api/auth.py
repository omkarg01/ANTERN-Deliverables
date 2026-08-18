from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi.security import HTTPAuthorizationCredentials

from cmis.admin.errors import TenantIsolationViolationError, UnauthorizedError
from cmis.config import (
    get_jwt_audience,
    get_jwt_issuer,
    get_jwt_secret,
    is_auth_disabled,
)

DEFAULT_SCOPES = frozenset({"memory:read", "memory:write", "memory:admin"})
READ_SCOPES = frozenset({"memory:read", "memory:write", "memory:admin"})
WRITE_SCOPES = frozenset({"memory:write", "memory:admin"})


@dataclass(frozen=True)
class RequestScope:
    tenant_id: str
    user_id: str
    scopes: frozenset[str]


def mint_access_token(
    *,
    tenant_id: str,
    user_id: str,
    secret: str | None = None,
    issuer: str | None = None,
    audience: str | None = None,
    expires_in: timedelta = timedelta(hours=24),
    scopes: frozenset[str] | None = None,
) -> str:
    """Create a signed JWT for dev/tests."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "scopes": sorted(scopes or DEFAULT_SCOPES),
        "iss": issuer or get_jwt_issuer(),
        "aud": audience or get_jwt_audience(),
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, secret or get_jwt_secret(), algorithm="HS256")


def decode_access_token(token: str) -> RequestScope:
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=["HS256"],
            audience=get_jwt_audience(),
            issuer=get_jwt_issuer(),
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError(f"Invalid bearer token: {exc}") from exc

    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")
    if not tenant_id or not user_id:
        raise UnauthorizedError("Token missing tenant_id or user_id claims")

    raw_scopes = payload.get("scopes", [])
    if isinstance(raw_scopes, str):
        scopes = frozenset(scope.strip() for scope in raw_scopes.split(",") if scope.strip())
    elif isinstance(raw_scopes, list):
        scopes = frozenset(str(scope) for scope in raw_scopes)
    else:
        scopes = DEFAULT_SCOPES

    return RequestScope(
        tenant_id=str(tenant_id),
        user_id=str(user_id),
        scopes=scopes,
    )


def _scope_from_bypass(
    *,
    query_tenant: str | None,
    query_user: str | None,
    body_tenant: str | None,
    body_user: str | None,
) -> RequestScope:
    tenant_id = query_tenant or body_tenant
    user_id = query_user or body_user
    if not tenant_id or not user_id:
        raise UnauthorizedError("tenant_id and user_id are required when auth is disabled")
    return RequestScope(tenant_id=tenant_id, user_id=user_id, scopes=DEFAULT_SCOPES)


def _assert_scope_alignment(
    scope: RequestScope,
    *,
    query_tenant: str | None,
    query_user: str | None,
    body_tenant: str | None,
    body_user: str | None,
) -> None:
    if query_tenant is not None and query_tenant != scope.tenant_id:
        raise TenantIsolationViolationError(
            "Query tenant_id does not match authenticated tenant",
        )
    if query_user is not None and query_user != scope.user_id:
        raise TenantIsolationViolationError(
            "Query user_id does not match authenticated user",
        )
    if body_tenant is not None and body_tenant != scope.tenant_id:
        raise TenantIsolationViolationError(
            "Request tenant_id does not match authenticated tenant",
        )
    if body_user is not None and body_user != scope.user_id:
        raise TenantIsolationViolationError(
            "Request user_id does not match authenticated user",
        )


def resolve_scope(
    credentials: HTTPAuthorizationCredentials | None,
    *,
    query_tenant: str | None = None,
    query_user: str | None = None,
    body_tenant: str | None = None,
    body_user: str | None = None,
    required_scopes: frozenset[str] | None = None,
) -> RequestScope:
    if is_auth_disabled():
        return _scope_from_bypass(
            query_tenant=query_tenant,
            query_user=query_user,
            body_tenant=body_tenant,
            body_user=body_user,
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing bearer token")

    scope = decode_access_token(credentials.credentials)
    _assert_scope_alignment(
        scope,
        query_tenant=query_tenant,
        query_user=query_user,
        body_tenant=body_tenant,
        body_user=body_user,
    )

    if required_scopes and not scope.scopes.intersection(required_scopes):
        raise UnauthorizedError("Token missing required scope for this operation")

    return scope


def require_scope(scope: RequestScope, allowed: frozenset[str]) -> None:
    if not scope.scopes.intersection(allowed):
        raise UnauthorizedError("Token missing required scope for this operation")
