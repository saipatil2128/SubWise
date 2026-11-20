"""Node `validate`: Pure: core.validation over observations -> validated + DataQualityReport.

Implementation: M10.
"""

from __future__ import annotations

from typing import Any

from subwise.agent.state import RunState
from subwise.errors import NotImplementedYet


def validate(state: RunState) -> dict[str, Any]:
    raise NotImplementedYet("M10", "node validate")
