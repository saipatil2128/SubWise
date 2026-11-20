"""FastAPI dependencies. ``user_id`` ALWAYS comes from the auth token, never from the request
body or path (blueprint J.3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from subwise.config import Settings, get_settings
from subwise.errors import NotImplementedYet


class AuthenticatedUser:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id


def settings_dep() -> Settings:
    return get_settings()


def current_user(request: Request) -> AuthenticatedUser:
    """Decode the session cookie into the user. Implemented in M3."""
    raise NotImplementedYet("M3", "Authentication")


SettingsDep = Annotated[Settings, Depends(settings_dep)]
CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]
