"""Learned (agent-written) long-term preferences (blueprint F.3).

Rule: the agent writes here ONLY as the result of an approval action (approve or reject);
form-edited data (budget, requirements, subscriptions) is never copied into the store.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from subwise.memory.backends import STORE_ROOT, Store, store_namespace


class MemoryKind(StrEnum):
    REJECTIONS = "rejections"
    STATED_PRIORITIES = "stated_priorities"
    PROVIDER_ATTITUDES = "provider_attitudes"


class LearnedItem(BaseModel):
    kind: MemoryKind
    key: str
    value: dict[str, Any]
    run_id: str
    created_at: datetime


class LearnedMemory:
    def __init__(self, store: Store) -> None:
        self._store = store

    def list_for_user(self, user_id: str, *, limit: int = 50) -> list[LearnedItem]:
        with self._store.locked() as st:
            items = st.search((STORE_ROOT, user_id), limit=limit)
        out = []
        for it in items:
            kind = it.namespace[-1]
            if kind not in MemoryKind.__members__.values():
                continue
            out.append(
                LearnedItem(
                    kind=MemoryKind(kind),
                    key=it.key,
                    value=dict(it.value),
                    run_id=str(it.value.get("run_id", "")),
                    created_at=it.created_at
                    if it.created_at.tzinfo
                    else it.created_at.replace(tzinfo=UTC),
                )
            )
        return sorted(out, key=lambda i: i.created_at, reverse=True)

    def remember(
        self, user_id: str, kind: MemoryKind, key: str, value: dict[str, Any], run_id: str
    ) -> None:
        payload = {**value, "run_id": run_id, "saved_at": datetime.now(UTC).isoformat()}
        with self._store.locked() as st:
            st.put(store_namespace(user_id, kind.value), key, payload)

    def forget(self, user_id: str, kind: MemoryKind, key: str) -> bool:
        ns = store_namespace(user_id, kind.value)
        with self._store.locked() as st:
            if st.get(ns, key) is None:
                return False
            st.delete(ns, key)
        return True
