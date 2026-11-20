"""OAVOE: two-stage lexicographic 0-1 program on PuLP 3.3.x + bundled CBC (ADR-005).

Constraints (blueprint H.3, v2):
  y_f <= sum_p a_pf x_p                for all f        (overlap: each feature counts once)
  y_f = 1                              for f in M       (must-haves)
  sum_p c_p x_p <= B - fixed                            (budget)
  sum_{p in E} x_p <= 1                for each exclusion group E (NOT per provider)
  x_a <= sum_{q in R} x_q              for each prerequisite set R of add-on a
  k_s <= sum_{p : s in lines(p)} x_p   retention via any plan granting line s (incl. bundles)
  x_p = 1 for p in K;  x_p = 0 for p in X
Stage 1 maximises S = sum w_f y_f + lambda * sum u_s k_s.
Stage 2 minimises cost subject to S >= S* (1 - delta(mode)), tie-breaking towards higher S
and towards keeping current plans. Alternatives come from no-good cuts.
"""

from __future__ import annotations

import time

import pulp

from subwise.domain.enums import OptimizeMode
from subwise.domain.optimization import (
    CandidatePlan,
    InfeasibilityDiagnosis,
    OptimizationResult,
    OptimizerInput,
    Portfolio,
    RejectedCandidate,
)

MODE_DELTA_FRACTION = {
    OptimizeMode.BEST: 0.0,
    OptimizeMode.BALANCED: 0.3,
    OptimizeMode.SAVINGS: 1.0,
}
EPS = 1e-6


def _solver() -> pulp.LpSolver:
    return pulp.PULP_CBC_CMD(msg=False, timeLimit=20)


class _Model:
    """Builds the constraint set once per solve; objectives are swapped per stage."""

    def __init__(self, p: OptimizerInput, cuts: list[frozenset[str]]) -> None:
        self.p = p
        cands = list(p.candidates)
        self.cands = cands
        self.prob = pulp.LpProblem("oavoe", pulp.LpMaximize)
        self.x = {c.plan_id: pulp.LpVariable(f"x_{i}", cat="Binary") for i, c in enumerate(cands)}
        valued = set(p.must_have) | set(p.weights)
        self.features = sorted(valued)
        self.y = {f: pulp.LpVariable(f"y_{i}", cat="Binary") for i, f in enumerate(self.features)}
        lines = sorted(k for k, u in p.current_line_usage.items() if u > 0)
        self.k = {s: pulp.LpVariable(f"k_{i}", cat="Binary") for i, s in enumerate(lines)}
        prob = self.prob
        for f, yf in self.y.items():
            prob += yf <= pulp.lpSum(self.x[c.plan_id] for c in cands if f in c.features)
            if f in p.must_have:
                prob += yf == 1
        if p.budget_paise is not None:
            prob += self.cost_expr() <= max(0, p.budget_paise - p.fixed_monthly_paise)
        groups: dict[str, list[str]] = {}
        for c in cands:
            groups.setdefault(c.exclusion_group, []).append(c.plan_id)
        for members in groups.values():
            if len(members) > 1:
                prob += pulp.lpSum(self.x[m] for m in members) <= 1
        ids = set(self.x)
        for c in cands:
            for req in c.prerequisites_any_of:
                prob += self.x[c.plan_id] <= pulp.lpSum(self.x[q] for q in req if q in ids)
        for s, ks in self.k.items():
            prob += ks <= pulp.lpSum(self.x[c.plan_id] for c in cands if s in c.service_lines)
        for pid in p.mandatory_plan_ids:
            if pid in self.x:
                prob += self.x[pid] == 1
        for pid in p.excluded_plan_ids:
            if pid in self.x and pid not in p.mandatory_plan_ids:
                prob += self.x[pid] == 0
        for cut in cuts:
            # Exclude this exact portfolio (and any superset of it) from the next solve.
            prob += pulp.lpSum(self.x[pid] for pid in cut) <= len(cut) - 1

    def cost_expr(self) -> pulp.LpAffineExpression:
        return pulp.lpSum(c.monthly_paise * self.x[c.plan_id] for c in self.cands)

    def score_expr(self) -> pulp.LpAffineExpression:
        p = self.p
        return pulp.lpSum(
            p.weights.get(f, 0.0) * yf
            for f, yf in self.y.items()
            if f not in p.must_have and p.weights.get(f, 0.0) > 0
        ) + pulp.lpSum(
            p.retention_lambda * p.current_line_usage[s] * ks for s, ks in self.k.items()
        )

    def solve(self, sense: int, objective: pulp.LpAffineExpression) -> str:
        self.prob.sense = sense
        self.prob.setObjective(objective)
        status = self.prob.solve(_solver())
        return str(pulp.LpStatus[status])

    def chosen(self) -> list[str]:
        return [pid for pid, v in self.x.items() if (v.value() or 0) > 0.5]


