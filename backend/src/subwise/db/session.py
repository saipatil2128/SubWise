"""Engine and session factory (M2): SQLite in WAL mode with busy_timeout=5000 (blueprint J.2)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from subwise.config import Settings
from subwise.errors import NotImplementedYet

SQLITE_PRAGMAS = ("PRAGMA journal_mode=WAL", "PRAGMA busy_timeout=5000", "PRAGMA foreign_keys=ON")


def make_session_factory(settings: Settings) -> object:
    raise NotImplementedYet("M2", "make_session_factory")


def get_session() -> Iterator[Session]:
    raise NotImplementedYet("M2", "get_session")
