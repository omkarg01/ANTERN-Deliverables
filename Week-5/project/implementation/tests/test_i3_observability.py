"""I3 tests — Grafana /metrics scrape surface and PostHog event hygiene."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cmis.admin.gateway import CMISGateway
from cmis.api.server import create_app
from cmis.formation.extraction import AdmissionDecision
from cmis.observability.metrics import MetricsRegistry
from cmis.observability.posthog import NullAnalytics, sanitize_properties


class RecordingAnalytics:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict]] = []

    def capture(self, event: str, *, distinct_id: str, properties: dict) -> None:
        self.events.append((event, distinct_id, dict(properties)))


def test_i3_t3_prometheus_export_includes_abstention_counter() -> None:
    registry = MetricsRegistry()
    registry.inc("admissions_total")
    registry.inc("context_abstentions_total")
    text = registry.render_prometheus()
    assert "cmis_admissions_total 1" in text
    assert "cmis_context_abstentions_total 1" in text


def test_i3_t2_sanitize_drops_memory_content() -> None:
    cleaned = sanitize_properties(
        {
            "tenant_id": "acme",
            "user_id": "alice",
            "content": "I prefer coffee",
            "query": "What do I drink?",
            "reason": "conflict with I prefer tea",
            "injected_count": 2,
            "extra_secret": "drop-me",
        }
    )
    assert cleaned == {"tenant_id": "acme", "user_id": "alice", "injected_count": 2}
    assert "content" not in cleaned
    assert "query" not in cleaned
    assert "reason" not in cleaned


def test_i3_null_analytics_is_noop() -> None:
    NullAnalytics().capture("memory_admitted", distinct_id="acme:alice", properties={"content": "nope"})


def test_i3_t2_posthog_events_omit_raw_content(db_conn, embedder) -> None:
    sink = RecordingAnalytics()
    instrumented = CMISGateway(db_conn, embedder, analytics=sink)
    instrumented.admission.repository.truncate_all()
    admitted = instrumented.admit(
        tenant_id="acme",
        user_id="alice",
        content="I prefer coffee every morning",
    )
    assert admitted.decision == AdmissionDecision.ADMITTED

    rejected = instrumented.admit(
        tenant_id="acme",
        user_id="alice",
        content="What do I drink?",
    )
    assert rejected.decision == AdmissionDecision.REJECTED

    instrumented.build_context(
        query="What color is the sky on Mars?",
        tenant_id="acme",
        user_id="alice",
    )

    names = [event for event, _, _ in sink.events]
    assert "memory_admitted" in names
    assert "memory_rejected" in names
    assert "context_abstained" in names or "context_built" in names

    dumped = str(sink.events)
    assert "I prefer coffee" not in dumped
    assert "What do I drink" not in dumped
    assert "What color is the sky" not in dumped
    for _, _, properties in sink.events:
        assert "content" not in properties
        assert "query" not in properties
        assert properties.get("tenant_id") == "acme"
        assert properties.get("user_id") == "alice"


def test_i3_t1_metrics_http_endpoint(migrated_db: None, monkeypatch) -> None:
    monkeypatch.setenv("CMIS_AUTH_DISABLED", "1")
    with TestClient(create_app()) as client:
        response = client.get("/metrics")
    assert response.status_code == 200
    assert "cmis_admissions_total" in response.text
    assert "cmis_context_abstentions_total" in response.text
    assert "text/plain" in response.headers["content-type"]
    assert "version=0.0.4" in response.headers["content-type"]
