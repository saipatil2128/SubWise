"""Node `optimize`: core.optimizer.solve; infeasible -> diagnosis, never raise.

Implementation: M10.
"""

from __future__ import annotations

from typing import Any

from subwise.agent.state import RunState
from subwise.errors import NotImplementedYet


def optimize(state: RunState) -> dict[str, Any]:
    raise NotImplementedYet("M10", "node optimize")
