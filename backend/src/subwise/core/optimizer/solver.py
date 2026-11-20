"""Two-stage lexicographic 0-1 program solved with PuLP 3.3.x + bundled CBC (ADR-005).

Constraints (blueprint H.3, v2):
  y_f <= sum_p a_pf x_p                for all f        (overlap: each feature counts once)
  y_f = 1                              for f in M       (must-haves)
  sum_p c_p x_p <= B                                    (budget)
  sum_{p in E} x_p <= 1                for each exclusion group E (NOT per provider)
  x_a <= sum_{q in R(a)} x_q           for each add-on a
  k_s <= sum_{p : s in ent(p)} x_p     retention via any plan granting line s (incl. bundles)
  x_p = 1 for p in K;  x_p = 0 for p in X
Stage 1 maximises sum w_f y_f + lambda * sum u_s k_s; stage 2 minimises cost at
score >= S* - delta(mode); stage 3 adds no-good cuts for alternatives.
"""

from __future__ import annotations

from subwise.domain.optimization import OptimizationResult, OptimizerInput
from subwise.errors import NotImplementedYet

MODE_DELTA_FRACTION = {"best": 0.0, "balanced": 0.3, "savings": 1.0}


def solve(problem: OptimizerInput) -> OptimizationResult:
    """Solve OAVOE. Must return ``status='infeasible'`` with a diagnosis, never raise, when
    the problem has no feasible portfolio (M6)."""
    raise NotImplementedYet("M6", "OAVOE solve")
