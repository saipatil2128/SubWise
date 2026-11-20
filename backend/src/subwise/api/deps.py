"""FastAPI dependencies. ``user_id`` ALWAYS comes from the auth cookie, never from the request
body or path (blueprint J.3). Unsafe methods also require the CSRF header."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from subwise.container import Container
from subwise.errors import Forbidden, Unauthenticated
from subwise.services.auth import COOKIE_NAME, CSRF_HEADER, decode_token

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class AuthenticatedUser:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id


def container_dep(request: Request) -> Container:
    c = getattr(request.app.state, "container", None)
    if c is None:  # pragma: no cover - app not started via lifespan
        raise RuntimeError("Application container is not initialised")
    return c  # type: ignore[no-any-return]


ContainerDep = Annotated[Container, Depends(container_dep)]


def db_session(c: ContainerDep) -> Iterator[Session]:
    s = c.session_factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


DbDep = Annotated[Session, Depends(db_session)]


def require_csrf(request: Request) -> None:
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != "1":
        raise Forbidden(f"Missing {CSRF_HEADER} header.")


def current_user(request: Request, c: ContainerDep) -> AuthenticatedUser:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise Unauthenticated("Please sign in.")
    user_id = decode_token(c.settings, token)
    require_csrf(request)
    return AuthenticatedUser(user_id)


CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]
