"""Subscriptions (M3) and read-only catalog (M4)."""

from __future__ import annotations

from fastapi import APIRouter, status

from subwise.api.deps import CurrentUser
from subwise.api.schemas.common import ERROR_RESPONSES
from subwise.api.schemas.subscriptions import (
    CatalogPlanOut,
    ProviderOut,
    SubscriptionIn,
    SubscriptionOut,
    SubscriptionPatch,
)
from subwise.domain.enums import Category
from subwise.errors import NotImplementedYet

subscriptions_router = APIRouter(
    prefix="/subscriptions", tags=["subscriptions"], responses=ERROR_RESPONSES
)
catalog_router = APIRouter(prefix="/catalog", tags=["catalog"], responses=ERROR_RESPONSES)


@subscriptions_router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(user: CurrentUser) -> list[SubscriptionOut]:
    raise NotImplementedYet("M3")


@subscriptions_router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(body: SubscriptionIn, user: CurrentUser) -> SubscriptionOut:
    raise NotImplementedYet("M3")


@subscriptions_router.patch("/{subscription_id}", response_model=SubscriptionOut)
def update_subscription(
    subscription_id: str, body: SubscriptionPatch, user: CurrentUser
) -> SubscriptionOut:
    raise NotImplementedYet("M3")


@subscriptions_router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: str, user: CurrentUser) -> None:
    raise NotImplementedYet("M3")


@catalog_router.get("/providers", response_model=list[ProviderOut])
def list_providers(user: CurrentUser) -> list[ProviderOut]:
    raise NotImplementedYet("M4")


@catalog_router.get("/plans", response_model=list[CatalogPlanOut])
def list_plans(user: CurrentUser, category: Category | None = None) -> list[CatalogPlanOut]:
    raise NotImplementedYet("M4")
