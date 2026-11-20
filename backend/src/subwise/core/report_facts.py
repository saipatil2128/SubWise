"""Turn an OptimizationResult into explainable, verifiable facts (blueprint H.6). M6/M7.

The LLM explainer only verbalises ``ReportFacts``; ``check_numbers`` enforces that every ₹
amount and plan name in the text appears here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from subwise.domain.optimization import OptimizationResult
from subwise.errors import NotImplementedYet


class ReportFacts(BaseModel):
    chosen_plan_names: list[str]
    current_monthly_display: str
    recommended_monthly_display: str
    monthly_saving_display: str
    annual_saving_display: str
    allowed_amounts_paise: set[int] = Field(default_factory=set)
    allowed_plan_names: set[str] = Field(default_factory=set)
    sections: dict[str, list[str]] = Field(default_factory=dict)


def build_report_facts(result: OptimizationResult, plan_names: dict[str, str]) -> ReportFacts:
    raise NotImplementedYet("M6", "build_report_facts")


def check_numbers(report_markdown: str, facts: ReportFacts) -> list[str]:
    """Return the list of violations (empty == pass) (M7)."""
    raise NotImplementedYet("M7", "check_numbers")
