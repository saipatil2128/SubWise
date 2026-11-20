"""Single-thread run worker (blueprint C, I.3): one local Ollama serves one run at a time.

Status transitions: queued → running → waiting_clarification | waiting_approval | completed |
failed | cancelled. After a backend restart, ``sweep_orphaned_runs`` marks runs that were
mid-flight as failed with WORKER_LOST; they can be resumed from their checkpoint.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from langgraph.types import Command
from sqlalchemy import select

from subwise.agent.config import as_runnable_config, graph_config
from subwise.agent.graph import AgentDeps, build_graph
from subwise.agent.state import initial_state
from subwise.db.models import Message, OptimizationRun
from subwise.db.repositories import latest_report
from subwise.db.session import session_scope
from subwise.domain.enums import EventType, RunStatus
from subwise.errors import SubWiseError
from subwise.ids import new_id
from subwise.memory.backends import Checkpointer

log = logging.getLogger(__name__)
TERMINAL = {RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value}


class RunWorker:
    def __init__(
        self, deps: AgentDeps, checkpointer: Checkpointer, *, max_workers: int = 1
    ) -> None:
        self.deps = deps
        self.graph = build_graph(deps, checkpointer.saver)
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="subwise-run")
        self._futures: dict[str, Future[None]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ public API
    def start(self, run_id: str, user_id: str) -> None:
        self._submit(run_id, user_id, None)

    def resume(self, run_id: str, user_id: str, value: dict[str, Any]) -> None:
        self._submit(run_id, user_id, value)

    def continue_from_checkpoint(self, run_id: str, user_id: str) -> None:
        self._submit(run_id, user_id, "__continue__")

    def wait(self, run_id: str, timeout: float | None = None) -> None:
        fut = self._futures.get(run_id)
        if fut is not None:
            fut.result(timeout=timeout)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def pending_state(self, run_id: str, user_id: str) -> Any:
        return self.graph.get_state(
            as_runnable_config(graph_config(run_id=run_id, user_id=user_id))
        )

    # ------------------------------------------------------------------ internals
    def _submit(self, run_id: str, user_id: str, value: Any) -> None:
        with self._lock:
            self._futures[run_id] = self._pool.submit(self._execute, run_id, user_id, value)

    def _set(self, run_id: str, **fields: Any) -> OptimizationRun | None:
        with session_scope(self.deps.session_factory) as s:
            run = s.get(OptimizationRun, run_id)
            if run is None:
                return None
            for k, v in fields.items():
                setattr(run, k, v)
            return run

    def _execute(self, run_id: str, user_id: str, value: Any) -> None:
        sf = self.deps.session_factory
        with session_scope(sf) as s:
            run = s.get(OptimizationRun, run_id)
            if run is None or run.status == RunStatus.CANCELLED.value:
                return
            message, thread_id, mode = run.request_message, run.thread_id, run.mode
            run.status = RunStatus.RUNNING.value
            run.pending_interrupt = None
            run.started_at = run.started_at or datetime.now(UTC)
            run.llm_model = self.deps.llm.model_name
        cfg = as_runnable_config(
            graph_config(
                run_id=run_id, user_id=user_id, recursion_limit=self.deps.settings.recursion_limit
            )
        )
        try:
            if value is None:
                payload: Any = initial_state(
                    run_id=run_id,
                    user_id=user_id,
                    thread_id=thread_id,
                    user_message=message,
                    mode=mode,
                )
            elif value == "__continue__":
                payload = None
            else:
                payload = Command(resume=value)
            self.graph.invoke(payload, cfg)
        except SubWiseError as exc:
            log.exception("run %s failed", run_id)
            self._fail(run_id, exc.code.value, exc.message)
            return
        except Exception as exc:
            log.exception("run %s crashed", run_id)
            self._fail(run_id, "INTERNAL_ERROR", f"{type(exc).__name__}: {exc}")
            return
        self._after_step(run_id, user_id, cfg)

    def _fail(self, run_id: str, code: str, message: str) -> None:
        self._set(
            run_id,
            status=RunStatus.FAILED.value,
            error_code=code,
            error_message=message,
            ended_at=datetime.now(UTC),
        )
        self.deps.events.emit(
            run_id, None, EventType.TOOL_ERROR, f"Run failed: {message}", {"code": code}
        )

    def _after_step(self, run_id: str, user_id: str, cfg: dict[str, Any]) -> None:
        snap = self.graph.get_state(cfg)
        values = snap.values or {}
        with session_scope(self.deps.session_factory) as s:
            run = s.get(OptimizationRun, run_id)
            if run is None:
                return
            if values.get("request_spec"):
                run.request_spec = values["request_spec"]
            if snap.interrupts:
                intr = snap.interrupts[0].value
                kind = intr.get("kind") if isinstance(intr, dict) else None
                run.status = (
                    RunStatus.WAITING_APPROVAL.value
                    if kind == "approval"
                    else RunStatus.WAITING_CLARIFICATION.value
                )
                run.pending_interrupt = intr if isinstance(intr, dict) else {"value": intr}
                text = (
                    "Recommendation ready for your review."
                    if kind == "approval"
                    else "I need a little more information."
                )
            else:
                run.status = RunStatus.COMPLETED.value
                run.pending_interrupt = None
                run.ended_at = datetime.now(UTC)
                run.revision = 1 + int(values.get("revision_count", 0))
                rep = latest_report(s, run_id)
                text = (
                    f"Run finished. Final report version {rep.version} was {rep.status}."
                    if rep
                    else "Run finished."
                )
            s.add(
                Message(
                    id=new_id("msg"),
                    thread_id=run.thread_id,
                    user_id=user_id,
                    role="assistant",
                    content=text,
                    run_id=run_id,
                )
            )
            status = run.status
        self.deps.events.emit(
            run_id,
            None,
            EventType.INTERRUPT if status.startswith("waiting") else EventType.NODE_END,
            f"Run status: {status}",
            {"status": status},
        )


def sweep_orphaned_runs(worker: RunWorker) -> int:
    """Mark runs left 'queued'/'running' by a previous process as failed (WORKER_LOST)."""
    count = 0
    with session_scope(worker.deps.session_factory) as s:
        rows = s.scalars(
            select(OptimizationRun).where(
                OptimizationRun.status.in_([RunStatus.QUEUED.value, RunStatus.RUNNING.value])
            )
        ).all()
        for run in rows:
            run.status = RunStatus.FAILED.value
            run.error_code = "WORKER_LOST"
            run.error_message = (
                "The server stopped while this run was in progress. "
                "You can resume it from its last checkpoint."
            )
            run.ended_at = datetime.now(UTC)
            count += 1
    return count
