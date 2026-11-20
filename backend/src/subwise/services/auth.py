"""AuthService: business rules between routers and repositories (blueprint I.3). Implementation: M3.

Signatures are deliberately loose in Phase 1; the implementing module replaces ``*args`` with
typed parameters that ALWAYS start with ``user_id: str``.
"""

from __future__ import annotations

from typing import Any

from subwise.errors import NotImplementedYet


class AuthService:
    def register(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M3", "AuthService.register")

    def authenticate(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M3", "AuthService.authenticate")

    def issue_token(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M3", "AuthService.issue_token")

    def decode_token(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedYet("M3", "AuthService.decode_token")
