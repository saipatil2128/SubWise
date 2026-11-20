"""The only place that opens LangGraph's SQLite checkpointer and store (blueprint F).

Verified against langgraph==1.2.24 + langgraph-checkpoint-sqlite==3.1.3
(tests/integration/test_library_contracts.py, docs/verified-apis.md).
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

STORE_ROOT = "users"
"""Long-term memory namespace = (STORE_ROOT, user_id, kind)."""


def store_namespace(user_id: str, kind: str) -> tuple[str, str, str]:
    if not user_id or not kind:
        raise ValueError("user_id and kind are required for a memory namespace")
    return (STORE_ROOT, user_id, kind)


class Checkpointer:
    """Long-lived SqliteSaver shared by the worker thread (one connection,
    check_same_thread off)."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self.saver = SqliteSaver(self._conn)

    def close(self) -> None:
        self._conn.close()


class Store:
    """Thread-safe wrapper over SqliteStore (API requests and the worker both use it)."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._lock = threading.Lock()
        self.store = SqliteStore(self._conn)
        with self._lock:
            self.store.setup()

    @contextmanager
    def locked(self) -> Iterator[SqliteStore]:
        with self._lock:
            yield self.store

    def close(self) -> None:
        self._conn.close()
