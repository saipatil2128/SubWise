"""Exhaustive reference solver for tests only (n <= 12 candidates).

``test_ilp_matches_bruteforce`` checks that ``solver.solve`` finds the same lexicographic
optimum (best stage-1 score, then lowest cost at that score) on random instances.
"""

from __future__ import annotations

from itertools import combinations

from subwise.domain.optimization import CandidatePlan, OptimizerInput

MAX_CANDIDATES = 12


def feasible(p: OptimizerInput, chosen: list[CandidatePlan]) -> bool:
    ids = {c.plan_id for c in chosen}
    groups = [c.exclusion_group for c in chosen]
    if len(groups) != len(set(groups)):
        return False
    if any(
        pid not in ids for pid in p.mandatory_plan_ids if pid in {c.plan_id for c in p.candidates}
    ):
        return False
    if ids & set(p.excluded_plan_ids) - set(p.mandatory_plan_ids):
        return False
    for c in chosen:
        for req in c.prerequisites_any_of:
            if not (req & ids):
                return False
    feats = set().union(*(c.features for c in chosen)) if chosen else set()
    if not set(p.must_have) <= feats:
        return False
    cost = sum(c.monthly_paise for c in chosen) + p.fixed_monthly_paise
    return p.budget_paise is None or cost <= p.budget_paise


def score(p: OptimizerInput, chosen: list[CandidatePlan]) -> float:
    feats = set().union(*(c.features for c in chosen)) if chosen else set()
    lines = set().union(*(c.service_lines for c in chosen)) if chosen else set()
    s = sum(w for f, w in p.weights.items() if f in feats and f not in p.must_have)
    s += sum(p.retention_lambda * u for line, u in p.current_line_usage.items() if line in lines)
    return round(s, 6)


def solve_bruteforce(p: OptimizerInput) -> tuple[float, int] | None:
    """Return (best score, min cost at that score) or None if infeasible (BEST mode only)."""
    if len(p.candidates) > MAX_CANDIDATES:
        raise ValueError(f"brute force supports at most {MAX_CANDIDATES} candidates")
    best: tuple[float, int] | None = None
    for r in range(len(p.candidates) + 1):
        for combo in combinations(p.candidates, r):
            chosen = list(combo)
            if not feasible(p, chosen):
                continue
            key = (score(p, chosen), sum(c.monthly_paise for c in chosen))
            if (
                best is None
                or key[0] > best[0] + 1e-9
                or (abs(key[0] - best[0]) <= 1e-9 and key[1] < best[1])
            ):
                best = key
    return best
