"""Optimization run graph (blueprint D, diagram "Only three steps touch the LLM").

Verified API (langgraph==1.2.24): ``StateGraph(RunState)``, ``add_node``,
``add_conditional_edges``, ``compile(checkpointer=...)``; pause with
``langgraph.types.interrupt(payload)``; resume with
``graph.invoke(Command(resume=value), config)``; ``graph.get_state(config).next`` /
``.interrupts`` expose a pending pause. ``invoke`` output contains ``"__interrupt__"`` when
paused. Implementation: M10.
"""

from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel

from subwise.errors import NotImplementedYet

NODE_NAMES: Final[tuple[str, ...]] = (
    "load_context",
    "parse_intent",
    "clarify",
    "plan_research",
    "research",
    "validate",
    "decide",
    "optimize",
    "explain",
    "check_numbers",
    "approval",
    "save_and_learn",
)

LLM_NODES: Final[frozenset[str]] = frozenset({"parse_intent", "decide", "explain"})
INTERRUPT_NODES: Final[frozenset[str]] = frozenset({"clarify", "approval"})


class ClarifyInterrupt(BaseModel):
    kind: str = "clarify"
    questions: list[str]


class ApprovalInterrupt(BaseModel):
    kind: str = "approval"
    report_id: str


class ClarifyResume(BaseModel):
    answers: dict[str, str]


class ApprovalResume(BaseModel):
    decision: str  # Decision value
    reason: str | None = None
    remember: list[str] = []


def build_graph(checkpointer: Any) -> Any:
    """Return the compiled StateGraph for one run (M10)."""
    raise NotImplementedYet("M10", "build_graph")
