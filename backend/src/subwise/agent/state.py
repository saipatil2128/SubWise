"""RunState: the LangGraph state of ONE optimization run (blueprint D, F.2).

Values stay JSON-serialisable (Pydantic models are stored via ``model_dump(mode="json")``) so
checkpoints survive restarts. ``trace`` accumulates with an ``operator.add`` reducer.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict


class TraceEntry(TypedDict):
    node: str
    event: str
    detail: str
    decided_by: NotRequired[str]


class RunState(TypedDict):
    # identity (set once at start; never changed by nodes)
    run_id: str
    user_id: str
    thread_id: str
    user_message: str
    mode: str

    # context loaded by load_context
    profile: NotRequired[dict[str, Any]]
    requirements: NotRequired[list[dict[str, Any]]]
    subscriptions: NotRequired[list[dict[str, Any]]]
    learned: NotRequired[list[dict[str, Any]]]

    # planning
    request_spec: NotRequired[dict[str, Any]]
    missing_fields: NotRequired[list[str]]
    feedback: NotRequired[str]
    research_plan: NotRequired[list[str]]
    retry_providers: NotRequired[list[str]]
    research_results: NotRequired[list[dict[str, Any]]]
    quality: NotRequired[dict[str, Any]]
    next_action: NotRequired[str]

    # optimisation and reporting
    optimization: NotRequired[dict[str, Any]]
    facts: NotRequired[dict[str, Any]]
    observation_ids: NotRequired[list[str]]
    draft_summary: NotRequired[str]
    draft_source: NotRequired[str]
    report_id: NotRequired[str]

    # approval
    decision: NotRequired[str]
    decision_reason: NotRequired[str]
    remember: NotRequired[list[str]]

    # loop counters (blueprint D: each <= 2) and trace
    clarification_count: int
    research_round: int
    revision_count: int
    trace: Annotated[list[TraceEntry], operator.add]


def initial_state(
    *, run_id: str, user_id: str, thread_id: str, user_message: str, mode: str = "balanced"
) -> RunState:
    return {
        "run_id": run_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "user_message": user_message,
        "mode": mode,
        "clarification_count": 0,
        "research_round": 0,
        "revision_count": 0,
        "trace": [],
    }
