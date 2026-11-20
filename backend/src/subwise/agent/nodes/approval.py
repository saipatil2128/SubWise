"""Node `approval`: interrupt({'report_id': ...}) -> Decision; nothing with side effects before
interrupt().

Implementation: M10.
"""

from __future__ import annotations

from typing import Any

from subwise.agent.state import RunState
from subwise.errors import NotImplementedYet


def approval(state: RunState) -> dict[str, Any]:
    raise NotImplementedYet("M10", "node approval")
