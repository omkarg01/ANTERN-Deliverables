"""M6 acceptance tests — JWT auth at HTTP boundary."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cmis.api.auth import mint_access_token
from cmis.api.server import create_app

pytestmark = pytest.mark.integration

TEST_JWT_SECRET = "test-secret-key-m6"


@pytest.fixture
def auth_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CMIS_AUTH_DISABLED", "0")
    monkeypatch.setenv("CMIS_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("CMIS_JWT_ISSUER", "cmis")
    monkeypatch.setenv("CMIS_JWT_AUDIENCE", "cmis-api")


@pytest.fixture
def api_client(auth_enabled: None, migrated_db: None, database_url: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    with TestClient(create_app()) as client:
        gateway = client.app.state.gateway
        gateway.admission.repository.truncate_all()
        yield client
        gateway.admission.repository.truncate_all()


def _token(tenant_id: str, user_id: str) -> str:
    return mint_access_token(
        tenant_id=tenant_id,
        user_id=user_id,
        secret=TEST_JWT_SECRET,
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_m6_t1_missing_token_returns_401(api_client: TestClient) -> None:
    """M6-T1: Request without bearer token → 401."""
    response = api_client.get("/api/memories")
    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "UNAUTHORIZED"


def test_m6_t1_health_unauthenticated(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_m6_t2_cross_tenant_isolation(api_client: TestClient) -> None:
    """M6-T2: Token for tenant A cannot read tenant B memories."""
    token_a = _token("tenant_a", "alice")
    token_b = _token("tenant_b", "alice")

    admit = api_client.post(
        "/api/memories",
        json={"content": "Tenant A secret preference"},
        headers=_auth_header(token_a),
    )
    assert admit.status_code == 200

    own = api_client.get("/api/memories", headers=_auth_header(token_a))
    assert own.status_code == 200
    assert own.json()["count"] == 1

    other = api_client.get("/api/memories", headers=_auth_header(token_b))
    assert other.status_code == 200
    assert other.json()["count"] == 0


def test_m6_t3_body_tenant_mismatch_rejected(api_client: TestClient) -> None:
    """M6-T3: Body tenant_id mismatch with token → 403."""
    token = _token("acme", "alice")
    response = api_client.post(
        "/api/memories",
        json={
            "content": "I prefer tea",
            "tenant_id": "other-tenant",
            "user_id": "alice",
        },
        headers=_auth_header(token),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "TENANT_ISOLATION_VIOLATION"


def test_m6_t3_query_tenant_mismatch_rejected(api_client: TestClient) -> None:
    token = _token("acme", "alice")
    response = api_client.get(
        "/api/memories?tenant_id=other-tenant&user_id=alice",
        headers=_auth_header(token),
    )
    assert response.status_code == 403


def test_m6_auth_disabled_accepts_scope_in_query(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backward compat: CMIS_AUTH_DISABLED=1 uses query/body scope without JWT."""
    monkeypatch.setenv("CMIS_AUTH_DISABLED", "1")

    with TestClient(create_app()) as client:
        gateway = client.app.state.gateway
        gateway.admission.repository.truncate_all()
        try:
            admit = client.post(
                "/api/memories",
                json={
                    "tenant_id": "acme",
                    "user_id": "alice",
                    "content": "Legacy auth path",
                },
            )
            assert admit.status_code == 200

            listed = client.get("/api/memories?tenant_id=acme&user_id=alice")
            assert listed.status_code == 200
            assert listed.json()["count"] == 1
        finally:
            gateway.admission.repository.truncate_all()
