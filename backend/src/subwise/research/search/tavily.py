"""Optional Tavily provider (free tier, no card). Requires ``pip install -e ".[search]"`` and
``SUBWISE_TAVILY_API_KEY``. The ``tavily`` package is imported lazily so the base install never
needs it. Used only to recover an official pricing URL when the registry URL fails."""

from __future__ import annotations

from typing import Any

from subwise.errors import SearchUnavailable
from subwise.research.search.base import SearchHit


class TavilySearchProvider:
    name = "tavily"
    enabled = True

    def __init__(self, api_key: str, *, timeout_s: float = 15.0) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    def search(
        self,
        query: str,
        *,
        country: str,
        max_results: int = 5,
        include_domains: list[str] | None = None,
    ) -> list[SearchHit]:
        try:
            from tavily import TavilyClient  # optional dependency

            client = TavilyClient(api_key=self._api_key)
            kwargs: dict[str, Any] = {"max_results": max_results, "search_depth": "basic"}
            if include_domains:
                kwargs["include_domains"] = include_domains
            data = client.search(query, **kwargs)
        except Exception as exc:  # network, quota or auth problems
            raise SearchUnavailable(f"Tavily search failed: {exc}") from exc
        hits = []
        for r in data.get("results", []):
            try:
                hits.append(
                    SearchHit(
                        url=r["url"], title=r.get("title", ""), snippet=r.get("content", "")[:300]
                    )
                )
            except (KeyError, ValueError):
                continue
        return hits
