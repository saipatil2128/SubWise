"""Deterministic fallbacks used whenever the LLM is down, slow or wrong (blueprint J.2). M7."""

from __future__ import annotations

from subwise.core.report_facts import ReportFacts
from subwise.domain.enums import NextAction
from subwise.domain.evidence import DataQualityReport
from subwise.domain.request import RequestSpec
from subwise.errors import NotImplementedYet


def parse_intent_rules(message: str, *, profile_budget_paise: int | None) -> RequestSpec:
    """Keyword + regex parser (₹ amounts, category words). Sets ``source='rules'``."""
    raise NotImplementedYet("M7", "parse_intent_rules")


def decide_rules(report: DataQualityReport, *, research_round: int, max_rounds: int) -> NextAction:
    """Blueprint D.1 rule table: all must-haves verified -> proceed; round < max ->
    research_more; else proceed_with_gaps."""
    raise NotImplementedYet("M7", "decide_rules")


def render_template_report(facts: ReportFacts) -> str:
    """Jinja-free string template with the same sections as the LLM report."""
    raise NotImplementedYet("M7", "render_template_report")
