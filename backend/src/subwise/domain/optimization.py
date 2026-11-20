"""OAVOE input/output contracts (blueprint section H, v2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from subwise.domain.enums import OptimizeMode


class CandidatePlan(BaseModel):
    """One element of P: a plan with a usable monthly-equivalent price and its feature row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    name: str = ""
    monthly_paise: int = Field(ge=0)
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
    budget_paise: int | None = Field(default=None, ge=0)  # None = no budget limit
    fixed_monthly_paise: int = Field(default=0, ge=0)  # kept subscriptions outside the catalog
    mandatory_plan_ids: frozenset[str] = frozenset()
    excluded_plan_ids: dict[str, str] = Field(default_factory=dict)  # plan_id -> reason
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
    name: str = ""
    reason_code: str
    reason: str


class Portfolio(BaseModel):
    plan_ids: list[str]
    plan_names: list[str] = Field(default_factory=list)
    monthly_paise: int  # catalog plans only
    total_monthly_paise: int  # including fixed subscriptions kept outside the catalog
    score: float
    covered_features: list[str]
    missing_must_have: list[str] = Field(default_factory=list)
    missing_nice_to_have: list[str]
    lost_features: list[str] = Field(
        default_factory=list
    )  # valued features current has, this lacks
    within_budget: bool = True


class InfeasibilityDiagnosis(BaseModel):
    uncoverable_features: list[str] = Field(default_factory=list)
    min_cost_for_must_haves_paise: int | None = None
    shortfall_paise: int | None = None
    max_must_haves_within_budget: int | None = None
    message: str


class OptimizationResult(BaseModel):
    status: str = Field(pattern=r"^(optimal|infeasible|no_candidates)$")
    best: Portfolio | None = None
    alternatives: list[Portfolio] = Field(default_factory=list)
    current: Portfolio | None = None
    budget_paise: int | None = None
    overlaps: dict[str, list[str]] = Field(default_factory=dict)  # chosen: feature -> plan ids
    current_overlaps: dict[str, list[str]] = Field(default_factory=dict)
    rejected: list[RejectedCandidate] = Field(default_factory=list)
    diagnosis: InfeasibilityDiagnosis | None = None
    solver: str = "CBC"
    solve_ms: float = 0.0
