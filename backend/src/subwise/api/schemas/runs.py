"""Threads, runs, events, reports, dashboard and health schemas (blueprint I.2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, Field

from subwise.api.schemas.common import Money
from subwise.domain.enums import Decision, RunStatus


class ThreadIn(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class ThreadOut(BaseModel):
    thread_id: str
    title: str | None
    created_at: AwareDatetime


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    run_id: str | None
    created_at: AwareDatetime


class RunCreateIn(BaseModel):
    thread_id: str | None = None
    message: str = Field(min_length=3, max_length=2000)
    mode: Literal["auto", "savings", "balanced", "best"] = "auto"


class RunOut(BaseModel):
    run_id: str
    thread_id: str
    status: RunStatus
    request_message: str
    mode: str
    revision: int
    error_code: str | None = None
    error_message: str | None = None
    created_at: AwareDatetime
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None
    llm_model: str | None = None
    latest_report_id: str | None = None
    latest_report_status: str | None = None
    recommended_monthly: Money | None = None
    current_monthly: Money | None = None
    pending_interrupt: dict[str, Any] | None = None
    resumable: bool = False


class RunEventOut(BaseModel):
    seq: int
    node: str | None
    event_type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float | None = None
    created_at: AwareDatetime


class ClarificationIn(BaseModel):
    answers: dict[str, str] = Field(min_length=1)


class ApprovalIn(BaseModel):
    report_id: str
    decision: Decision
    reason: str | None = Field(default=None, max_length=500)
    remember: list[str] = Field(default_factory=list)


class EvidenceOut(BaseModel):
    plan_id: str
    plan_name: str
    price: Money
    billing_cycle: int
    status: str
    source_url: str | None
    observed_at: AwareDatetime
    evidence_snippet: str


class ReportOut(BaseModel):
    id: str
    run_id: str
    version: int
    status: str
    markdown: str
    generated_by: str
    current_monthly: Money
    recommended_monthly: Money | None
    result: dict[str, Any]
    facts: dict[str, Any]
    evidence: list[EvidenceOut]
    created_at: AwareDatetime


class SpendSlice(BaseModel):
    name: str
    category: str | None
    monthly: Money


class DashboardOut(BaseModel):
    monthly_spend: Money
    annual_spend: Money
    active_subscriptions: int
    renewals_next_30_days: list[dict[str, Any]]
    spend_by_subscription: list[SpendSlice]
    spend_by_category: list[SpendSlice]
    latest_report: dict[str, Any] | None
    recent_runs: list[RunOut]
    budget_monthly: Money | None
    over_budget: bool | None


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    environment: str
    database: str
    llm: dict[str, Any]
    search: Literal["enabled", "disabled"]
    playwright: Literal["enabled", "disabled"]
