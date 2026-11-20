# ADR-007: Optional search

Date: 2026-11-21 · Status: Accepted

## Context

The project must run with free, local tools only. Brave's search API now needs a credit card even for its free credit; Tavily's free tier needs no card but needs an account.

## Decision

`tavily-python` is the optional `search` extra. `get_search_provider()` returns `NullSearchProvider` unless a key is configured **and** the package is installed. `/health` reports `search: disabled`; tier-3 discovery is skipped; runs use tiers 1–2.

## Consequences

+ No mandatory external account. − Providers outside the curated registry cannot be discovered without a key.
