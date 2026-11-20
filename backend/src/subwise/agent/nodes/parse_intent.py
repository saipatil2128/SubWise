"""Node `parse_intent`: LLM -> RequestSpec (JSON schema); fallback parse_intent_rules.

Implementation: M10.
"""

from __future__ import annotations

from typing import Any

from subwise.agent.state import RunState
from subwise.errors import NotImplementedYet


def parse_intent(state: RunState) -> dict[str, Any]:
    raise NotImplementedYet("M10", "node parse_intent")
