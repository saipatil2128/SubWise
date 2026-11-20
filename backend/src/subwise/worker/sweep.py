"""Startup sweep: runs left 'running' with no live worker become failed: WORKER_LOST and are
offered for resume if a checkpoint exists (blueprint E.3). M11."""

from __future__ import annotations

from subwise.errors import NotImplementedYet


def sweep_orphaned_runs() -> int:
    """Return the number of runs marked WORKER_LOST."""
    raise NotImplementedYet("M11", "sweep_orphaned_runs")
