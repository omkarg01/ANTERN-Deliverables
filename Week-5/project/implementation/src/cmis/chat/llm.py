from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request
from uuid import UUID

from cmis.chat.models import ChatCompletion
from cmis.config import get_llm_api_key, get_llm_base_url, get_llm_model, get_llm_provider

# Groq sits behind Cloudflare; default Python-urllib UA triggers 403 / error 1010.
_HTTP_HEADERS = {
    "User-Agent": "CMIS/0.1",
    "Accept": "application/json",
}


class ChatCompletionClient(Protocol):
    def complete(self, prompt: str, *, memory_ids: tuple[UUID, ...]) -> ChatCompletion: ...


class MockChatLLM:
    """Deterministic chat LLM for tests — cites memory_ids in the answer."""

    def __init__(self, *, model: str = "mock") -> None:
        self._model = model

    def complete(self, prompt: str, *, memory_ids: tuple[UUID, ...]) -> ChatCompletion:
        del prompt
        if not memory_ids:
            return ChatCompletion(
                text="I don't have relevant memories to answer that.",
                model=self._model,
            )
        cites = ", ".join(str(memory_id) for memory_id in memory_ids)
        return ChatCompletion(
            text=f"Based on memories [{cites}]: here is my answer.",
            model=self._model,
        )


@dataclass(frozen=True)
class OpenAICompatibleChatLLM:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 60.0

    def complete(self, prompt: str, *, memory_ids: tuple[UUID, ...]) -> ChatCompletion:
        del memory_ids
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                **_HTTP_HEADERS,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"LLM API unreachable: {exc}") from exc

        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected LLM response shape: {body}") from exc

        return ChatCompletion(text=str(text).strip(), model=self.model)


def create_chat_llm() -> ChatCompletionClient:
    provider = get_llm_provider()
    if provider == "mock":
        return MockChatLLM()
    return OpenAICompatibleChatLLM(
        api_key=get_llm_api_key(),
        base_url=get_llm_base_url(),
        model=get_llm_model(),
    )
