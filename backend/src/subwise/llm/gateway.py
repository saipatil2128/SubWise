"""The ONLY module that talks to Ollama (blueprint C, J.1). Implementation: M7.

Verified against ollama==0.6.3 (docs/verified-apis.md):
  client = ollama.Client(host=settings.ollama_host, timeout=settings.llm_timeout_s)
      # the client's default timeout is None (wait forever) - always pass one
  resp = client.chat(model=..., messages=[...], format=Schema.model_json_schema(),
                     options={"temperature": 0})
  Schema.model_validate_json(resp.message.content)
  errors: ollama.ResponseError (HTTP error from server), ollama.RequestError (bad request),
          httpx.ConnectError / httpx.TimeoutException (server down / slow)
Structured outputs (dict schema in ``format``) need an Ollama SERVER >= 0.5; scripts/check_env.py
prints the server version.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from subwise.config import Settings
from subwise.errors import NotImplementedYet

T = TypeVar("T", bound=BaseModel)


class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMHealth(BaseModel):
    reachable: bool
    server_version: str | None = None
    model: str
    model_present: bool = False
    error: str | None = None


class LLMGateway(Protocol):
    def call_structured(
        self, schema: type[T], messages: list[ChatMessage], *, timeout_s: float | None = None
    ) -> T:
        """Return a validated instance of ``schema``. One repair retry on invalid JSON, then
        raise ``LLMInvalidOutput``. Raise ``LLMUnavailable``/``LLMTimeout`` on transport errors."""
        ...

    def call_text(self, messages: list[ChatMessage], *, timeout_s: float | None = None) -> str: ...

    def health(self) -> LLMHealth: ...


class OllamaGateway:
    """Concrete gateway over the official ``ollama`` Python client (ADR-006)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def call_structured(
        self, schema: type[T], messages: list[ChatMessage], *, timeout_s: float | None = None
    ) -> T:
        raise NotImplementedYet("M7", "OllamaGateway.call_structured")

    def call_text(self, messages: list[ChatMessage], *, timeout_s: float | None = None) -> str:
        raise NotImplementedYet("M7", "OllamaGateway.call_text")

    def health(self) -> LLMHealth:
        raise NotImplementedYet("M7", "OllamaGateway.health")
