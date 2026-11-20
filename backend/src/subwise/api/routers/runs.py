"""Threads, optimization runs, live events (SSE), clarification/approval, reports, dashboard."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from subwise.api.deps import ContainerDep, CurrentUser, DbDep
from subwise.api.schemas.common import ERROR_RESPONSES, Accepted, Money
from subwise.api.schemas.runs import (
    ApprovalIn,
    ClarificationIn,
    DashboardOut,
    EvidenceOut,
    MessageOut,
    ReportOut,
    RunCreateIn,
    RunEventOut,
    RunOut,
    SpendSlice,
    ThreadIn,
    ThreadOut,
)
from subwise.core.money import format_inr
from subwise.db import repositories as repo
from subwise.db.models import (
    Conversation,
    Message,
    OptimizationRun,
    Plan,
    PriceObservation,
    Report,
    ReportEvidence,
    RunEvent,
    SourceDocument,
)
from subwise.db.session import session_scope
from subwise.domain.enums import RunStatus
from subwise.errors import Conflict, NotFound
from subwise.ids import new_id

threads_router = APIRouter(prefix="/threads", tags=["threads"], responses=ERROR_RESPONSES)
runs_router = APIRouter(prefix="/runs", tags=["runs"], responses=ERROR_RESPONSES)
reports_router = APIRouter(prefix="/reports", tags=["reports"], responses=ERROR_RESPONSES)
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"], responses=ERROR_RESPONSES)

ACTIVE = {RunStatus.QUEUED.value, RunStatus.RUNNING.value}
TERMINAL = {RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value}


def money(paise: int) -> Money:
    return Money(paise=paise, display=format_inr(paise))


def _run_out(db: DbDep, run: OptimizationRun) -> RunOut:
    rep = repo.latest_report(db, run.id)
    return RunOut(
        run_id=run.id,
        thread_id=run.thread_id,
        status=RunStatus(run.status),
        request_message=run.request_message,
        mode=run.mode,
        revision=run.revision,
        error_code=run.error_code,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        ended_at=run.ended_at,
        llm_model=run.llm_model,
        latest_report_id=rep.id if rep else None,
        latest_report_status=rep.status if rep else None,
        recommended_monthly=money(rep.recommended_monthly_paise)
        if rep and rep.recommended_monthly_paise is not None
        else None,
        current_monthly=money(rep.current_monthly_paise) if rep else None,
        pending_interrupt=run.pending_interrupt,
        resumable=run.status == RunStatus.FAILED.value and run.error_code == "WORKER_LOST",
    )


# ----------------------------------------------------------------------------- threads
@threads_router.get("", response_model=list[ThreadOut])
def list_threads(user: CurrentUser, db: DbDep) -> list[ThreadOut]:
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.user_id)
        .order_by(Conversation.created_at.desc())
    ).all()
    return [ThreadOut(thread_id=c.id, title=c.title, created_at=c.created_at) for c in rows]


@threads_router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(body: ThreadIn, user: CurrentUser, db: DbDep) -> ThreadOut:
    conv = Conversation(id=new_id("thr"), user_id=user.user_id, title=body.title)
    db.add(conv)
    db.flush()
    return ThreadOut(thread_id=conv.id, title=conv.title, created_at=conv.created_at)


@threads_router.get("/{thread_id}/messages", response_model=list[MessageOut])
def list_messages(thread_id: str, user: CurrentUser, db: DbDep) -> list[MessageOut]:
    repo.get_conversation(db, user.user_id, thread_id)
    rows = db.scalars(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)
    ).all()
    return [
        MessageOut(
            id=m.id, role=m.role, content=m.content, run_id=m.run_id, created_at=m.created_at
        )
        for m in rows
    ]


# ----------------------------------------------------------------------------- runs
@runs_router.post("", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
def create_run(body: RunCreateIn, user: CurrentUser, db: DbDep, c: ContainerDep) -> RunOut:
    busy = db.scalar(
        select(OptimizationRun).where(
            OptimizationRun.user_id == user.user_id, OptimizationRun.status.in_(ACTIVE)
        )
    )
    if busy is not None:
        raise Conflict("You already have a run in progress.", details={"run_id": busy.id})
    if body.thread_id:
        thread_id = repo.get_conversation(db, user.user_id, body.thread_id).id
    else:
        conv = Conversation(id=new_id("thr"), user_id=user.user_id, title=body.message[:60])
        db.add(conv)
        db.flush()
        thread_id = conv.id
    run = OptimizationRun(
        id=new_id("run"),
        user_id=user.user_id,
        thread_id=thread_id,
        status=RunStatus.QUEUED.value,
        request_message=body.message,
        mode=body.mode,
    )
    db.add(run)
    db.add(
        Message(
            id=new_id("msg"),
            thread_id=thread_id,
            user_id=user.user_id,
            role="user",
            content=body.message,
            run_id=run.id,
        )
    )
    db.commit()
    c.worker.start(run.id, user.user_id)
    return _run_out(db, run)


@runs_router.get("", response_model=list[RunOut])
def list_runs(user: CurrentUser, db: DbDep, limit: int = 30) -> list[RunOut]:
    rows = db.scalars(
        select(OptimizationRun)
        .where(OptimizationRun.user_id == user.user_id)
        .order_by(OptimizationRun.created_at.desc())
        .limit(min(limit, 100))
    ).all()
    return [_run_out(db, r) for r in rows]


@runs_router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: str, user: CurrentUser, db: DbDep) -> RunOut:
    return _run_out(db, repo.get_run(db, user.user_id, run_id))


@runs_router.get("/{run_id}/events/list", response_model=list[RunEventOut])
def list_events(run_id: str, user: CurrentUser, db: DbDep, after_seq: int = 0) -> list[RunEventOut]:
    repo.get_run(db, user.user_id, run_id)
    rows = db.scalars(
        select(RunEvent)
        .where(RunEvent.run_id == run_id, RunEvent.seq > after_seq)
        .order_by(RunEvent.seq)
    ).all()
    return [_event_out(e) for e in rows]


def _event_out(e: RunEvent) -> RunEventOut:
    return RunEventOut(
        seq=e.seq,
        node=e.node,
        event_type=e.event_type,
        message=e.message,
        payload=e.payload or {},
        duration_ms=e.duration_ms,
        created_at=e.created_at,
    )


@runs_router.get(
    "/{run_id}/events",
    responses={200: {"content": {"text/event-stream": {}}, "description": "RunEventOut stream"}},
)
async def stream_events(
    run_id: str, request: Request, user: CurrentUser, c: ContainerDep, after_seq: int = 0
) -> StreamingResponse:
    """Server-Sent Events: replays events after ``after_seq`` then streams new ones (polling
    the event table every 0.5 s). Ends shortly after the run pauses or finishes."""
    with session_scope(c.session_factory) as s:
        repo.get_run(s, user.user_id, run_id)

    async def gen() -> AsyncIterator[str]:
        last = after_seq
        idle_after_stop = 0
        beat = 0.0
        while True:
            if await request.is_disconnected():
                return
            with session_scope(c.session_factory) as s:
                rows = s.scalars(
                    select(RunEvent)
                    .where(RunEvent.run_id == run_id, RunEvent.seq > last)
                    .order_by(RunEvent.seq)
                ).all()
                run = s.get(OptimizationRun, run_id)
                status_now = run.status if run else RunStatus.FAILED.value
                payloads = [_event_out(e).model_dump(mode="json") for e in rows]
            for p in payloads:
                last = p["seq"]
                yield f"id: {last}\nevent: run_event\ndata: {json.dumps(p)}\n\n"
            stopped = status_now in TERMINAL or status_now.startswith("waiting")
            if stopped and not payloads:
                idle_after_stop += 1
                if idle_after_stop >= 2:
                    yield f"event: run_status\ndata: {json.dumps({'status': status_now})}\n\n"
                    return
            beat += 0.5
            if beat >= 15:
                beat = 0.0
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@runs_router.post(
    "/{run_id}/clarification", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED
)
def answer_clarification(
    run_id: str, body: ClarificationIn, user: CurrentUser, db: DbDep, c: ContainerDep
) -> Accepted:
    run = repo.get_run(db, user.user_id, run_id)
    if run.status != RunStatus.WAITING_CLARIFICATION.value:
        raise Conflict("This run is not waiting for clarification.")
    db.add(
        Message(
            id=new_id("msg"),
            thread_id=run.thread_id,
            user_id=user.user_id,
            role="user",
            content="; ".join(f"{k}: {v}" for k, v in body.answers.items()),
            run_id=run_id,
        )
    )
    run.status = RunStatus.QUEUED.value
    db.commit()
    c.worker.resume(run_id, user.user_id, {"answers": body.answers})
    return Accepted()


@runs_router.post(
    "/{run_id}/approval", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED
)
def decide_approval(
    run_id: str, body: ApprovalIn, user: CurrentUser, db: DbDep, c: ContainerDep
) -> Accepted:
    run = repo.get_run(db, user.user_id, run_id)
    if run.status != RunStatus.WAITING_APPROVAL.value:
        raise Conflict("This run is not waiting for approval.")
    pending = run.pending_interrupt or {}
    if pending.get("report_id") != body.report_id:
        raise Conflict("That report is not the latest version for this run.")
    run.status = RunStatus.QUEUED.value
    db.commit()
    c.worker.resume(
        run_id,
        user.user_id,
        {"decision": body.decision.value, "reason": body.reason or "", "remember": body.remember},
    )
    return Accepted()


@runs_router.post("/{run_id}/cancel", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED)
def cancel_run(run_id: str, user: CurrentUser, db: DbDep) -> Accepted:
    run = repo.get_run(db, user.user_id, run_id)
    if run.status in TERMINAL:
        raise Conflict("This run has already finished.")
    if run.status == RunStatus.RUNNING.value:
        raise Conflict("A running step cannot be stopped midway; cancel when it pauses.")
    run.status = RunStatus.CANCELLED.value
    run.ended_at = datetime.now(UTC)
    run.pending_interrupt = None
    return Accepted()


@runs_router.post("/{run_id}/resume", response_model=Accepted, status_code=status.HTTP_202_ACCEPTED)
def resume_run(run_id: str, user: CurrentUser, db: DbDep, c: ContainerDep) -> Accepted:
    """Continue a run interrupted by a server restart from its last checkpoint."""
    run = repo.get_run(db, user.user_id, run_id)
    if not (run.status == RunStatus.FAILED.value and run.error_code == "WORKER_LOST"):
        raise Conflict("Only runs interrupted by a server restart can be resumed.")
    run.status, run.error_code, run.error_message = RunStatus.QUEUED.value, None, None
    db.commit()
    c.worker.continue_from_checkpoint(run_id, user.user_id)
    return Accepted()


@runs_router.get("/{run_id}/reports", response_model=list[ReportOut])
def run_reports(run_id: str, user: CurrentUser, db: DbDep) -> list[ReportOut]:
    repo.get_run(db, user.user_id, run_id)
    rows = db.scalars(select(Report).where(Report.run_id == run_id).order_by(Report.version)).all()
    return [_report_out(db, r) for r in rows]


# ----------------------------------------------------------------------------- reports
def _report_out(db: DbDep, rep: Report) -> ReportOut:
    evidence = []
    for link in db.scalars(select(ReportEvidence).where(ReportEvidence.report_id == rep.id)):
        o = db.get(PriceObservation, link.price_observation_id)
        if o is None:
            continue
        plan = db.get(Plan, o.plan_id)
        doc = db.get(SourceDocument, o.source_document_id) if o.source_document_id else None
        evidence.append(
            EvidenceOut(
                plan_id=o.plan_id,
                plan_name=plan.name if plan else o.plan_id,
                price=money(o.price_paise),
                billing_cycle=o.billing_cycle_months,
                status=o.status,
                source_url=doc.final_url if doc else None,
                observed_at=o.observed_at,
                evidence_snippet=o.evidence_snippet,
            )
        )
    return ReportOut(
        id=rep.id,
        run_id=rep.run_id,
        version=rep.version,
        status=rep.status,
        markdown=rep.markdown,
        generated_by=rep.generated_by,
        current_monthly=money(rep.current_monthly_paise),
        recommended_monthly=money(rep.recommended_monthly_paise)
        if rep.recommended_monthly_paise is not None
        else None,
        result=rep.result,
        facts=rep.facts,
        evidence=evidence,
        created_at=rep.created_at,
    )


@reports_router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, user: CurrentUser, db: DbDep) -> ReportOut:
    return _report_out(db, repo.get_report(db, user.user_id, report_id))


# ----------------------------------------------------------------------------- dashboard
@dashboard_router.get("", response_model=DashboardOut)
def get_dashboard(user: CurrentUser, db: DbDep) -> DashboardOut:
    subs = [
        repo.subscription_view(db, s)
        for s in repo.list_subscriptions(db, user.user_id, active_only=True)
    ]
    total = sum(int(s["monthly_paise"]) for s in subs)
    today = datetime.now(UTC).date()
    soon = []
    for s in subs:
        if s["renewal_date"]:
            d = date.fromisoformat(str(s["renewal_date"]))
            if today <= d <= today + timedelta(days=30):
                soon.append(
                    {
                        "name": s["display_name"],
                        "date": d.isoformat(),
                        "days": (d - today).days,
                        "amount": format_inr(int(s["price_paise"])),
                    }
                )
    cats: dict[str, int] = {}
    for s in subs:
        key = str(s["category"] or "other")
        cats[key] = cats.get(key, 0) + int(s["monthly_paise"])
    prof = repo.get_or_create_profile(db, user.user_id)
    budget = None
    if prof.budget_paise is not None:
        budget = prof.budget_paise if prof.budget_period == "monthly" else prof.budget_paise // 12
    rep = db.scalars(
        select(Report)
        .where(Report.user_id == user.user_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    ).first()
    latest = None
    if rep is not None:
        latest = {
            "id": rep.id,
            "run_id": rep.run_id,
            "status": rep.status,
            "created_at": rep.created_at.isoformat(),
            "current_monthly": format_inr(rep.current_monthly_paise),
            "recommended_monthly": format_inr(rep.recommended_monthly_paise)
            if rep.recommended_monthly_paise is not None
            else None,
            "monthly_saving": format_inr(rep.current_monthly_paise - rep.recommended_monthly_paise)
            if rep.recommended_monthly_paise is not None
            else None,
        }
    runs = db.scalars(
        select(OptimizationRun)
        .where(OptimizationRun.user_id == user.user_id)
        .order_by(OptimizationRun.created_at.desc())
        .limit(5)
    ).all()
    return DashboardOut(
        monthly_spend=money(total),
        annual_spend=money(total * 12),
        active_subscriptions=len(subs),
        renewals_next_30_days=sorted(soon, key=lambda x: x["days"]),
        spend_by_subscription=[
            SpendSlice(
                name=str(s["display_name"]),
                category=s["category"],
                monthly=money(int(s["monthly_paise"])),
            )
            for s in subs
        ],
        spend_by_category=[
            SpendSlice(name=k.title(), category=k, monthly=money(v))
            for k, v in sorted(cats.items())
        ],
        latest_report=latest,
        recent_runs=[_run_out(db, r) for r in runs],
        budget_monthly=money(budget) if budget is not None else None,
        over_budget=(total > budget) if budget is not None else None,
    )


__all__ = ["NotFound"]
