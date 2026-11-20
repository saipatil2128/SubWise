"""DashboardService: business rules between routers and repositories (blueprint I.3).
Implementation: M11.

Signatures are deliberately loose in Phase 1; the implementing module replaces ``*args`` with
typed parameters that ALWAYS start with ``user_id: str``.
"""

from __future__ import annotations

from typing import Any

from subwise.errors import NotImplementedYet


class DashboardService:
    def summary(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "DashboardService.summary")
