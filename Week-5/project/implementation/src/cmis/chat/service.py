from __future__ import annotations

from typing import TYPE_CHECKING

from cmis.chat.llm import ChatCompletionClient
from cmis.chat.models import ChatResponse
from cmis.chat.prompt import ABSTENTION_ANSWER, build_chat_prompt
from cmis.observability.tracing import TraceContext, set_trace_id

if TYPE_CHECKING:
    from cmis.admin.gateway import CMISGateway


class ChatService:
    """Stage 6: context block → LLM answer with provenance."""

    def __init__(self, gateway: CMISGateway, llm: ChatCompletionClient) -> None:
        self._gateway = gateway
        self._llm = llm

    def chat(
        self,
        *,
        query: str,
        tenant_id: str,
        user_id: str,
        trace_id: str | None = None,
        max_tokens: int = 2000,
    ) -> ChatResponse:
        trace = TraceContext.start() if trace_id is None else TraceContext(trace_id=trace_id)
        set_trace_id(trace.trace_id)

        block = self._gateway.build_context(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            max_tokens=max_tokens,
            trace_id=trace.trace_id,
        )

        memory_ids = [item.memory.memory_id for item in block.memories]
        if block.abstention_reason or not block.memories:
            reason = block.abstention_reason or "No relevant memories above threshold"
            return ChatResponse(
                answer=ABSTENTION_ANSWER,
                memory_ids=[],
                trace_id=trace.trace_id,
                model="abstain",
                abstention_reason=reason,
                context=block,
            )

        prompt = build_chat_prompt(query=query, formatted_block=block.formatted_block)
        completion = self._llm.complete(prompt, memory_ids=tuple(memory_ids))

        return ChatResponse(
            answer=completion.text,
            memory_ids=memory_ids,
            trace_id=trace.trace_id,
            model=completion.model,
            abstention_reason=None,
            context=block,
        )
