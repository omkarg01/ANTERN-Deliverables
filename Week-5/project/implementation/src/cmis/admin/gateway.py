from __future__ import annotations

from uuid import UUID

import psycopg

from cmis.admin.erasure import ErasureService
from cmis.admin.errors import ContentTooLongError, InvalidMemoryTypeError, RateLimitExceededError
from cmis.admin.health import check_health
from cmis.admin.rate_limit import RateLimiterProtocol, create_rate_limiter
from cmis.cache.context_cache import ContextCache, cache_get, cache_set
from cmis.cache.client import create_redis_client
from cmis.config import get_context_cache_ttl, is_context_cache_enabled
from cmis.chat.llm import ChatCompletionClient, create_chat_llm
from cmis.chat.service import ChatService
from cmis.context.service import ContextService
from cmis.embedder import DeterministicEmbedder, Embedder
from cmis.formation.admission import AdmissionService
from cmis.formation.extraction import AdmissionDecision, AdmissionResult
from cmis.models import ActorType, MemoryType
from cmis.observability.audit import AuditLogger
from cmis.observability.metrics import MetricsRegistry
from cmis.observability.tracing import TraceContext, set_trace_id
from cmis.workflows.client import get_workflow_dispatcher
from cmis.workflows.models import WorkflowStartResult


class CMISGateway:
    """Facade wiring admission, retrieval, erasure, tracing, metrics, and rate limits."""

    MAX_CONTENT_LENGTH = 10_000

    def __init__(
        self,
        conn: psycopg.Connection,
        embedder: Embedder | None = None,
        *,
        metrics: MetricsRegistry | None = None,
        rate_limiter: RateLimiterProtocol | None = None,
        context_cache: ContextCache | None = None,
        chat_llm: ChatCompletionClient | None = None,
    ) -> None:
        self._conn = conn
        self._embedder = embedder or DeterministicEmbedder()
        self._metrics = metrics or MetricsRegistry()
        self._rate_limiter = rate_limiter or create_rate_limiter(limit=100, window_seconds=60)
        if context_cache is not None:
            self._context_cache = context_cache
        elif is_context_cache_enabled():
            redis_client = create_redis_client()
            self._context_cache = (
                ContextCache(redis_client, ttl_seconds=get_context_cache_ttl())
                if redis_client is not None
                else None
            )
        else:
            self._context_cache = None
        self._admission = AdmissionService(conn, self._embedder)
        self._context = ContextService(conn, self._embedder)
        self._erasure = ErasureService(self._admission.repository, metrics=self._metrics)
        self._audit = AuditLogger(self._admission.repository)
        self._chat = ChatService(self, chat_llm or create_chat_llm())

    @property
    def metrics(self) -> MetricsRegistry:
        return self._metrics

    @property
    def admission(self) -> AdmissionService:
        return self._admission

    @property
    def context(self) -> ContextService:
        return self._context

    @property
    def audit(self) -> AuditLogger:
        return self._audit

    @property
    def chat(self) -> ChatService:
        return self._chat

    def health(self) -> dict[str, str]:
        return check_health(self._conn)

    def metrics_prometheus(self) -> str:
        return self._metrics.render_prometheus()

    def admit(
        self,
        *,
        tenant_id: str,
        user_id: str,
        content: str,
        trace_id: str | None = None,
        source_turn_id: UUID | None = None,
        created_by: ActorType = ActorType.USER,
    ) -> AdmissionResult:
        trace = TraceContext.start() if trace_id is None else TraceContext(trace_id=trace_id)
        set_trace_id(trace.trace_id)

        rate = self._rate_limiter.check(tenant_id=tenant_id, user_id=user_id, bucket="admit")
        if not rate.allowed:
            self._metrics.inc("rate_limit_rejections_total")
            raise RateLimitExceededError(
                "Too many admit requests",
                trace_id=trace.trace_id,
            )

        if len(content) > self.MAX_CONTENT_LENGTH:
            self._metrics.inc("errors_total")
            raise ContentTooLongError(
                "Content exceeds maximum length",
                field="content",
                trace_id=trace.trace_id,
            )

        result = self._admission.admit(
            tenant_id=tenant_id,
            user_id=user_id,
            content=content,
            created_by=created_by,
            trace_id=trace.trace_id,
            source_turn_id=source_turn_id,
        )
        if result.decision == AdmissionDecision.ADMITTED and result.memory is not None:
            self._metrics.inc("admissions_total")
            self._audit.record_admission(
                memory_id=result.memory.memory_id,
                tenant_id=tenant_id,
                user_id=user_id,
                trace_id=trace.trace_id,
                source_turn_id=source_turn_id,
            )
        return result

    def build_context(
        self,
        *,
        query: str,
        tenant_id: str,
        user_id: str,
        trace_id: str | None = None,
        **kwargs,
    ):
        trace = TraceContext.start() if trace_id is None else TraceContext(trace_id=trace_id)
        set_trace_id(trace.trace_id)

        rate = self._rate_limiter.check(
            tenant_id=tenant_id,
            user_id=user_id,
            bucket="retrieve",
        )
        if not rate.allowed:
            self._metrics.inc("rate_limit_rejections_total")
            raise RateLimitExceededError(
                "Too many retrieve requests",
                trace_id=trace.trace_id,
            )

        max_tokens = int(kwargs.get("max_tokens", 2000))
        cached = cache_get(
            self._context_cache,
            self._metrics,
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            max_tokens=max_tokens,
        )
        if cached is not None:
            self._metrics.inc("context_builds_total")
            self._metrics.inc("retrievals_total")
            return cached

        block = self._context.build_context(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            **kwargs,
        )
        cache_set(
            self._context_cache,
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            max_tokens=max_tokens,
            block=block,
        )
        self._metrics.inc("context_builds_total")
        self._metrics.inc("retrievals_total")

        memory_ids = [item.memory.memory_id for item in block.memories]
        if memory_ids:
            self._audit.record_retrieval(
                tenant_id=tenant_id,
                user_id=user_id,
                query=query,
                memory_ids=memory_ids,
                trace_id=trace.trace_id,
            )
        return block

    def chat(
        self,
        *,
        query: str,
        tenant_id: str,
        user_id: str,
        trace_id: str | None = None,
        max_tokens: int = 2000,
    ):
        return self._chat.chat(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=trace_id,
            max_tokens=max_tokens,
        )

    def trigger_lifecycle_workflow(
        self,
        *,
        tenant_id: str,
        user_id: str,
        trace_id: str | None = None,
    ) -> WorkflowStartResult:
        trace = TraceContext.start() if trace_id is None else TraceContext(trace_id=trace_id)
        set_trace_id(trace.trace_id)
        return get_workflow_dispatcher().start_lifecycle(
            tenant_id=tenant_id,
            user_id=user_id,
        )

    def hard_delete(
        self,
        *,
        memory_id: UUID,
        tenant_id: str,
        user_id: str,
        trace_id: str | None = None,
    ):
        trace = TraceContext.start() if trace_id is None else TraceContext(trace_id=trace_id)
        set_trace_id(trace.trace_id)
        return self._erasure.hard_delete(
            memory_id=memory_id,
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=trace.trace_id,
        )

    @staticmethod
    def validate_memory_type(value: str, *, trace_id: str | None = None) -> MemoryType:
        try:
            return MemoryType(value)
        except ValueError as exc:
            raise InvalidMemoryTypeError(
                f"Invalid memory type: {value}",
                field="memory_type",
                trace_id=trace_id,
            ) from exc
