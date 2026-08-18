"""M7 acceptance tests — LLM chat orchestration (stage 6)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cmis.api.auth import mint_access_token
from cmis.api.server import create_app
from cmis.chat.prompt import ABSTENTION_ANSWER

pytestmark = pytest.mark.integration

TEST_JWT_SECRET = "test-secret-key-m7"


@pytest.fixture
def m7_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CMIS_AUTH_DISABLED", "0")
    monkeypatch.setenv("CMIS_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("CMIS_JWT_ISSUER", "cmis")
    monkeypatch.setenv("CMIS_JWT_AUDIENCE", "cmis-api")
    monkeypatch.setenv("CMIS_LLM_PROVIDER", "mock")
    monkeypatch.setenv("CMIS_EMBEDDER", "deterministic")
    monkeypatch.setenv("CMIS_RELEVANCE_THRESHOLD", "0.3")
    monkeypatch.setenv("CMIS_RERANKER", "off")


@pytest.fixture
def api_client(m7_env: None, migrated_db: None, database_url: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    with TestClient(create_app()) as client:
        gateway = client.app.state.gateway
        gateway.admission.repository.truncate_all()
        yield client
        gateway.admission.repository.truncate_all()


def _token(tenant_id: str = "acme", user_id: str = "alice") -> str:
    return mint_access_token(
        tenant_id=tenant_id,
        user_id=user_id,
        secret=TEST_JWT_SECRET,
    )


def _auth(token: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token or _token()}"}


def test_m7_t1_chat_cites_injected_memories(api_client: TestClient) -> None:
    """M7-T1: Chat response memory_ids match injected context memories."""
    admit = api_client.post(
        "/api/memories",
        json={"content": "I prefer oat milk in my coffee every morning"},
        headers=_auth(),
    )
    assert admit.status_code == 200
    memory_id = admit.json()["memory"]["memory_id"]

    response = api_client.post(
        "/api/chat",
        json={"query": "What milk do I like in coffee?"},
        headers=_auth(),
    )
    assert response.status_code == 200
    body = response.json()
    assert memory_id in body["memory_ids"]
    assert memory_id in body["answer"]
    assert body["abstained"] is False
    assert body["context"]["injected_count"] >= 1


def test_m7_t2_abstention_returns_explicit_no_memory_behavior(api_client: TestClient) -> None:
    """M7-T2: Unrelated query abstains without citing memories."""
    gateway = api_client.app.state.gateway
    from cmis.models import MemoryCreate, MemoryType

    gateway.admission.repository.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="I like cooking pasta with garlic and olive oil",
            memory_type=MemoryType.FACT,
            importance=0.1,
        )
    )
    gateway.admission.repository.create_memory(
        MemoryCreate(
            tenant_id="acme",
            user_id="alice",
            content="My cat is named Whiskers and sleeps on the couch",
            memory_type=MemoryType.FACT,
            importance=0.1,
        )
    )

    response = api_client.post(
        "/api/chat",
        json={"query": "quantum mechanics wave function collapse"},
        headers=_auth(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["memory_ids"] == []
    assert body["answer"] == ABSTENTION_ANSWER
    assert body["abstention_reason"] is not None
    assert body["model"] == "abstain"


def test_m7_t3_f01_no_pii_in_unrelated_chat(api_client: TestClient) -> None:
    """M7-T3: F-01 regression — SSN memory not leaked in hobbies chat."""
    api_client.post(
        "/api/memories",
        json={"content": "My SSN is 123-45-6789"},
        headers=_auth(),
    )
    api_client.post(
        "/api/memories",
        json={"content": "I enjoy hiking on weekends"},
        headers=_auth(),
    )

    response = api_client.post(
        "/api/chat",
        json={"query": "What are my hobbies?"},
        headers=_auth(),
    )
    assert response.status_code == 200
    body = response.json()
    answer_lower = body["answer"].lower()
    assert "ssn" not in answer_lower
    assert "123-45-6789" not in body["answer"]
    injected_text = " ".join(
        item["memory"]["content"] for item in body["context"]["memories"]
    ).lower()
    assert "ssn" not in injected_text
    assert any("hiking" in item["memory"]["content"].lower() for item in body["context"]["memories"])


def test_m7_chat_requires_auth(api_client: TestClient) -> None:
    response = api_client.post("/api/chat", json={"query": "hello"})
    assert response.status_code == 401
