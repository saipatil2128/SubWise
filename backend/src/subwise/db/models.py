"""SQLAlchemy models (blueprint E, v2). Money columns are INTEGER paise; timestamps UTC.

Every user-owned table carries ``user_id``; access goes through user-scoped queries in
``subwise.db.repositories``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from subwise.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC in SQLite, always returns timezone-aware UTC datetimes."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime given to UTCDateTime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


# ----------------------------------------------------------------------------- accounts
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    country: Mapped[str] = mapped_column(String(2), default="IN")
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    budget_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_period: Mapped[str] = mapped_column(String(8), default="monthly")  # monthly|annual
    billing_preference: Mapped[str] = mapped_column(String(8), default="any")
    ads_tolerance: Mapped[str] = mapped_column(String(8), default="ok")
    allow_cached_prices: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_partial_prices: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_unverified_prices: Mapped[bool] = mapped_column(Boolean, default=False)
    eligibility: Mapped[list[str]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class FeatureRequirement(Base):
    __tablename__ = "feature_requirements"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    feature_code: Mapped[str] = mapped_column(String(40), primary_key=True)
    level: Mapped[str] = mapped_column(String(8))  # must|nice|none
    weight: Mapped[float] = mapped_column(Float, default=0.5)


# ----------------------------------------------------------------------------- catalog
class Provider(Base):
    __tablename__ = "providers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(16))
    official_domains: Mapped[list[str]] = mapped_column(JSON)
    pricing_url: Mapped[str] = mapped_column(String(500))
    needs_js: Mapped[bool] = mapped_column(Boolean, default=False)
    service_line_id: Mapped[str] = mapped_column(String(60))


class ServiceLine(Base):
    __tablename__ = "service_lines"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(16))


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)  # provider:tier:cycle
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    service_line_id: Mapped[str] = mapped_column(ForeignKey("service_lines.id"))
    tier_key: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    billing_cycle_months: Mapped[int] = mapped_column(Integer)
    exclusion_group: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entitled_lines: Mapped[list[str]] = mapped_column(JSON, default=list)
    prerequisites: Mapped[list[list[str]]] = mapped_column(JSON, default=list)
    eligibility: Mapped[list[str]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class PlanFeature(Base):
    __tablename__ = "plan_features"
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), primary_key=True
    )
    feature_code: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(8))  # yes|no|unknown
    source: Mapped[str] = mapped_column(String(12))  # defining|extracted
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class SourceDocument(Base):
    __tablename__ = "source_documents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    requested_url: Mapped[str] = mapped_column(String(500))
    final_url: Mapped[str] = mapped_column(String(500))
    http_status: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    fetch_method: Mapped[str] = mapped_column(String(12))
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime())
    path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class FetchAttempt(Base):
    __tablename__ = "fetch_attempts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    run_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(500))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16))  # success|no_prices|failed|disallowed|needs_js
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prices_found: Mapped[int] = mapped_column(Integer, default=0)
    verified_found: Mapped[int] = mapped_column(Integer, default=0)
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_documents.id"), nullable=True
    )
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)


class PriceObservation(Base):
    __tablename__ = "price_observations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), index=True)
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_documents.id"), nullable=True
    )
    fetch_attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("fetch_attempts.id"), nullable=True
    )
    price_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    region: Mapped[str] = mapped_column(String(2), default="IN")
    billing_cycle_months: Mapped[int] = mapped_column(Integer)
    price_kind: Mapped[str] = mapped_column(String(10))
    intro_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tax_included: Mapped[str] = mapped_column(String(8), default="unknown")
    evidence_snippet: Mapped[str] = mapped_column(Text)
    binding: Mapped[dict[str, Any]] = mapped_column(JSON)
    extracted_by: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(12))
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)

    __table_args__ = (Index("ix_obs_plan_time", "plan_id", "observed_at"),)


# ----------------------------------------------------------------------------- user data
class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("plans.id"), nullable=True)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"), nullable=True)
    custom_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    price_paise: Mapped[int] = mapped_column(Integer)
    billing_cycle_months: Mapped[int] = mapped_column(Integer)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    usage_frequency: Mapped[str] = mapped_column(String(14), default="unknown")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # thread_id
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    run_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # run_id = workflow_id
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(24), index=True)
    request_message: Mapped[str] = mapped_column(Text)
    request_spec: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(10), default="best")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_interrupt: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class RunEvent(Base):
    __tablename__ = "run_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("optimization_runs.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)
    node: Mapped[str | None] = mapped_column(String(40), nullable=True)
    event_type: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    __table_args__ = (UniqueConstraint("run_id", "seq"),)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("optimization_runs.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    facts: Mapped[dict[str, Any]] = mapped_column(JSON)
    markdown: Mapped[str] = mapped_column(Text)
    generated_by: Mapped[str] = mapped_column(String(10))
    current_monthly_paise: Mapped[int] = mapped_column(Integer)
    recommended_monthly_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|approved|rejected
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class ReportEvidence(Base):
    __tablename__ = "report_evidence"
    report_id: Mapped[str] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    price_observation_id: Mapped[str] = mapped_column(
        ForeignKey("price_observations.id"), primary_key=True
    )


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("optimization_runs.id", ondelete="CASCADE"))
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
