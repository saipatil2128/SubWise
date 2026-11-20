"""Exhaustive reference solver for tests only (n <= 12 candidates). Implementation: M6.

``test_ilp_matches_bruteforce`` compares this against ``solver.solve`` on random instances.
"""

from __future__ import annotations

from subwise.domain.optimization import OptimizationResult, OptimizerInput
from subwise.errors import NotImplementedYet

MAX_CANDIDATES = 12


def solve_bruteforce(problem: OptimizerInput) -> OptimizationResult:
    raise NotImplementedYet("M6", "brute-force reference solver")
