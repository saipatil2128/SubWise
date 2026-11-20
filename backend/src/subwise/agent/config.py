"""The single place a LangGraph config is built (blueprint F.1 "naming trap").

LangGraph calls its checkpoint key ``thread_id``. In SubWise that value is ALWAYS a
``run_id`` (one optimization). A SubWise ``thread_id`` (chat conversation) and a ``user_id``
are never used as the checkpoint key. Building ``{"configurable": ...}`` anywhere else is a
review-blocking bug (see AGENTS.md).
"""

from __future__ import annotations

from typing import Any, TypedDict


class Configurable(TypedDict):
    thread_id: str  # == SubWise run_id
    user_id: str


class GraphConfig(TypedDict):
    configurable: Configurable
    recursion_limit: int


DEFAULT_RECURSION_LIMIT = 40


def graph_config(
    *, run_id: str, user_id: str, recursion_limit: int = DEFAULT_RECURSION_LIMIT
) -> GraphConfig:
    if not run_id.startswith("run_"):
        raise ValueError(f"graph_config expects a run_id ('run_...'), got {run_id!r}")
    if not user_id.startswith("usr_"):
        raise ValueError(f"graph_config expects a user_id ('usr_...'), got {user_id!r}")
    return {
        "configurable": {"thread_id": run_id, "user_id": user_id},
        "recursion_limit": recursion_limit,
    }


def as_runnable_config(config: GraphConfig) -> dict[str, Any]:
    """LangGraph accepts a plain dict; this keeps call sites typed."""
    return dict(config)
