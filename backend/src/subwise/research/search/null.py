"""Default search provider: discovery off. Used when no Tavily key or package is present."""

from __future__ import annotations

from subwise.research.search.base import SearchHit


class NullSearchProvider:
    name = "null"
    enabled = False

    def search(self, query: str, *, country: str, max_results: int = 5) -> list[SearchHit]:
        return []
