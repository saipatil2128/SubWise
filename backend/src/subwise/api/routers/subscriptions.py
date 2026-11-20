"""Subscriptions (user data) and the live catalog / price intelligence."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from subwise.api.deps import ContainerDep, CurrentUser, DbDep
from subwise.api.schemas.common import ERROR_RESPONSES, Money
from subwise.api.schemas.subscriptions import (
    AttemptOut,
    PlanPriceOut,
    PriceHistoryPoint,
    PriceRefreshIn,
    ProviderOut,
    RefreshOut,
    SubscriptionIn,
    SubscriptionOut,
    SubscriptionPatch,
)
from subwise.core.costing import annual_cost
from subwise.core.money import format_inr
from subwise.db import repositories as repo
from subwise.db.models import FetchAttempt, Plan, UserSubscription
from subwise.domain.enums import BillingCycle
from subwise.errors import NotFound, ValidationFailed
from subwise.ids import new_id
from subwise.research.registry import PROVIDERS, PROVIDERS_BY_ID
from subwise.services.prices import PlanPrice

subscriptions_router = APIRouter(
    prefix="/subscriptions", tags=["subscriptions"], responses=ERROR_RESPONSES
)
catalog_router = APIRouter(prefix="/catalog", tags=["catalog"], responses=ERROR_RESPONSES)
prices_router = APIRouter(prefix="/prices", tags=["prices"], responses=ERROR_RESPONSES)


def money(paise: int) -> Money:
    return Money(paise=paise, display=format_inr(paise))


def _days_to(d: date | None) -> int | None:
    if d is None:
        return None
    return (d - datetime.now(UTC).date()).days


def _sub_out(v: dict[str, Any]) -> SubscriptionOut:
    price = int(v["price_paise"])
    cycle = int(v["billing_cycle_months"])
    renewal = date.fromisoformat(str(v["renewal_date"])) if v["renewal_date"] else None
    return SubscriptionOut(
        id=str(v["id"]),
        provider_id=v["provider_id"],
        provider_name=v["provider_name"],
        plan_id=v["plan_id"],
        display_name=str(v["display_name"]),
        category=v["category"],
        price=money(price),
        billing_cycle=BillingCycle(cycle),
        monthly_equivalent=money(int(v["monthly_paise"])),
        annual_cost=money(annual_cost(price, cycle)),
        renewal_date=renewal,
        days_to_renewal=_days_to(renewal),
        usage_frequency=v["usage_frequency"],
        is_mandatory=bool(v["is_mandatory"]),
        notes=v["notes"],
        active=bool(v["active"]),
    )


def _validate_catalog_refs(db: DbDep, provider_id: str | None, plan_id: str | None) -> str | None:
    if plan_id is not None:
        plan = db.get(Plan, plan_id)
        if plan is None:
            raise ValidationFailed("Unknown plan.", details={"plan_id": plan_id})
        if provider_id and provider_id != plan.provider_id:
            raise ValidationFailed("Plan does not belong to that provider.")
        return plan.provider_id
    if provider_id is not None and provider_id not in PROVIDERS_BY_ID:
        raise ValidationFailed("Unknown provider.", details={"provider_id": provider_id})
    return provider_id


@subscriptions_router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(user: CurrentUser, db: DbDep) -> list[SubscriptionOut]:
    return [
        _sub_out(repo.subscription_view(db, s)) for s in repo.list_subscriptions(db, user.user_id)
    ]


@subscriptions_router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(body: SubscriptionIn, user: CurrentUser, db: DbDep) -> SubscriptionOut:
    provider_id = _validate_catalog_refs(db, body.provider_id, body.plan_id)
    sub = UserSubscription(
        id=new_id("sub"),
        user_id=user.user_id,
        plan_id=body.plan_id,
        provider_id=provider_id,
        custom_name=body.custom_name,
        price_paise=body.price_paise,
        billing_cycle_months=int(body.billing_cycle),
        renewal_date=body.renewal_date,
        usage_frequency=body.usage_frequency.value,
        is_mandatory=body.is_mandatory,
        notes=body.notes,
        active=True,
    )
    db.add(sub)
    db.flush()
    return _sub_out(repo.subscription_view(db, sub))


@subscriptions_router.patch("/{subscription_id}", response_model=SubscriptionOut)
def update_subscription(
    subscription_id: str, body: SubscriptionPatch, user: CurrentUser, db: DbDep
) -> SubscriptionOut:
    sub = repo.get_subscription(db, user.user_id, subscription_id)
    data = body.model_dump(exclude_unset=True)
    if "plan_id" in data:
        sub.provider_id = _validate_catalog_refs(db, sub.provider_id, data["plan_id"]) or (
            sub.provider_id
        )
    for field, value in data.items():
        if field == "billing_cycle":
            sub.billing_cycle_months = int(value)
        elif field == "usage_frequency":
            sub.usage_frequency = value.value if hasattr(value, "value") else value
        else:
            setattr(sub, field, value)
    db.flush()
    return _sub_out(repo.subscription_view(db, sub))


@subscriptions_router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: str, user: CurrentUser, db: DbDep) -> Response:
    db.delete(repo.get_subscription(db, user.user_id, subscription_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------------------- catalog
def _attempt_out(a: FetchAttempt) -> AttemptOut:
    return AttemptOut(
        provider_id=a.provider_id,
        url=a.url,
        outcome=a.outcome,
        error=a.error,
        started_at=a.started_at,
        finished_at=a.finished_at,
        prices_found=a.prices_found,
        verified_found=a.verified_found,
        warnings=list(a.warnings or []),
    )


def _price_out(p: PlanPrice) -> PlanPriceOut:
    return PlanPriceOut(
        plan_id=p.plan_id,
        provider_id=p.provider_id,
        provider_name=p.provider_name,
        plan_name=p.plan_name,
        billing_cycle=p.billing_cycle_months,
        price=money(p.price_paise),
        monthly=money(p.monthly_paise),
        annual=money(annual_cost(p.price_paise, p.billing_cycle_months)),
        status=p.status,
        label=p.label,
        observed_at=p.observed_at,
        age_days=p.age_days,
        source_url=p.source_url,
        evidence=p.evidence_snippet,
        features=p.features,
        intro=(
            {**p.intro, "price_display": format_inr(int(p.intro["price_paise"]))}
            if p.intro and p.intro.get("price_paise") is not None
            else p.intro
        ),
    )


@catalog_router.get("/providers", response_model=list[ProviderOut])
def list_providers(user: CurrentUser, c: ContainerDep) -> list[ProviderOut]:
    attempts = c.prices.latest_attempts()
    return [
        ProviderOut(
            id=p.id,
            name=p.name,
            category=p.category,
            pricing_url=p.pricing_url,
            needs_js=p.needs_js,
            latest_attempt=_attempt_out(attempts[p.id]) if p.id in attempts else None,
        )
        for p in PROVIDERS
    ]


@catalog_router.get("/plans", response_model=list[PlanPriceOut])
def list_plans(
    user: CurrentUser, c: ContainerDep, provider_id: str | None = None
) -> list[PlanPriceOut]:
    return [
        _price_out(p)
        for p in c.prices.plan_prices()
        if provider_id is None or p.provider_id == provider_id
    ]


@prices_router.get("", response_model=list[PlanPriceOut])
def list_prices(user: CurrentUser, c: ContainerDep) -> list[PlanPriceOut]:
    return [_price_out(p) for p in c.prices.plan_prices()]


@prices_router.get("/{plan_id}/history", response_model=list[PriceHistoryPoint])
def price_history(
    plan_id: str, user: CurrentUser, c: ContainerDep, db: DbDep
) -> list[PriceHistoryPoint]:
    if db.get(Plan, plan_id) is None:
        raise NotFound("Plan not found.")
    return [
        PriceHistoryPoint(
            observed_at=o.observed_at,
            price=money(o.price_paise),
            kind=o.price_kind,
            status=o.status,
            evidence=o.evidence_snippet,
        )
        for o in c.prices.history(plan_id)
    ]


@prices_router.post("/refresh", response_model=list[RefreshOut])
async def refresh_prices(
    body: PriceRefreshIn, user: CurrentUser, c: ContainerDep
) -> list[RefreshOut]:
    ids = body.provider_ids or [p.id for p in PROVIDERS]
    unknown = [i for i in ids if i not in PROVIDERS_BY_ID]
    if unknown:
        raise ValidationFailed("Unknown providers.", details={"unknown": unknown})
    results = await run_in_threadpool(c.prices.refresh, ids)
    return [
        RefreshOut(
            provider_id=r.provider_id,
            outcome=r.outcome,
            prices_found=r.prices_found,
            verified=r.verified,
            error=r.error,
            warnings=r.warnings,
        )
        for r in results
    ]


@prices_router.get("/attempts", response_model=list[AttemptOut])
def list_attempts(user: CurrentUser, db: DbDep, limit: int = 50) -> list[AttemptOut]:
    rows = db.scalars(
        select(FetchAttempt)
        .where(FetchAttempt.outcome != "running")
        .order_by(FetchAttempt.started_at.desc())
        .limit(min(limit, 200))
    ).all()
    return [_attempt_out(a) for a in rows]
