"""User-scoped data access. Every function that touches user data takes ``user_id`` and filters
by it, so one account can never read or change another's rows (blueprint J.3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from subwise.core.costing import monthly_equivalent
from subwise.db.models import (
    Conversation,
    FeatureRequirement,
    OptimizationRun,
    Plan,
    PlanFeature,
    Provider,
    Report,
    RunEvent,
    User,
    UserProfile,
    UserSubscription,
)
from subwise.errors import NotFound


def get_user(s: Session, user_id: str) -> User:
    user = s.get(User, user_id)
    if user is None:
        raise NotFound("User not found.")
    return user


def get_or_create_profile(s: Session, user_id: str) -> UserProfile:
    prof = s.get(UserProfile, user_id)
    if prof is None:
        prof = UserProfile(user_id=user_id, eligibility=[])
        s.add(prof)
        s.flush()
    return prof


def list_requirements(s: Session, user_id: str) -> list[FeatureRequirement]:
    return list(s.scalars(select(FeatureRequirement).where(FeatureRequirement.user_id == user_id)))


def replace_requirements(s: Session, user_id: str, items: list[dict[str, Any]]) -> None:
    for r in list_requirements(s, user_id):
        s.delete(r)
    s.flush()
    for it in items:
        s.add(
            FeatureRequirement(
                user_id=user_id,
                feature_code=it["feature_code"],
                level=it["level"],
                weight=it["weight"],
            )
        )


def list_subscriptions(
    s: Session, user_id: str, *, active_only: bool = False
) -> list[UserSubscription]:
    q = select(UserSubscription).where(UserSubscription.user_id == user_id)
    if active_only:
        q = q.where(UserSubscription.active.is_(True))
    return list(s.scalars(q.order_by(UserSubscription.created_at)))


def get_subscription(s: Session, user_id: str, sub_id: str) -> UserSubscription:
    sub = s.get(UserSubscription, sub_id)
    if sub is None or sub.user_id != user_id:
        raise NotFound("Subscription not found.")
    return sub


def get_conversation(s: Session, user_id: str, thread_id: str) -> Conversation:
    conv = s.get(Conversation, thread_id)
    if conv is None or conv.user_id != user_id:
        raise NotFound("Conversation not found.")
    return conv


def get_run(s: Session, user_id: str, run_id: str) -> OptimizationRun:
    run = s.get(OptimizationRun, run_id)
    if run is None or run.user_id != user_id:
        raise NotFound("Run not found.")
    return run


def get_report(s: Session, user_id: str, report_id: str) -> Report:
    rep = s.get(Report, report_id)
    if rep is None or rep.user_id != user_id:
        raise NotFound("Report not found.")
    return rep


def latest_report(s: Session, run_id: str) -> Report | None:
    return s.scalars(
        select(Report).where(Report.run_id == run_id).order_by(Report.version.desc()).limit(1)
    ).first()


def next_event_seq(s: Session, run_id: str) -> int:
    cur = s.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id))
    return (cur or 0) + 1


def plan_features(s: Session, plan_id: str) -> dict[str, str]:
    return {
        f.feature_code: f.value
        for f in s.scalars(select(PlanFeature).where(PlanFeature.plan_id == plan_id))
    }


def subscription_view(s: Session, sub: UserSubscription) -> dict[str, Any]:
    plan = s.get(Plan, sub.plan_id) if sub.plan_id else None
    provider_id = plan.provider_id if plan else sub.provider_id
    prov = s.get(Provider, provider_id) if provider_id else None
    if plan is not None:
        name = plan.name
    elif prov is not None and sub.custom_name:
        label = sub.custom_name
        name = label if label.lower().startswith(prov.name.lower()) else f"{prov.name} {label}"
    else:
        name = sub.custom_name or (prov.name if prov else "Subscription")
    return {
        "id": sub.id,
        "plan_id": sub.plan_id,
        "provider_id": provider_id,
        "provider_name": prov.name if prov else None,
        "display_name": name,
        "price_paise": sub.price_paise,
        "billing_cycle_months": sub.billing_cycle_months,
        "monthly_paise": monthly_equivalent(sub.price_paise, sub.billing_cycle_months).paise,
        "renewal_date": sub.renewal_date.isoformat() if sub.renewal_date else None,
        "usage_frequency": sub.usage_frequency,
        "is_mandatory": sub.is_mandatory,
        "notes": sub.notes,
        "active": sub.active,
        "service_line_id": plan.service_line_id
        if plan
        else (prov.service_line_id if prov else None),
        "category": prov.category if prov else None,
    }
