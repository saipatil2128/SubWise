# ADR-002: Identifiers

Date: 2026-11-21 · Status: Accepted

## Context

TA2 used the conversation ID as the user ID (`get_preference(thread_id)`) and reused one checkpoint thread for every run.

## Decision

`usr_…` = account, `thr_…` = chat conversation, `run_…` = one optimisation (the workflow_id). LangGraph's `configurable.thread_id` is always the run_id and is built only by `subwise.agent.config.graph_config`, which rejects non-`run_` IDs. `user_id` comes only from the auth token. IDs are prefixed ULIDs (`subwise.ids.new_id`).

## Consequences

+ Runs are isolated, resumable and replayable; mix-ups fail loudly. − Conversation continuity is handled explicitly (last messages + previous RequestSpec), not by the checkpointer.
