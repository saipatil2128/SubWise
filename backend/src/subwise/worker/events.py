"""Run events: persisted to ``run_events`` (one source for the live SSE stream and the stored
trace). Every event is a real step that happened in the backend - nothing is simulated."""

from __future__ import annotations

import logging
import threading
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from subwise.db.models import RunEvent
from subwise.db.repositories import next_event_seq
from subwise.db.session import session_scope
from subwise.domain.enums import EventType

log = logging.getLogger(__name__)


class EventSink:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory
        self._lock = threading.Lock()

    def emit(
        self,
        run_id: str,
        node: str | None,
        event_type: EventType,
        message: str,
        payload: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> None:
        with self._lock, session_scope(self._sf) as s:
            seq = next_event_seq(s, run_id)
            s.add(
                RunEvent(
                    run_id=run_id,
                    seq=seq,
                    node=node,
                    event_type=event_type.value,
                    message=message,
                    payload=payload or {},
                    duration_ms=duration_ms,
                )
            )
        log.info("run %s [%s] %s", run_id, node or "-", message)
