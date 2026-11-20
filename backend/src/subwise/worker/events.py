"""Run events: persisted to ``run_events`` and fanned out to SSE subscribers. M11."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from pydantic import AwareDatetime, BaseModel

from subwise.domain.enums import EventType
from subwise.errors import NotImplementedYet


class RunEvent(BaseModel):
    run_id: str
    seq: int
    node: str | None
    event_type: EventType
    payload: dict[str, Any] = {}
    duration_ms: float | None = None
    created_at: AwareDatetime


class EventBus:
    def publish(self, event: RunEvent) -> None:
        raise NotImplementedYet("M11", "EventBus.publish")

    def subscribe(self, run_id: str, *, after_seq: int = 0) -> AsyncIterator[RunEvent]:
        """Replay stored events with seq > after_seq, then stream live ones."""
        raise NotImplementedYet("M11", "EventBus.subscribe")
