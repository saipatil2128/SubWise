"""Replaceable search interface (blueprint G.4). Search is OPTIONAL in SubWise."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, HttpUrl


class SearchHit(BaseModel):
    url: HttpUrl
    title: str
    snippet: str = ""


@runtime_checkable
class SearchProvider(Protocol):
    name: str
    enabled: bool

    def search(
        self,
        query: str,
        *,
        country: str,
        max_results: int = 5,
        include_domains: list[str] | None = None,
    ) -> list[SearchHit]:
        """Return candidate URLs. Callers must still check the domain is official."""
        ...
