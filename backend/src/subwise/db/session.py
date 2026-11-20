"""Engine and session factory: SQLite in WAL mode with busy_timeout (blueprint J.2)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from subwise.config import Settings

SQLITE_PRAGMAS = ("PRAGMA journal_mode=WAL", "PRAGMA busy_timeout=5000", "PRAGMA foreign_keys=ON")


def make_engine(settings: Settings) -> Engine:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}, future=True
    )

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn: Any, _record: Any) -> None:
        cur = dbapi_conn.cursor()
        for pragma in SQLITE_PRAGMAS:
            cur.execute(pragma)
        cur.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
