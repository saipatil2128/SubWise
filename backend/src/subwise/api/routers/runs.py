"""Threads, runs, SSE events, clarification/approval resume, reports (M11); prices (M8);
dashboard (M3/M11)."""

from __future__ import annotations

from fastapi import APIRouter, status

from subwise.api.deps import CurrentUser
from subwise.api.schemas.common import ERROR_RESPONSES, Accepted, Page
from subwise.api.schemas.runs import (
    ApprovalIn,
    ClarificationIn,
    DashboardOut,
    MessageOut,
    PriceRefreshIn,
    ReportOut,
    RunCreatedOut,
    RunCreateIn,
    RunOut,
    ThreadIn,
    ThreadOut,
)
from subwise.api.schemas.subscriptions import PlanPriceOut
from subwise.domain.enums import RunStatus
from subwise.errors import NotImplementedYet

threads_router = APIRouter(prefix="/threads", tags=["threads"], responses=ERROR_RESPONSES)
runs_router = APIRouter(prefix="/runs", tags=["runs"], responses=ERROR_RESPONSES)
reports_router = APIRouter(prefix="/reports", tags=["reports"], responses=ERROR_RESPONSES)
prices_router = APIRouter(prefix="/prices", tags=["prices"], responses=ERROR_RESPONSES)
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"], responses=ERROR_RESPONSES)


@threads_router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(body: ThreadIn, user: CurrentUser) -> ThreadOut:
    raise NotImplementedYet("M11")


@threads_router.get("/{thread_id}/messages", response_model=list[MessageOut])
def list_messages(thread_id: str, user: CurrentUser) -> list[MessageOut]:
    raise NotImplementedYet("M11")


@runs_router.post("", response_model=RunCreatedOut, status_code=status.HTTP_202_ACCEPTED)
def create_run(body: RunCreateIn, user: CurrentUser) -> RunCreatedOut:
    """Returns immediately; 409 RUN_IN_PROGRESS if the user already has an active run."""
    raise NotImplementedYet("M11")


@runs_router.get("", response_model=Page[RunOut])
def list_runs(
    user: CurrentUser, status: RunStatus | None = None, limit: int = 20, cursor: str | None = None
) -> Page[RunOut]:
    raise NotImplementedYet("M11")


@runs_router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: str, user: CurrentUser) -> RunOut:
    raise NotImplementedYet("M11")


@runs_router.get(
    "/{run_id}/events",
    responses={200: {"content": {"text/event-stream": {}}, "description": "RunEventOut stream"}},
)
def stream_events(run_id: str, user: CurrentUser, after_seq: int = 0) -> None:
    """SSE: replay events with seq > after_seq, then stream; heartbeat every 15 s."""
    raise NotImplementedYet("M11")


@runs_router.post(
    "/{run_id}/clarification", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED
)
def answer_clarification(run_id: str, body: ClarificationIn, user: CurrentUser) -> Accepted:
    raise NotImplementedYet("M11")


@runs_router.post(
    "/{run_id}/approval", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED
)
def decide_approval(run_id: str, body: ApprovalIn, user: CurrentUser) -> Accepted:
    raise NotImplementedYet("M11")


@runs_router.post("/{run_id}/cancel", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED)
def cancel_run(run_id: str, user: CurrentUser) -> Accepted:
    raise NotImplementedYet("M11")


@reports_router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, user: CurrentUser) -> ReportOut:
    raise NotImplementedYet("M11")


@prices_router.get("", response_model=list[PlanPriceOut])
def list_prices(user: CurrentUser) -> list[PlanPriceOut]:
    raise NotImplementedYet("M8")


@prices_router.get("/{plan_id}/history", response_model=list[PlanPriceOut])
def price_history(plan_id: str, user: CurrentUser) -> list[PlanPriceOut]:
    raise NotImplementedYet("M8")


@prices_router.post("/refresh", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED)
def refresh_prices(body: PriceRefreshIn, user: CurrentUser) -> Accepted:
    raise NotImplementedYet("M8")


@dashboard_router.get("", response_model=DashboardOut)
def get_dashboard(user: CurrentUser) -> DashboardOut:
    raise NotImplementedYet("M11")
