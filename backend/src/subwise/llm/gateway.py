"""The ONLY module that talks to Ollama (blueprint C, J.1; ADR-006).

Verified against ollama==0.6.3 (docs/verified-apis.md): ``Client(host, timeout)``;
``chat(model, messages, format=<JSON schema>, options={"temperature": 0})``; server down raises
``ConnectionError``; schema output needs an Ollama server >= 0.5.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol, TypeVar

import httpx
import ollama
from pydantic import BaseModel, ValidationError

from subwise.config import Settings
from subwise.errors import LLMInvalidOutput, LLMTimeout, LLMUnavailable

T = TypeVar("T", bound=BaseModel)
log = logging.getLogger(__name__)


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
    model_name: str

    def call_structured(
        self, schema: type[T], messages: list[ChatMessage], *, timeout_s: float | None = None
    ) -> T: ...

    def call_text(self, messages: list[ChatMessage], *, timeout_s: float | None = None) -> str: ...

    def health(self) -> LLMHealth: ...


class OllamaGateway:
    """Concrete gateway over the official ``ollama`` client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = settings.ollama_model

    def _client(self, timeout_s: float | None) -> ollama.Client:
        return ollama.Client(
            host=self._settings.ollama_host, timeout=timeout_s or self._settings.llm_timeout_s
        )

    def _chat(
        self, messages: list[ChatMessage], fmt: dict[str, object] | None, timeout_s: float | None
    ) -> str:
        try:
            resp = self._client(timeout_s).chat(
                model=self.model_name,
                messages=[m.model_dump() for m in messages],
                format=fmt,
                options={"temperature": 0},
            )
        except ConnectionError as exc:
            raise LLMUnavailable(
                f"Ollama is not reachable at {self._settings.ollama_host}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeout(f"Ollama did not answer within the timeout: {exc}") from exc
        except ollama.ResponseError as exc:
            raise LLMUnavailable(f"Ollama error: {exc.error}") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"Ollama transport error: {exc}") from exc
        return resp.message.content or ""

    def call_structured(
        self, schema: type[T], messages: list[ChatMessage], *, timeout_s: float | None = None
    ) -> T:
        js = schema.model_json_schema()
        content = self._chat(messages, js, timeout_s)
        try:
            return schema.model_validate_json(content)
        except ValidationError as first:
            repair = [
                *messages,
                ChatMessage(role="assistant", content=content),
                ChatMessage(
                    role="user",
                    content="That JSON did not match the schema. Errors: "
                    + json.dumps(first.errors(include_url=False), default=str)[:1500]
                    + " Reply again with corrected JSON only.",
                ),
            ]
            content = self._chat(repair, js, timeout_s)
            try:
                return schema.model_validate_json(content)
            except ValidationError as second:
                raise LLMInvalidOutput(
                    "Model output did not match the schema twice.",
                    details={"errors": str(second)[:500]},
                ) from second

    def call_text(self, messages: list[ChatMessage], *, timeout_s: float | None = None) -> str:
        return self._chat(messages, None, timeout_s).strip()

    def health(self) -> LLMHealth:
        base = self._settings.ollama_host.rstrip("/")
        try:
            version = httpx.get(f"{base}/api/version", timeout=3).json().get("version")
            tags = httpx.get(f"{base}/api/tags", timeout=5).json().get("models", [])
        except (httpx.HTTPError, ValueError) as exc:
            return LLMHealth(reachable=False, model=self.model_name, error=str(exc))
        names = {m.get("name") for m in tags} | {m.get("model") for m in tags}
        return LLMHealth(
            reachable=True,
            server_version=version,
            model=self.model_name,
            model_present=self.model_name in names,
        )
