"""Node `clarify`: interrupt({'questions': [...]}) when RequestSpec.missing_fields; max 2. Keep
code before interrupt() idempotent: the node re-runs from its start on resume.

Implementation: M10.
"""

from __future__ import annotations

from typing import Any

from subwise.agent.state import RunState
from subwise.errors import NotImplementedYet


def clarify(state: RunState) -> dict[str, Any]:
    raise NotImplementedYet("M10", "node clarify")
