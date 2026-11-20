"""Optional Tavily provider (free tier, no card). Requires ``pip install -e ".[search]"``.

The ``tavily`` package is imported lazily so the base install never needs it. Implementation: M8.
"""

from __future__ import annotations

from subwise.errors import NotImplementedYet
from subwise.research.search.base import SearchHit


class TavilySearchProvider:
    name = "tavily"
    enabled = True

    def __init__(self, api_key: str, *, timeout_s: float = 15.0) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    def search(self, query: str, *, country: str, max_results: int = 5) -> list[SearchHit]:
        raise NotImplementedYet("M8", "Tavily search")
