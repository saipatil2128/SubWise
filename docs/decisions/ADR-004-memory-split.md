# ADR-004: Memory split

Date: 2026-11-21 · Status: Accepted

## Context

TA2 had two incompatible long-term stores and never saved anything.

## Decision

If the user edits it in a form, it lives in `app.db` (budget, requirements, subscriptions). If the agent learned it from a decision, it lives in the LangGraph `SqliteStore` under `("users", user_id, kind)`, written only after an approval action, listed and deletable on the Profile page. Short-term memory = checkpoints of one run.

## Consequences

+ No duplicated facts; the user controls what was learned. − Two stores to back up (both are single SQLite files under `data/`).
