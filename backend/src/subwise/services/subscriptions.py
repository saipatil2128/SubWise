"""SubscriptionService: business rules between routers and repositories (blueprint I.3).
Implementation: M3.

Signatures are deliberately loose in Phase 1; the implementing module replaces ``*args`` with
typed parameters that ALWAYS start with ``user_id: str``.
"""

from __future__ import annotations

from typing import Any

from subwise.errors import NotImplementedYet


class SubscriptionService:
    def list(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M3", "SubscriptionService.list")

    def create(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M3", "SubscriptionService.create")

    def update(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M3", "SubscriptionService.update")

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M3", "SubscriptionService.delete")
