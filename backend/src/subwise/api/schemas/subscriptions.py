"""Subscription and catalog schemas (blueprint I.2)."""

from __future__ import annotations

from datetime import date

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from subwise.api.schemas.common import Money
from subwise.core.money import Paise
from subwise.domain.enums import (
    BillingCycle,
    Category,
    Freshness,
    ObservationStatus,
    UsageFrequency,
)


class SubscriptionIn(BaseModel):
    plan_id: str | None = None
    custom_name: str | None = Field(default=None, max_length=80)
    price_paise: Paise
    billing_cycle: BillingCycle
    renewal_date: date | None = None
    usage_frequency: UsageFrequency = UsageFrequency.UNKNOWN
    is_mandatory: bool = False
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _plan_or_custom(self) -> SubscriptionIn:
        if (self.plan_id is None) == (self.custom_name is None):
            raise ValueError("Provide exactly one of plan_id or custom_name.")
        return self


class SubscriptionPatch(BaseModel):
    price_paise: Paise | None = None
    billing_cycle: BillingCycle | None = None
    renewal_date: date | None = None
    usage_frequency: UsageFrequency | None = None
    is_mandatory: bool | None = None
    notes: str | None = None
    active: bool | None = None


class SubscriptionOut(BaseModel):
    id: str
    plan_id: str | None
    display_name: str
    price: Money
    billing_cycle: BillingCycle
    monthly_equivalent: Money
    renewal_date: date | None
    usage_frequency: UsageFrequency
    is_mandatory: bool
    active: bool


class PlanPriceOut(BaseModel):
    price: Money
    status: ObservationStatus
    freshness: Freshness
    age_days: int
    source_url: str | None
    observed_at: AwareDatetime


class CatalogPlanOut(BaseModel):
    id: str
    provider_id: str
    provider_name: str
    service_line_id: str
    name: str
    category: Category
    billing_cycle: BillingCycle
    is_bundle: bool
    exclusion_group: str
    current_price: PlanPriceOut | None


class ProviderOut(BaseModel):
    id: str
    name: str
    category: Category
    official_domains: list[str]
