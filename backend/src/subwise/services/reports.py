"""ReportService: business rules between routers and repositories (blueprint I.3). Implementation:
M11.

Signatures are deliberately loose in Phase 1; the implementing module replaces ``*args`` with
typed parameters that ALWAYS start with ``user_id: str``.
"""

from __future__ import annotations

from typing import Any

from subwise.errors import NotImplementedYet


class ReportService:
    def get(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "ReportService.get")

    def latest_for_run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "ReportService.latest_for_run")
