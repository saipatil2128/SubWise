"""Research evidence models (blueprint G.2-G.3, v2 evidence binding)."""

from __future__ import annotations

from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl

from subwise.core.money import Paise
from subwise.domain.enums import (
    BillingCycle,
    BindingMethod,
    ExtractedBy,
    FetchMethod,
    Freshness,
    ObservationStatus,
    PriceKind,
    TaxIncluded,
)


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requested_url: HttpUrl
    final_url: HttpUrl  # after redirects; provider binding uses THIS
    domain: str
    fetched_at: AwareDatetime
    http_status: int
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fetch_method: FetchMethod
    text_path: str | None = None


class DimensionBinding(BaseModel):
    """How one of the five evidence dimensions was bound, and by which exact text."""

    model_config = ConfigDict(extra="forbid")

    method: BindingMethod
    matched_text: str | None = None
    note: str | None = None

    @property
    def bound(self) -> bool:
        return self.method is not BindingMethod.UNBOUND


class PriceBinding(BaseModel):
    """A price is usable only when all five dimensions are bound (blueprint G.3, v2)."""

    model_config = ConfigDict(extra="forbid")

    provider: DimensionBinding
    plan: DimensionBinding
    billing_cycle: DimensionBinding
    currency: DimensionBinding
    region: DimensionBinding

    @property
    def fully_bound(self) -> bool:
        return all(
            d.bound
            for d in (self.provider, self.plan, self.billing_cycle, self.currency, self.region)
        )


class PlanObservation(BaseModel):
    """One extracted price for one plan from one source document (append-only history)."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    source_document_id: str | None  # None only for fetch_method=manual seed rows
    price_paise: Paise
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    region: str = Field(default="IN", min_length=2, max_length=2)
    billing_cycle: BillingCycle
    price_kind: PriceKind = PriceKind.STANDARD
    intro_months: int | None = Field(default=None, ge=1, le=24)
    tax_included: TaxIncluded = TaxIncluded.UNKNOWN
    evidence_snippet: str = Field(min_length=1, max_length=600)
    binding: PriceBinding
    extracted_by: ExtractedBy
    observed_at: AwareDatetime


class ValidatedPlan(BaseModel):
    observation: PlanObservation
    status: ObservationStatus
    freshness: Freshness
    age_days: int = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)


class FeatureCoverage(BaseModel):
    feature_code: str
    verified_plans: int = 0
    partial_plans: int = 0


class DataQualityReport(BaseModel):
    """Input to the guarded `decide` node (blueprint D.1)."""

    generated_at: datetime
    counts: dict[ObservationStatus, int] = Field(default_factory=dict)
    stale_or_cached: int = 0
    must_have_coverage: list[FeatureCoverage] = Field(default_factory=list)
    failed_sources: list[str] = Field(default_factory=list)

    @property
    def every_must_have_verified(self) -> bool:
        return all(c.verified_plans > 0 for c in self.must_have_coverage)
