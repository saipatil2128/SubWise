"""Node `decide`: LLM picks among guard-allowed NextActions; fallback decide_rules. Records
decided_by.

Implementation: M10.
"""

from __future__ import annotations

from typing import Any

from subwise.agent.state import RunState
from subwise.errors import NotImplementedYet


def decide(state: RunState) -> dict[str, Any]:
    raise NotImplementedYet("M10", "node decide")
