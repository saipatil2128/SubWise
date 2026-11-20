# ADR-006: Use the official ollama client

Date: 2026-11-21 · Status: Accepted

## Context

The blueprint listed `ollama/langchain-ollama`. LangGraph does not need LangChain chat-model wrappers, and the gateway only needs `chat(format=schema)`.

## Decision

Use `ollama==0.6.3` directly inside `subwise/llm/gateway.py` (the only module allowed to import it). Always pass `timeout` (the client default is none). Map `ConnectionError` and httpx timeouts to `LLMUnavailable` / `LLMTimeout`.

## Consequences

+ One fewer dependency layer, and direct access to JSON-schema `format`. − No LangChain tool-calling helpers (not needed; tools are plain Python called by graph nodes).
