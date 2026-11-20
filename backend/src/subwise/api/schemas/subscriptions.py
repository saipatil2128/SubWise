"""Subscription, catalog and price schemas (blueprint I.2)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from subwise.api.schemas.common import Money
from subwise.core.money import Paise
from subwise.domain.enums import BillingCycle, Category, UsageFrequency


class SubscriptionIn(BaseModel):
    provider_id: str | None = None
    plan_id: str | None = None
    custom_name: str | None = Field(default=None, min_length=1, max_length=80)
    price_paise: Paise
    billing_cycle: BillingCycle
    renewal_date: date | None = None
    usage_frequency: UsageFrequency = UsageFrequency.UNKNOWN
    is_mandatory: bool = False
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _source(self) -> SubscriptionIn:
        """A catalog plan, OR a provider with an optional plan label (plan not fetched yet),
        OR a custom (non-catalog) subscription with a name."""
        if self.plan_id is not None and self.custom_name is not None:
            raise ValueError("A catalog plan already has a name; omit custom_name.")
        if self.provider_id is None and self.plan_id is None and self.custom_name is None:
            raise ValueError("Choose a provider/plan from the catalog or give a custom name.")
        return self


class SubscriptionPatch(BaseModel):
    plan_id: str | None = None
    price_paise: Paise | None = None
    billing_cycle: BillingCycle | None = None
    renewal_date: date | None = None
    usage_frequency: UsageFrequency | None = None
    is_mandatory: bool | None = None
    notes: str | None = None
    active: bool | None = None


class SubscriptionOut(BaseModel):
    id: str
    provider_id: str | None
    provider_name: str | None
    plan_id: str | None
    display_name: str
    category: str | None
    price: Money
    billing_cycle: BillingCycle
    monthly_equivalent: Money
    annual_cost: Money
    renewal_date: date | None
    days_to_renewal: int | None
    usage_frequency: UsageFrequency
    is_mandatory: bool
    notes: str | None
    active: bool


class AttemptOut(BaseModel):
    provider_id: str
    url: str
    outcome: str
    error: str | None
    started_at: AwareDatetime
    finished_at: AwareDatetime | None
    prices_found: int
    verified_found: int
    warnings: list[str]


class ProviderOut(BaseModel):
    id: str
    name: str
    category: Category
    pricing_url: str
    needs_js: bool
    latest_attempt: AttemptOut | None


class PlanPriceOut(BaseModel):
    plan_id: str
    provider_id: str
    provider_name: str
    plan_name: str
    billing_cycle: int
    price: Money
    monthly: Money
    annual: Money
    status: str
    label: str
    observed_at: AwareDatetime
    age_days: int
    source_url: str | None
    evidence: str
    features: dict[str, str]
    intro: dict[str, Any] | None = None


class PriceHistoryPoint(BaseModel):
    observed_at: AwareDatetime
    price: Money
    kind: str
    status: str
    evidence: str


class PriceRefreshIn(BaseModel):
    provider_ids: list[str] | None = None


class RefreshOut(BaseModel):
    provider_id: str
    outcome: str
    prices_found: int
    verified: int
    error: str | None
    warnings: list[str]