def _solve_once(p: OptimizerInput, cuts: list[frozenset[str]]) -> list[str] | None:
    m = _Model(p, cuts)
    has_score = any(f not in p.must_have and p.weights.get(f, 0) > 0 for f in m.y) or bool(m.k)
    if has_score:
        if m.solve(pulp.LpMaximize, m.score_expr()) != "Optimal":
            return None
        best_score = pulp.value(m.score_expr()) or 0.0
        delta = MODE_DELTA_FRACTION[p.mode]
        if best_score * (1 - delta) > EPS:
            m.prob += m.score_expr() >= best_score * (1 - delta) - EPS
    current = [c.plan_id for c in m.cands if c.is_current]
    tie = 0.0001 * pulp.lpSum(m.x[c] for c in current)
    if has_score:
        tie = tie + 0.001 * m.score_expr()
    objective = m.cost_expr() - tie
    if not objective.keys():  # nothing to choose between
        objective = pulp.lpSum(m.x.values())
    if m.solve(pulp.LpMinimize, objective) != "Optimal":
        return None
    return m.chosen()


def _score(p: OptimizerInput, chosen: list[CandidatePlan]) -> float:
    feats = set().union(*(c.features for c in chosen)) if chosen else set()
    lines = set().union(*(c.service_lines for c in chosen)) if chosen else set()
    s = sum(w for f, w in p.weights.items() if f in feats and f not in p.must_have)
    s += sum(p.retention_lambda * u for line, u in p.current_line_usage.items() if line in lines)
    return round(s, 6)


def _portfolio(p: OptimizerInput, ids: list[str], current_feats: set[str]) -> Portfolio:
    by_id = {c.plan_id: c for c in p.candidates}
    chosen = [by_id[i] for i in ids]
    cost = sum(c.monthly_paise for c in chosen)
    feats = set().union(*(c.features for c in chosen)) if chosen else set()
    valued = set(p.must_have) | set(p.weights)
    total = cost + p.fixed_monthly_paise
    return Portfolio(
        plan_ids=sorted(ids),
        plan_names=[by_id[i].name or i for i in sorted(ids)],
        monthly_paise=cost,
        total_monthly_paise=total,
        score=_score(p, chosen),
        covered_features=sorted(feats & valued) if valued else sorted(feats),
        missing_must_have=sorted(set(p.must_have) - feats),
        missing_nice_to_have=sorted(set(p.weights) - set(p.must_have) - feats),
        lost_features=sorted((current_feats - feats) & (valued or current_feats)),
        within_budget=p.budget_paise is None or total <= p.budget_paise,
    )


def _overlaps(p: OptimizerInput, ids: list[str]) -> dict[str, list[str]]:
    by_id = {c.plan_id: c for c in p.candidates}
    counts: dict[str, list[str]] = {}
    for i in ids:
        for f in by_id[i].features:
            counts.setdefault(f, []).append(i)
    return {f: sorted(v) for f, v in sorted(counts.items()) if len(v) > 1}


