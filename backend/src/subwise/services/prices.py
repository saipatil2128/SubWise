"""PriceService: business rules between routers and repositories (blueprint I.3). Implementation:
M8.

Signatures are deliberately loose in Phase 1; the implementing module replaces ``*args`` with
typed parameters that ALWAYS start with ``user_id: str``.
"""

from __future__ import annotations

from typing import Any

from subwise.errors import NotImplementedYet


class PriceService:
    def current(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M8", "PriceService.current")

    def history(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M8", "PriceService.history")

    def refresh(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M8", "PriceService.refresh")
