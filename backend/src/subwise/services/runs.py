"""RunService: business rules between routers and repositories (blueprint I.3). Implementation: M11.

Signatures are deliberately loose in Phase 1; the implementing module replaces ``*args`` with
typed parameters that ALWAYS start with ``user_id: str``.
"""

from __future__ import annotations

from typing import Any

from subwise.errors import NotImplementedYet


class RunService:
    def create(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "RunService.create")

    def get(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "RunService.get")

    def list(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "RunService.list")

    def resume_clarification(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "RunService.resume_clarification")

    def resume_approval(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "RunService.resume_approval")

    def cancel(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M11", "RunService.cancel")
