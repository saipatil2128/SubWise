"""RunState: the LangGraph state of ONE optimization run (blueprint D, F.2).

List fields that accumulate across nodes use ``operator.add`` reducers so a node returns only
its new items. Everything else is last-write-wins. Values must stay JSON/msgpack-serialisable
(Pydantic models are stored via ``model_dump(mode="json")``) so checkpoints survive restarts.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict

from subwise.domain.enums import DecidedBy, Decision, NextAction


class TraceEntry(TypedDict):
    node: str
    event: str
    detail: str
    decided_by: NotRequired[DecidedBy]


class RunState(TypedDict):
    # identity (set once at start; never changed by nodes)
    run_id: str
    user_id: str
    thread_id: str
    revision: int

    # input
    user_message: str
    feedback: NotRequired[str]  # rejection reason fed back into revision N+1

    # context loaded by load_context
    profile: NotRequired[dict[str, Any]]
    subscriptions: NotRequired[list[dict[str, Any]]]
    learned_prefs: NotRequired[list[dict[str, Any]]]

    # planning and research
    request_spec: NotRequired[dict[str, Any]]  # RequestSpec.model_dump(mode="json")
    clarification_questions: NotRequired[list[str]]
    research_plan: NotRequired[list[dict[str, Any]]]
    observations: Annotated[list[dict[str, Any]], operator.add]
    validated: NotRequired[list[dict[str, Any]]]
    quality_report: NotRequired[dict[str, Any]]
    next_action: NotRequired[NextAction]

    # optimisation and reporting
    optimization: NotRequired[dict[str, Any]]  # OptimizationResult
    report_id: NotRequired[str]
    report_markdown: NotRequired[str]
    report_source: NotRequired[str]

    # approval
    decision: NotRequired[Decision]
    decision_reason: NotRequired[str]

    # loop counters (blueprint D: each <= 2) and trace
    clarification_count: int
    research_round: int
    revision_count: int
    trace: Annotated[list[TraceEntry], operator.add]


def initial_state(
    *, run_id: str, user_id: str, thread_id: str, user_message: str, revision: int = 1
) -> RunState:
    return {
        "run_id": run_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "revision": revision,
        "user_message": user_message,
        "observations": [],
        "clarification_count": 0,
        "research_round": 0,
        "revision_count": 0,
        "trace": [],
    }
