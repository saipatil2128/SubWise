"""Single-thread run worker (blueprint C, I.3). Implementation: M11.

One ThreadPoolExecutor(max_workers=1): one local Ollama serves one run at a time.
"""

from __future__ import annotations

from typing import Any, Protocol

from subwise.errors import NotImplementedYet


class RunExecutor(Protocol):
    def submit_start(self, *, run_id: str, user_id: str, thread_id: str, message: str) -> None: ...

    def submit_resume(self, *, run_id: str, user_id: str, resume: dict[str, Any]) -> None: ...

    def cancel(self, run_id: str) -> None: ...

    def shutdown(self) -> None: ...


class ThreadRunExecutor:
    def __init__(self, *, max_workers: int = 1) -> None:
        self._max_workers = max_workers

    def submit_start(self, *, run_id: str, user_id: str, thread_id: str, message: str) -> None:
        raise NotImplementedYet("M11", "ThreadRunExecutor.submit_start")

    def submit_resume(self, *, run_id: str, user_id: str, resume: dict[str, Any]) -> None:
        raise NotImplementedYet("M11", "ThreadRunExecutor.submit_resume")

    def cancel(self, run_id: str) -> None:
        raise NotImplementedYet("M11", "ThreadRunExecutor.cancel")

    def shutdown(self) -> None:
        """Safe to call during app shutdown even before M11 (no threads exist yet)."""
        return None
