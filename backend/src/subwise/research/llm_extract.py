"""Tier-3 extraction: LLM reads ~400-char windows around each ₹ match (blueprint G.2). M8.

Output can reach at most ``partial`` and only if all five bindings hold; the extractor has no
tools, and page text is treated as data (prompt-injection rule, blueprint J.3).
"""

from __future__ import annotations

from subwise.domain.catalog import Plan, Provider
from subwise.domain.evidence import PlanObservation
from subwise.errors import NotImplementedYet
from subwise.llm.gateway import LLMGateway
from subwise.research.fetch import FetchResult

WINDOW_CHARS = 400


def price_windows(text: str, *, window: int = WINDOW_CHARS) -> list[str]:
    raise NotImplementedYet("M8", "price_windows")


def extract_with_llm(
    fetched: FetchResult, *, provider: Provider, plans: list[Plan], llm: LLMGateway
) -> list[PlanObservation]:
    raise NotImplementedYet("M8", "extract_with_llm")
