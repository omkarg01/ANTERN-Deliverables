from __future__ import annotations

from cmis.config import EMBEDDING_DIM, get_relevance_threshold
from cmis.embedder import BGEEmbedder, DeterministicEmbedder, create_embedder, embed_query


def test_create_embedder_defaults_to_deterministic(monkeypatch) -> None:
    monkeypatch.delenv("CMIS_EMBEDDER", raising=False)
    embedder = create_embedder()
    assert isinstance(embedder, DeterministicEmbedder)
    assert len(embedder.embed("hello world")) == EMBEDDING_DIM


def test_create_embedder_bge_kind(monkeypatch) -> None:
    monkeypatch.setenv("CMIS_EMBEDDER", "bge")
    embedder = create_embedder()
    assert isinstance(embedder, BGEEmbedder)


def test_embed_query_uses_bge_prefix(monkeypatch) -> None:
    calls: list[str] = []

    class StubBGE:
        model_name = "stub-bge"

        def embed(self, text: str) -> list[float]:
            calls.append(text)
            return [1.0, 0.0]

        def embed_query(self, query: str) -> list[float]:
            calls.append(f"query:{query}")
            return [0.0, 1.0]

    stub = StubBGE()
    doc = embed_query(stub, "what do I drink?")
    assert doc == [0.0, 1.0]
    assert calls == ["query:what do I drink?"]


def test_embed_query_falls_back_to_embed() -> None:
    embedder = DeterministicEmbedder()
    a = embedder.embed("test query")
    b = embed_query(embedder, "test query")
    assert a == b


def test_bge_relevance_threshold_default(monkeypatch) -> None:
    monkeypatch.setenv("CMIS_EMBEDDER", "bge")
    monkeypatch.delenv("CMIS_RELEVANCE_THRESHOLD", raising=False)
    assert get_relevance_threshold() == 0.62


def test_deterministic_relevance_threshold_default(monkeypatch) -> None:
    monkeypatch.setenv("CMIS_EMBEDDER", "deterministic")
    monkeypatch.delenv("CMIS_RELEVANCE_THRESHOLD", raising=False)
    assert get_relevance_threshold() == 0.3
