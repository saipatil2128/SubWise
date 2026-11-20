"""Node `explain`: LLM verbalises ReportFacts; fallback render_template_report.

Implementation: M10.
"""

from __future__ import annotations

from typing import Any

from subwise.agent.state import RunState
from subwise.errors import NotImplementedYet


def explain(state: RunState) -> dict[str, Any]:
    raise NotImplementedYet("M10", "node explain")
