from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

from cmis.admin.gateway import CMISGateway
from cmis.config import get_database_url
from cmis.context.service import ContextService
from cmis.embedder import DeterministicEmbedder
from cmis.formation.admission import AdmissionService
from cmis.retrieval.service import RetrievalService
from cmis.storage.repository import MemoryRepository

IMPLEMENTATION_ROOT = Path(__file__).resolve().parent.parent
MIGRATE_SCRIPT = IMPLEMENTATION_ROOT / "scripts" / "migrate.py"


@pytest.fixture(autouse=True)
def _retrieval_test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep M1–M5 regression stable: passthrough rerank unless a test overrides."""
    monkeypatch.setenv("CMIS_RERANKER", "off")
    monkeypatch.setenv("CMIS_EMBEDDER", "deterministic")
    monkeypatch.setenv("CMIS_RELEVANCE_THRESHOLD", "0.3")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("CMIS_CONTEXT_CACHE", "0")
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)


def _postgres_available(url: str) -> bool:
    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.OperationalError:
        return False


def _ensure_migrations() -> None:
    import os

    url = os.environ.get("DATABASE_URL", get_database_url())
    if not _postgres_available(url):
        pytest.skip(
            "Postgres unavailable — start Docker: "
            "docker compose -f implementation/docker-compose.yml up -d"
        )

    env = os.environ.copy()
    env.setdefault("DATABASE_URL", url)
    result = subprocess.run(
        [sys.executable, str(MIGRATE_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    if result.returncode != 0:
        pytest.skip(f"Postgres unavailable or migration failed:\n{result.stderr}")


@pytest.fixture(scope="session")
def database_url() -> str:
    return get_database_url()


@pytest.fixture(scope="session")
def migrated_db(database_url: str) -> None:
    _ensure_migrations()


@pytest.fixture
def db_conn(migrated_db: None, database_url: str):
    conn = psycopg.connect(database_url, autocommit=False, connect_timeout=5)
    yield conn
    conn.close()


@pytest.fixture
def embedder() -> DeterministicEmbedder:
    return DeterministicEmbedder()


@pytest.fixture
def repo(db_conn, embedder) -> MemoryRepository:
    repository = MemoryRepository(db_conn, embedder)
    repository.truncate_all()
    yield repository
    repository.truncate_all()


@pytest.fixture
def retrieval(db_conn, embedder) -> RetrievalService:
    service = RetrievalService(db_conn, embedder)
    service.repository.truncate_all()
    yield service
    service.repository.truncate_all()


@pytest.fixture
def admission(db_conn, embedder) -> AdmissionService:
    service = AdmissionService(db_conn, embedder)
    service.repository.truncate_all()
    yield service
    service.repository.truncate_all()


@pytest.fixture
def context_service(db_conn, embedder) -> ContextService:
    service = ContextService(db_conn, embedder)
    service.retrieval.repository.truncate_all()
    yield service
    service.retrieval.repository.truncate_all()


@pytest.fixture
def gateway(db_conn, embedder) -> CMISGateway:
    service = CMISGateway(db_conn, embedder)
    service.admission.repository.truncate_all()
    yield service
    service.admission.repository.truncate_all()
