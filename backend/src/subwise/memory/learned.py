"""Learned (agent-written) long-term preferences (blueprint F.3). M9.

Rule: the agent writes here ONLY after an approval action; form-edited data (budget,
requirements, subscriptions) is never copied into the store.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import AwareDatetime, BaseModel

from subwise.errors import NotImplementedYet


class MemoryKind(StrEnum):
    REJECTIONS = "rejections"
    STATED_PRIORITIES = "stated_priorities"
    PROVIDER_ATTITUDES = "provider_attitudes"


class LearnedItem(BaseModel):
    kind: MemoryKind
    key: str
    value: dict[str, object]
    run_id: str
    created_at: AwareDatetime


class LearnedMemory:
    def list_for_user(self, user_id: str, *, limit: int = 10) -> list[LearnedItem]:
        raise NotImplementedYet("M9", "LearnedMemory.list_for_user")

    def remember(self, user_id: str, item: LearnedItem) -> None:
        raise NotImplementedYet("M9", "LearnedMemory.remember")

    def forget(self, user_id: str, kind: MemoryKind, key: str) -> None:
        raise NotImplementedYet("M9", "LearnedMemory.forget")
