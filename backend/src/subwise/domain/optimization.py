"""OAVOE input/output contracts (blueprint section H)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from subwise.core.money import Paise
from subwise.domain.enums import OptimizeMode


class CandidatePlan(BaseModel):
    """One element of P: a plan with a usable price and its feature row a(p, .)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    monthly_paise: Paise
    exclusion_group: str
    service_lines: frozenset[str] = Field(min_length=1)
    features: frozenset[str] = frozenset()  # only features with value == yes
    prerequisites_any_of: tuple[frozenset[str], ...] = ()  # each set: plan ids, any of which
    is_current: bool = False


class OptimizerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[CandidatePlan]
    must_have: frozenset[str] = frozenset()
    weights: dict[str, float] = Field(default_factory=dict)  # nice-to-have w(f) in (0, 1]
    budget_paise: Paise
    mandatory_plan_ids: frozenset[str] = frozenset()
    excluded_plan_ids: frozenset[str] = frozenset()
    current_line_usage: dict[str, float] = Field(default_factory=dict)  # u(s)
    retention_lambda: float = Field(default=0.5, ge=0)
    mode: OptimizeMode = OptimizeMode.BEST
    alternatives: int = Field(default=2, ge=0, le=5)

    @model_validator(mode="after")
    def _weights_in_range(self) -> OptimizerInput:
        bad = {f: w for f, w in self.weights.items() if not 0 < w <= 1}
        if bad:
            raise ValueError(f"Weights must be in (0, 1]: {bad}")
        return self


class RejectedCandidate(BaseModel):
    plan_id: str
    reason: str  # e.g. missing_must_have, adds_cost_no_new_feature, over_budget, excluded


class Portfolio(BaseModel):
    plan_ids: list[str]
    monthly_paise: Paise
    score: float
    covered_features: list[str]
    missing_nice_to_have: list[str]


class InfeasibilityDiagnosis(BaseModel):
    uncoverable_features: list[str] = Field(default_factory=list)
    min_cost_for_must_haves_paise: Paise | None = None
    shortfall_paise: Paise | None = None
    max_must_haves_within_budget: int | None = None
    message: str


class OptimizationResult(BaseModel):
    status: str = Field(pattern=r"^(optimal|infeasible)$")
    best: Portfolio | None = None
    alternatives: list[Portfolio] = Field(default_factory=list)
    current_monthly_paise: Paise = 0
    overlaps: dict[str, list[str]] = Field(default_factory=dict)  # feature -> plan ids
    rejected: list[RejectedCandidate] = Field(default_factory=list)
    diagnosis: InfeasibilityDiagnosis | None = None
    solver: str = "CBC"
    solve_ms: float = 0.0
