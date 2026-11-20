"""Threads, runs, events, reports, prices, dashboard and health schemas (blueprint I.2)."""

from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, BaseModel, Field

from subwise.api.schemas.common import Money
from subwise.domain.enums import (
    Decision,
    EventType,
    ObservationStatus,
    OptimizeMode,
    ReportSource,
    RunStatus,
)
from subwise.domain.optimization import OptimizationResult


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
    thread_id: str
    message: str = Field(min_length=1, max_length=2000)
    mode: OptimizeMode = OptimizeMode.BEST


class RunCreatedOut(BaseModel):
    run_id: str
    status: RunStatus = RunStatus.QUEUED


class PendingInterrupt(BaseModel):
    kind: str  # "clarify" | "approval"
    payload: dict[str, Any]


class RunOut(BaseModel):
    run_id: str
    thread_id: str
    status: RunStatus
    revision: int
    error_code: str | None = None
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None
    llm_model: str | None = None
    latest_report_id: str | None = None
    pending_interrupt: PendingInterrupt | None = None


class RunEventOut(BaseModel):
    seq: int
    node: str | None
    event_type: EventType
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
    price: Money
    status: ObservationStatus
    source_url: str | None
    observed_at: AwareDatetime
    evidence_snippet: str


class ReportOut(BaseModel):
    id: str
    run_id: str
    version: int
    markdown: str
    generated_by: ReportSource
    current_monthly: Money
    recommended_monthly: Money
    result: OptimizationResult
    evidence: list[EvidenceOut]
    created_at: AwareDatetime


class PriceRefreshIn(BaseModel):
    plan_ids: list[str] | None = None


class DashboardOut(BaseModel):
    monthly_spend: Money
    annual_spend: Money
    active_subscriptions: int
    renewals_next_30_days: int
    latest_potential_saving: Money | None
    latest_report_at: AwareDatetime | None
    recent_run_ids: list[str]


class HealthOut(BaseModel):
    status: str  # "ok" | "degraded"
    version: str
    environment: str
    llm: str  # "not_checked" until M1/M7 wire the real check
    search: str  # "enabled" | "disabled"
    database: str  # "not_checked" until M2
