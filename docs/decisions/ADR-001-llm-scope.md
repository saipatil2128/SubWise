# ADR-001: LLM scope

Date: 2026-11-21 · Status: Accepted

## Context

The local model (Qwen 2.5 3B via Ollama) is small, slow on CPU, and can hallucinate numbers.

## Decision

The LLM is used in exactly three graph nodes: `parse_intent` (text → `RequestSpec` via JSON schema), `decide` (choose among guard-allowed `NextAction`s), and `explain` (verbalise `ReportFacts`). Prices, costing, validation and optimisation are deterministic Python. Every LLM node has a deterministic fallback, and `check_numbers` rejects any report whose amounts or plan names are not in `ReportFacts`.

## Consequences

+ No fabricated prices; the app works with Ollama switched off. − Less "free-form" agent behaviour; the autonomy is shown through `decide`, clarification and memory.
