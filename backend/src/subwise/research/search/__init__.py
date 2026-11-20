"""Search provider selection. Tavily is optional; the app works fully without it."""

from __future__ import annotations

import importlib.util

from subwise.config import Settings
from subwise.research.search.base import SearchHit, SearchProvider
from subwise.research.search.null import NullSearchProvider

__all__ = ["NullSearchProvider", "SearchHit", "SearchProvider", "get_search_provider"]


def tavily_installed() -> bool:
    return importlib.util.find_spec("tavily") is not None


def get_search_provider(settings: Settings) -> SearchProvider:
    """Return Tavily only if a key is configured AND the optional package is installed."""
    if settings.tavily_api_key is None or not tavily_installed():
        return NullSearchProvider()
    from subwise.research.search.tavily import TavilySearchProvider

    return TavilySearchProvider(settings.tavily_api_key.get_secret_value())