def _diagnose(p: OptimizerInput) -> InfeasibilityDiagnosis:
    allowed = [c for c in p.candidates if c.plan_id not in p.excluded_plan_ids]
    coverable = set().union(*(c.features for c in allowed)) if allowed else set()
    uncoverable = sorted(set(p.must_have) - coverable)
    if uncoverable:
        return InfeasibilityDiagnosis(
            uncoverable_features=uncoverable,
            message="No usable plan provides: " + ", ".join(uncoverable) + ".",
        )
    relaxed = p.model_copy(
        update={
            "budget_paise": None,
            "weights": {},
            "current_line_usage": {},
            "mode": OptimizeMode.SAVINGS,
        }
    )
    ids = _solve_once(relaxed, [])
    if ids is None:
        return InfeasibilityDiagnosis(
            message="Your mandatory subscriptions, exclusions and eligibility rules cannot all be "
            "satisfied together with the must-have features."
        )
    by_id = {c.plan_id: c for c in p.candidates}
    min_cost = sum(by_id[i].monthly_paise for i in ids) + p.fixed_monthly_paise
    shortfall = max(0, min_cost - (p.budget_paise or 0))
    # Largest number of must-haves coverable within budget.
    m = _Model(
        p.model_copy(update={"must_have": frozenset(), "weights": dict.fromkeys(p.must_have, 1.0)}),
        [],
    )
    best_count = None
    if m.y and m.solve(pulp.LpMaximize, pulp.lpSum(m.y.values())) == "Optimal":
        best_count = round(pulp.value(pulp.lpSum(m.y.values())) or 0)
    return InfeasibilityDiagnosis(
        min_cost_for_must_haves_paise=min_cost,
        shortfall_paise=shortfall,
        max_must_haves_within_budget=best_count,
        message="Covering every must-have feature needs more than your budget.",
    )


def _rejections(p: OptimizerInput, best: list[str]) -> list[RejectedCandidate]:
    by_id = {c.plan_id: c for c in p.candidates}
    chosen = [by_id[i] for i in best]
    covered = set().union(*(c.features for c in chosen)) if chosen else set()
    groups = {c.exclusion_group: c for c in chosen}
    valued = set(p.must_have) | set(p.weights)
    cost = sum(c.monthly_paise for c in chosen) + p.fixed_monthly_paise
    out: list[RejectedCandidate] = []
    for c in p.candidates:
        if c.plan_id in best:
            continue
        if c.plan_id in p.excluded_plan_ids:
            code, why = "excluded", p.excluded_plan_ids[c.plan_id]
        elif c.exclusion_group in groups:
            other = groups[c.exclusion_group]
            code = "same_service_line"
            why = f"one plan per service; {other.name or other.plan_id} fits your needs better"
        elif not ((c.features & valued) - covered):
            code, why = "no_new_value", "adds cost but no feature you value that isn't covered"
        elif p.budget_paise is not None and cost + c.monthly_paise > p.budget_paise:
            code, why = "over_budget", "would add value but exceed your budget"
        else:
            code, why = "lower_value", "its extra features are worth less than its price"
        out.append(RejectedCandidate(plan_id=c.plan_id, name=c.name, reason_code=code, reason=why))
    return out


def solve(problem: OptimizerInput) -> OptimizationResult:
    """Solve OAVOE. Never raises for infeasibility: returns ``status='infeasible'`` with a
    diagnosis. Never invents a portfolio."""
    started = time.perf_counter()
    current_ids = [c.plan_id for c in problem.candidates if c.is_current]
    by_id = {c.plan_id: c for c in problem.candidates}
    current_feats = set().union(*(by_id[i].features for i in current_ids)) if current_ids else set()
    current = _portfolio(problem, current_ids, set()) if current_ids else None
    if not problem.candidates:
        return OptimizationResult(
            status="no_candidates",
            current=current,
            budget_paise=problem.budget_paise,
            diagnosis=InfeasibilityDiagnosis(message="No plans with usable prices are available."),
        )
    best = _solve_once(problem, [])
    if best is None:
        return OptimizationResult(
            status="infeasible",
            current=current,
            budget_paise=problem.budget_paise,
            current_overlaps=_overlaps(problem, current_ids),
            diagnosis=_diagnose(problem),
            rejected=_rejections(problem, []),
            solve_ms=round((time.perf_counter() - started) * 1000, 1),
        )
    cuts = [frozenset(best)]
    alts: list[Portfolio] = []
    for _ in range(problem.alternatives):
        nxt = _solve_once(problem, cuts)
        if nxt is None:
            break
        cuts.append(frozenset(nxt))
        alts.append(_portfolio(problem, nxt, current_feats))
    return OptimizationResult(
        status="optimal",
        best=_portfolio(problem, best, current_feats),
        alternatives=alts,
        current=current,
        budget_paise=problem.budget_paise,
        overlaps=_overlaps(problem, best),
        current_overlaps=_overlaps(problem, current_ids),
        rejected=_rejections(problem, best),
        solve_ms=round((time.perf_counter() - started) * 1000, 1),
    )


__all__ = ["solve"]
