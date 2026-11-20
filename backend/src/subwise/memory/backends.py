"""The only place that opens LangGraph's SQLite checkpointer and store (blueprint F). M9.

Verified against langgraph==1.2.24 + langgraph-checkpoint-sqlite==3.1.3
(see tests/integration/test_library_contracts.py and docs/verified-apis.md):

  from langgraph.checkpoint.sqlite import SqliteSaver
  from langgraph.store.sqlite import SqliteStore

  # long-lived (worker thread): pass a connection opened with check_same_thread=False
  conn = sqlite3.connect(path, check_same_thread=False); saver = SqliteSaver(conn)
  # short-lived / scripts: context managers
  with SqliteSaver.from_conn_string(path) as saver: ...
  with SqliteStore.from_conn_string(path) as store:
      store.setup()                                   # creates tables; idempotent
      store.put(("users", user_id, kind), key, {...})
      store.get(ns, key) -> Item | None ; store.search(("users", user_id)) ; store.delete(ns, key)

Ruff bans importing SqliteSaver/SqliteStore anywhere else (TID251).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from subwise.errors import NotImplementedYet

STORE_ROOT = "users"
"""Long-term memory namespace = (STORE_ROOT, user_id, kind)."""


def store_namespace(user_id: str, kind: str) -> tuple[str, str, str]:
    if not user_id or not kind:
        raise ValueError("user_id and kind are required for a memory namespace")
    return (STORE_ROOT, user_id, kind)


@contextmanager
def open_checkpointer(path: Path) -> Iterator[Any]:
    """Yield a SqliteSaver for ``path`` (M9)."""
    raise NotImplementedYet("M9", "open_checkpointer")
    yield  # pragma: no cover


@contextmanager
def open_store(path: Path) -> Iterator[Any]:
    """Yield a set-up SqliteStore for ``path`` (M9)."""
    raise NotImplementedYet("M9", "open_store")
    yield  # pragma: no cover
