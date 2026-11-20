"""Node `check_numbers`: Every amount and plan name in the report must exist in ReportFacts; else
template.

Implementation: M10.
"""

from __future__ import annotations

from typing import Any

from subwise.agent.state import RunState
from subwise.errors import NotImplementedYet


def check_numbers(state: RunState) -> dict[str, Any]:
    raise NotImplementedYet("M10", "node check_numbers")
