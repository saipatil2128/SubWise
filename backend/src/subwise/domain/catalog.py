"""Catalog vocabulary (blueprint H.2, v2): provider -> service line -> plan -> entitlements.

Key rule: a *provider* never forms an exclusion group by itself. Only plans that one account
cannot hold together share an ``exclusion_group`` (tiers, cycles, individual/family variants
of one service line). Bundles are ordinary plans with several entitlements.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from subwise.domain.enums import BillingCycle, Category, Eligibility, FeatureValue


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Provider(_Frozen):
    id: str
    name: str
    category: Category
    official_domains: tuple[str, ...] = Field(min_length=1)
    country: str = "IN"
    adapter_key: str | None = None
    needs_js: bool = False


class ServiceLine(_Frozen):
    """One product a person subscribes to, e.g. 'Netflix streaming', 'Prime membership'."""

    id: str
    provider_id: str
    name: str
    category: Category


class Entitlement(_Frozen):
    """A service line (and tier label) granted by a plan. A bundle grants several."""

    service_line_id: str
    tier: str | None = None


class Prerequisite(_Frozen):
    """Add-on rule: the plan is selectable only if ANY of these plans/lines is selected."""

    any_of_plan_ids: tuple[str, ...] = ()
    any_of_service_line_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _non_empty(self) -> Prerequisite:
        if not (self.any_of_plan_ids or self.any_of_service_line_ids):
            raise ValueError("A prerequisite must name at least one plan or service line.")
        return self


class PlanFeature(_Frozen):
    feature_code: str
    value: FeatureValue
    detail: str | None = None  # e.g. "screens=2"


class Plan(_Frozen):
    id: str
    provider_id: str
    service_line_id: str
    name: str
    aliases: tuple[str, ...] = ()
    billing_cycle: BillingCycle
    official_url: HttpUrl | None = None
    exclusion_group: str | None = None
    """Plans sharing this key are mutually exclusive. ``None`` => defaults to service_line_id."""
    entitlements: tuple[Entitlement, ...] = Field(min_length=1)
    prerequisites: tuple[Prerequisite, ...] = ()
    eligibility: tuple[Eligibility, ...] = ()
    features: tuple[PlanFeature, ...] = ()
    active: bool = True

    @property
    def effective_exclusion_group(self) -> str:
        return self.exclusion_group or self.service_line_id

    @property
    def is_bundle(self) -> bool:
        return len({e.service_line_id for e in self.entitlements}) >= 2
