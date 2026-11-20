"""The optimization run graph (blueprint D).

START → load_context → parse_intent ─(info missing?)→ clarify ⟲
      → plan_research → research → validate → decide ─(research_more)→ research ⟲
      → optimize → explain → check_numbers → approval → save_and_learn ─(rejected)→ parse_intent ⟲
      → END

LLM steps (parse_intent, decide, explain) each have a deterministic fallback. Pauses use
``interrupt()``; the worker resumes with ``Command(resume=...)``. Nodes never perform side
effects before ``interrupt()`` because the node re-runs from its start on resume.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from subwise.agent.state import RunState
from subwise.config import Settings
from subwise.core.costing import monthly_equivalent
from subwise.core.features import FEATURE_CODES, FEATURES_BY_CODE
from subwise.core.money import format_inr
from subwise.core.optimizer import solve
from subwise.core.report_facts import (
    PlanFact,
    ReportFacts,
    build_report_facts,
    check_numbers,
    known_provider_mentions,
    render_template_report,
    template_summary,
)
from subwise.db import repositories as repo
from subwise.db.models import ApprovalDecision, Report, ReportEvidence
from subwise.db.session import session_scope
from subwise.domain.enums import USAGE_VALUE, EventType, NextAction, UsageFrequency
from subwise.domain.optimization import CandidatePlan, OptimizationResult, OptimizerInput
from subwise.errors import SubWiseError
from subwise.ids import new_id
from subwise.llm.fallbacks import amount_stated, decide_rules, parse_intent_rules
from subwise.llm.gateway import ChatMessage, LLMGateway
from subwise.llm.prompts import DECIDE_SYSTEM, EXPLAIN_SYSTEM, PARSE_INTENT_SYSTEM
from subwise.memory.learned import LearnedMemory, MemoryKind
from subwise.research.registry import PROVIDERS, PROVIDERS_BY_ID
from subwise.services.prices import PlanPrice, PriceService, usable_for_optimizer
from subwise.worker.events import EventSink

log = logging.getLogger(__name__)

NODE_NAMES: Final[tuple[str, ...]] = (
    "load_context",
    "parse_intent",
    "clarify",
    "plan_research",
    "research",
    "validate",
    "decide",
    "optimize",
    "explain",
    "check_numbers",
    "approval",
    "save_and_learn",
)
LLM_NODES: Final[frozenset[str]] = frozenset({"parse_intent", "decide", "explain"})
INTERRUPT_NODES: Final[frozenset[str]] = frozenset({"clarify", "approval"})
PROVIDER_NAMES = [p.name for p in PROVIDERS]


class IntentLLM(BaseModel):
    categories: list[Literal["video", "music"]] = Field(default_factory=list)
    budget_rupees: int | None = None
    budget_period: Literal["monthly", "annual"] = "monthly"
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    keep_providers: list[str] = Field(default_factory=list)
    drop_providers: list[str] = Field(default_factory=list)
    mode: Literal["savings", "balanced", "best"] = "balanced"


class DecideLLM(BaseModel):
    action: Literal["research_more", "proceed", "proceed_with_gaps"]
    reason: str


@dataclass
class AgentDeps:
    settings: Settings
    session_factory: sessionmaker[Session]
    prices: PriceService
    llm: LLMGateway
    memory: LearnedMemory
    events: EventSink


def _now() -> datetime:
    return datetime.now(UTC)


class Nodes:
    def __init__(self, deps: AgentDeps) -> None:
        self.d = deps

    # -------------------------------------------------------------- helpers
    def ev(
        self,
        state: RunState,
        node: str,
        et: EventType,
        msg: str,
        payload: dict[str, Any] | None = None,
        ms: float | None = None,
    ) -> None:
        self.d.events.emit(state["run_id"], node, et, msg, payload, ms)

    def timed(
        self, name: str, fn: Callable[[RunState], dict[str, Any]], start_msg: str
    ) -> Callable[[RunState], dict[str, Any]]:
        def run(state: RunState) -> dict[str, Any]:
            if name not in INTERRUPT_NODES:
                self.ev(state, name, EventType.NODE_START, start_msg)
            t0 = time.perf_counter()
            out = fn(state)
            ms = round((time.perf_counter() - t0) * 1000, 1)
            detail = out.pop("_summary", "done")
            self.ev(state, name, EventType.NODE_END, detail, out.pop("_payload", None), ms)
            out.setdefault("trace", []).append({"node": name, "event": "end", "detail": detail})
            return out

        return run

    # -------------------------------------------------------------- load_context
    def load_context(self, state: RunState) -> dict[str, Any]:
        uid = state["user_id"]
        with session_scope(self.d.session_factory) as s:
            prof = repo.get_or_create_profile(s, uid)
            profile = {
                "budget_paise": prof.budget_paise,
                "budget_period": prof.budget_period,
                "billing_preference": prof.billing_preference,
                "ads_tolerance": prof.ads_tolerance,
                "eligibility": list(prof.eligibility or []),
                "allow_cached_prices": prof.allow_cached_prices,
                "allow_partial_prices": prof.allow_partial_prices,
                "allow_unverified_prices": prof.allow_unverified_prices,
                "country": prof.country,
                "currency": prof.currency,
            }
            reqs = [
                {"feature_code": r.feature_code, "level": r.level, "weight": r.weight}
                for r in repo.list_requirements(s, uid)
            ]
            subs = [
                repo.subscription_view(s, x)
                for x in repo.list_subscriptions(s, uid, active_only=True)
            ]
        learned = [i.model_dump(mode="json") for i in self.d.memory.list_for_user(uid, limit=10)]
        total = sum(x["monthly_paise"] for x in subs)
        return {
            "profile": profile,
            "requirements": reqs,
            "subscriptions": subs,
            "learned": learned,
            "_summary": f"Loaded {len(subs)} subscription(s) costing {format_inr(total)}/month, "
            f"{len(reqs)} feature preference(s), {len(learned)} learned preference(s).",
        }

    # -------------------------------------------------------------- parse_intent
    def parse_intent(self, state: RunState) -> dict[str, Any]:
        message = state["user_message"]
        if state.get("feedback"):
            message = f"{message}\nFeedback on the previous recommendation: {state['feedback']}"
        decided_by = "llm"
        try:
            intent = self.d.llm.call_structured(
                IntentLLM,
                [
                    ChatMessage(role="system", content=PARSE_INTENT_SYSTEM),
                    ChatMessage(role="user", content=message),
                ],
            )
            raw = intent.model_dump()
        except SubWiseError as exc:
            decided_by = "rules"
            self.ev(
                state,
                "parse_intent",
                EventType.FALLBACK,
                f"Language model unavailable ({exc.code.value}); using the rule-based parser.",
            )
            raw = parse_intent_rules(message)
        rules = parse_intent_rules(message)
        spec = self._merge_spec(state, raw, rules, message)
        missing = []
        if spec["budget_paise"] is None and not spec.get("budget_declined"):
            missing.append("budget")
        if not spec["must_have"] and not spec["nice_to_have"] and not state.get("subscriptions"):
            missing.append("needs")
        bp = spec["budget_paise"]
        budget_text = f"{format_inr(bp)}/month" if bp else "not set"
        summary = (
            f"Understood request ({decided_by}): categories {', '.join(spec['categories'])}; "
            f"must-have {', '.join(spec['must_have']) or 'none'}; budget "
            f"{budget_text}; "
            f"mode {spec['mode']}."
        )
        self.ev(
            state,
            "parse_intent",
            EventType.DECISION,
            summary,
            {"decided_by": decided_by, "spec": spec},
        )
        done = (
            ("Request understood; asking for: " + ", ".join(missing))
            if missing
            else ("Request understood.")
        )
        return {
            "request_spec": spec,
            "missing_fields": missing,
            "_summary": done,
            "trace": [
                {
                    "node": "parse_intent",
                    "event": "decision",
                    "detail": summary,
                    "decided_by": decided_by,
                }
            ],
        }

    def _merge_spec(
        self, state: RunState, raw: dict[str, Any], rules: dict[str, Any], message: str
    ) -> dict[str, Any]:
        profile = state.get("profile", {})
        prev = state.get("request_spec") or {}
        valid_providers = set(PROVIDERS_BY_ID)
        must = {f for f in raw.get("must_have", []) if f in FEATURE_CODES}
        nice = {f for f in raw.get("nice_to_have", []) if f in FEATURE_CODES}
        must |= {f for f in rules["must_have"] if f in FEATURE_CODES}  # keyword safety net
        weights: dict[str, float] = {}
        for r in state.get("requirements", []):
            if r["level"] == "must":
                must.add(r["feature_code"])
            elif r["level"] == "nice":
                weights[r["feature_code"]] = float(r["weight"])
        for f in nice:
            weights.setdefault(f, 0.6)
        ads = profile.get("ads_tolerance", "ok")
        cats = set(raw.get("categories") or []) | set(rules["categories"])
        cats |= {x["category"] for x in state.get("subscriptions", []) if x.get("category")}
        for code, cat in (("ad_free_video", "video"), ("ad_free_music", "music")):
            if cat in cats and ads == "never":
                must.add(code)
            elif cat in cats and ads == "avoid":
                weights.setdefault(code, 0.8)
        weights = {f: w for f, w in weights.items() if f not in must and 0 < w <= 1}
        # Budget: accept the model's number only if the user literally typed it.
        budget = None
        period = raw.get("budget_period", "monthly")
        b = raw.get("budget_rupees")
        if isinstance(b, int) and b > 0 and amount_stated(message, b):
            budget = b * 100 if period == "monthly" else (b * 100) // 12
        elif rules.get("budget_rupees"):
            rb = int(rules["budget_rupees"])
            budget = rb * 100 if rules["budget_period"] == "monthly" else (rb * 100) // 12
        if budget is None and prev.get("budget_paise"):
            budget = prev["budget_paise"]
        if budget is None and profile.get("budget_paise"):
            bp = int(profile["budget_paise"])
            budget = bp if profile.get("budget_period") == "monthly" else bp // 12
        keep = sorted(
            {
                p
                for p in raw.get("keep_providers", []) + rules["keep_providers"]
                if p in valid_providers
            }
            | set(prev.get("keep_providers", []))
        )
        drop = sorted(
            {
                p
                for p in raw.get("drop_providers", []) + rules["drop_providers"]
                if p in valid_providers
            }
            - set(keep)
        )
        mode = state.get("mode") or raw.get("mode") or "balanced"
        if state.get("mode") in (None, "", "auto"):
            mode = raw.get("mode", "balanced")
        return {
            "categories": sorted(cats or {"video", "music"}),
            "budget_paise": budget,
            "budget_declined": bool(prev.get("budget_declined")),
            "must_have": sorted(must),
            "nice_to_have": weights,
            "keep_providers": keep,
            "drop_providers": drop,
            "mode": mode,
            "billing_preference": profile.get("billing_preference", "any"),
        }

    # -------------------------------------------------------------- clarify (interrupt)
    def clarify(self, state: RunState) -> dict[str, Any]:
        questions = []
        for f in state.get("missing_fields", []):
            if f == "budget":
                questions.append(
                    {
                        "field": "budget",
                        "question": "What monthly budget (₹) should the subscriptions fit in? "
                        "Reply 'none' for no limit.",
                    }
                )
            if f == "needs":
                questions.append(
                    {
                        "field": "needs",
                        "question": "What do you mainly use subscriptions for (e.g. movies, "
                        "cricket, music)?",
                    }
                )
        answer = interrupt({"kind": "clarify", "questions": questions})
        answers: dict[str, str] = (
            dict(answer.get("answers", {})) if isinstance(answer, dict) else {}
        )
        spec = dict(state.get("request_spec", {}))
        budget_text = answers.get("budget", "").strip()
        if budget_text:
            digits = "".join(ch for ch in budget_text if ch.isdigit())
            if digits:
                spec["budget_paise"] = int(digits) * 100
            elif budget_text.lower() in ("none", "no", "no limit", "unlimited", "-"):
                spec["budget_declined"] = True
        if answers.get("needs"):
            extra = parse_intent_rules(answers["needs"])
            spec["must_have"] = sorted(set(spec.get("must_have", [])) | set(extra["must_have"]))
            spec["categories"] = sorted(set(spec.get("categories", [])) | set(extra["categories"]))
        missing = [
            f
            for f in state.get("missing_fields", [])
            if not (
                (f == "budget" and (spec.get("budget_paise") or spec.get("budget_declined")))
                or (f == "needs" and spec.get("must_have"))
            )
        ]
        return {
            "request_spec": spec,
            "missing_fields": missing,
            "clarification_count": state["clarification_count"] + 1,
            "_summary": f"Received your answers: {json.dumps(answers, ensure_ascii=False)}",
        }

    # -------------------------------------------------------------- plan_research
    def plan_research(self, state: RunState) -> dict[str, Any]:
        spec = state["request_spec"]
        cats = set(spec["categories"])
        ids = [p.id for p in PROVIDERS if p.category.value in cats]
        ids += [x["provider_id"] for x in state.get("subscriptions", []) if x.get("provider_id")]
        ids = [i for i in dict.fromkeys(ids) if i not in set(spec.get("drop_providers", []))]
        names = ", ".join(PROVIDERS_BY_ID[i].name for i in ids)
        done = {
            r["provider_id"] for r in state.get("research_results", []) if r["outcome"] == "success"
        }  # fetched successfully earlier in this run
        return {
            "research_plan": ids,
            "retry_providers": [i for i in ids if i not in done],
            "_summary": f"Will check official pricing pages of {len(ids)} providers: {names}.",
            "_payload": {"providers": ids},
        }

    # -------------------------------------------------------------- research
    def research(self, state: RunState) -> dict[str, Any]:
        targets = state.get("retry_providers", [])
        results = {r["provider_id"]: r for r in state.get("research_results", [])}
        if not targets:
            return {
                "research_round": state["research_round"] + 1,
                "_summary": "Using the prices already retrieved earlier in this run.",
            }
        for pid in targets:
            prov = PROVIDERS_BY_ID[pid]
            self.ev(
                state,
                "research",
                EventType.TOOL_CALL,
                f"Retrieving {prov.name} pricing from {prov.pricing_url}",
                {"provider_id": pid, "url": prov.pricing_url},
            )
            t0 = time.perf_counter()
            r = self.d.prices.refresh_provider(pid, run_id=state["run_id"])
            ms = round((time.perf_counter() - t0) * 1000, 1)
            ok = r.outcome == "success"
            msg = (
                f"{prov.name}: {r.verified} verified price(s) from the live page"
                if ok
                else f"{prov.name}: live retrieval failed ({r.outcome}) - {r.error}"
            )
            self.ev(
                state,
                "research",
                EventType.TOOL_CALL if ok else EventType.TOOL_ERROR,
                msg,
                {
                    "provider_id": pid,
                    "outcome": r.outcome,
                    "prices_found": r.prices_found,
                    "verified": r.verified,
                    "warnings": r.warnings[:5],
                },
                ms,
            )
            results[pid] = {
                "provider_id": pid,
                "outcome": r.outcome,
                "error": r.error,
                "verified": r.verified,
                "prices_found": r.prices_found,
            }
        ok_n = sum(1 for r in results.values() if r["outcome"] == "success")
        return {
            "research_results": list(results.values()),
            "research_round": state["research_round"] + 1,
            "_summary": f"Live retrieval succeeded for {ok_n} of {len(results)} providers.",
        }

    # -------------------------------------------------------------- validate
    def _usable(self, state: RunState) -> tuple[list[PlanPrice], list[tuple[PlanPrice, str]]]:
        prof = state.get("profile", {})
        plan = set(state.get("research_plan", []))
        usable: list[PlanPrice] = []
        unusable: list[tuple[PlanPrice, str]] = []
        for pp in self.d.prices.plan_prices():
            if pp.provider_id not in plan:
                continue
            ok, why = usable_for_optimizer(
                pp,
                allow_cached=prof.get("allow_cached_prices", True),
                allow_partial=prof.get("allow_partial_prices", False),
                allow_unverified=prof.get("allow_unverified_prices", False),
            )
            if ok:
                usable.append(pp)
            else:
                unusable.append((pp, why))
        return usable, unusable

    def validate(self, state: RunState) -> dict[str, Any]:
        usable, unusable = self._usable(state)
        must = state["request_spec"]["must_have"]
        coverage = {f: sum(1 for p in usable if p.features.get(f) == "yes") for f in must}
        labels: dict[str, int] = {}
        for p in usable:
            labels[p.label] = labels.get(p.label, 0) + 1
        failed = [
            r["provider_id"] for r in state.get("research_results", []) if r["outcome"] != "success"
        ]
        quality = {
            "usable": len(usable),
            "excluded": len(unusable),
            "labels": labels,
            "must_have_coverage": coverage,
            "failed_providers": failed,
            "excluded_reasons": [{"plan": p.plan_name, "reason": why} for p, why in unusable][:20],
        }
        parts = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in labels.items()) or "none"
        return {
            "quality": quality,
            "_summary": f"Validated prices: {len(usable)} usable ({parts}); "
            f"{len(unusable)} excluded; {len(failed)} provider(s) unavailable.",
            "_payload": quality,
        }

    # -------------------------------------------------------------- decide
    def decide(self, state: RunState) -> dict[str, Any]:
        q = state["quality"]
        all_ok = all(v > 0 for v in q["must_have_coverage"].values())
        failed = q["failed_providers"]
        rnd, mx = state["research_round"], self.d.settings.max_research_rounds
        allowed = {NextAction.PROCEED_WITH_GAPS}
        if all_ok:
            allowed.add(NextAction.PROCEED)
        if failed and rnd < mx:
            allowed.add(NextAction.RESEARCH_MORE)
        rule = decide_rules(
            all_must_haves_usable=all_ok,
            failed_providers=len(failed),
            research_round=rnd,
            max_rounds=mx,
        )
        decided_by, action, reason = "rule", rule, "rule table"
        try:
            out = self.d.llm.call_structured(
                DecideLLM,
                [
                    ChatMessage(role="system", content=DECIDE_SYSTEM),
                    ChatMessage(
                        role="user",
                        content=json.dumps(
                            {
                                "quality": q,
                                "research_round": rnd,
                                "max_rounds": mx,
                                "allowed_actions": sorted(a.value for a in allowed),
                            }
                        ),
                    ),
                ],
            )
            if NextAction(out.action) in allowed:
                decided_by, action, reason = "llm", NextAction(out.action), out.reason
            else:
                reason = f"model chose '{out.action}', which is not allowed now; rule applied"
        except SubWiseError as exc:
            reason = f"language model unavailable ({exc.code.value}); rule applied"
        msg = f"Decision: {action.value.replace('_', ' ')} ({decided_by}: {reason})"
        self.ev(
            state,
            "decide",
            EventType.DECISION,
            msg,
            {"decided_by": decided_by, "allowed": sorted(a.value for a in allowed)},
        )
        retry = failed if action is NextAction.RESEARCH_MORE else []
        return {
            "next_action": action.value,
            "retry_providers": retry,
            "_summary": f"Next step: {action.value.replace('_', ' ')}.",
            "trace": [
                {"node": "decide", "event": "decision", "detail": msg, "decided_by": decided_by}
            ],
        }

    # -------------------------------------------------------------- optimize
    def _plan_fact(
        self,
        pp: PlanPrice,
        *,
        is_current: bool = False,
        price: int | None = None,
        cycle: int | None = None,
        label: str | None = None,
    ) -> PlanFact:
        p = price if price is not None else pp.price_paise
        c = cycle if cycle is not None else pp.billing_cycle_months
        return PlanFact(
            plan_id=pp.plan_id,
            name=pp.plan_name,
            provider_name=pp.provider_name,
            monthly_display=format_inr(monthly_equivalent(p, c).paise),
            price_display=format_inr(p),
            billing_cycle_months=c,
            label=label or pp.label,
            observed_at=pp.observed_at.isoformat(),
            source_url=pp.source_url,
            evidence=pp.evidence_snippet,
            is_current=is_current,
        )

    def optimize(self, state: RunState) -> dict[str, Any]:
        spec, prof = state["request_spec"], state.get("profile", {})
        usable, _ = self._usable(state)
        by_plan = {p.plan_id: p for p in usable}
        all_prices = {p.plan_id: p for p in self.d.prices.plan_prices()}
        facts: dict[str, PlanFact] = {}
        cands: dict[str, CandidatePlan] = {}
        excluded: dict[str, str] = {}
        mandatory: set[str] = set()
        current_items, fixed_items = [], []
        usage: dict[str, float] = {}
        rejected_before = {
            i["key"]: i["value"]
            for i in state.get("learned", [])
            if i["kind"] == MemoryKind.REJECTIONS.value
        }
        elig = set(prof.get("eligibility", []))
        for pp in usable:
            feats = frozenset(f for f, v in pp.features.items() if v == "yes")
            cands[pp.plan_id] = CandidatePlan(
                plan_id=pp.plan_id,
                name=pp.plan_name,
                monthly_paise=pp.monthly_paise,
                exclusion_group=pp.exclusion_group,
                service_lines=frozenset(pp.entitled_lines),
                features=feats,
            )
            facts[pp.plan_id] = self._plan_fact(pp)
            if pp.provider_id in spec.get("drop_providers", []):
                excluded[pp.plan_id] = "you asked to drop this provider"
            elif not set(pp.eligibility) <= elig:
                excluded[pp.plan_id] = f"requires {', '.join(pp.eligibility)} eligibility"
            elif spec.get("billing_preference") == "monthly" and pp.billing_cycle_months != 1:
                excluded[pp.plan_id] = "you prefer monthly billing"
            elif pp.plan_id in rejected_before:
                excluded[pp.plan_id] = (
                    "you rejected this plan before: "
                    f"{rejected_before[pp.plan_id].get('reason') or 'no reason given'}"
                )
        for sub in state.get("subscriptions", []):
            usage_val = USAGE_VALUE[UsageFrequency(sub["usage_frequency"])]
            item = {
                "name": sub["display_name"],
                "monthly_paise": sub["monthly_paise"],
                "usage": sub["usage_frequency"],
                "plan_id": None,
            }
            prov = PROVIDERS_BY_ID.get(sub.get("provider_id") or "")
            if prov is None:  # custom subscription outside the catalog: fixed, kept
                fixed_items.append(item)
                current_items.append(item)
                continue
            cid = sub["plan_id"] or f"current:{sub['id']}"
            item["plan_id"] = cid
            current_items.append(item)
            line = prov.service_line_id
            if usage_val > 0:
                usage[line] = max(usage.get(line, 0.0), usage_val)
            known = all_prices.get(sub["plan_id"]) if sub["plan_id"] else None
            if known is not None:
                feats = frozenset(f for f, v in known.features.items() if v == "yes")
                lines = frozenset(known.entitled_lines)
                name = known.plan_name
            else:
                feats = frozenset(prov.defining_features)
                lines = frozenset({line, *prov.entitled_lines})
                name = sub["display_name"]
            cands[cid] = CandidatePlan(
                plan_id=cid,
                name=name,
                monthly_paise=sub["monthly_paise"],
                exclusion_group=line,
                service_lines=lines,
                features=feats,
                is_current=True,
            )
            excluded.pop(cid, None)
            facts[cid] = PlanFact(
                plan_id=cid,
                name=name,
                provider_name=prov.name,
                monthly_display=format_inr(sub["monthly_paise"]),
                price_display=format_inr(sub["price_paise"]),
                billing_cycle_months=sub["billing_cycle_months"],
                label="user_entered",
                is_current=True,
            )
            if sub["is_mandatory"] or prov.id in spec.get("keep_providers", []):
                mandatory.add(cid)
            if sub["usage_frequency"] == "never" and not sub["is_mandatory"]:
                pass  # no retention credit; report flags it
        fixed = sum(i["monthly_paise"] for i in fixed_items)
        inp = OptimizerInput(
            candidates=list(cands.values()),
            must_have=frozenset(spec["must_have"]),
            weights=spec["nice_to_have"],
            budget_paise=spec.get("budget_paise"),
            fixed_monthly_paise=fixed,
            mandatory_plan_ids=frozenset(mandatory),
            excluded_plan_ids=excluded,
            current_line_usage=usage,
            mode=spec["mode"],
        )
        result = solve(inp)
        if result.current_overlaps:
            ov = "; ".join(
                f"{FEATURES_BY_CODE[f].label if f in FEATURES_BY_CODE else f}: "
                f"{', '.join(facts[i].name for i in ids)}"
                for f, ids in result.current_overlaps.items()
            )
            self.ev(
                state,
                "optimize",
                EventType.DECISION,
                f"Detected overlap in current subscriptions - {ov}",
            )
        issues = [
            f"{PROVIDERS_BY_ID[r['provider_id']].name}: live retrieval failed "
            f"({r['outcome']}). {r['error'] or ''}".strip()
            for r in state.get("research_results", [])
            if r["outcome"] != "success"
        ]
        cached = [f.name for f in facts.values() if f.label == "cached_verified"]
        if cached:
            issues.append(
                "Cached (previously verified, not live) prices used for: "
                + ", ".join(sorted(cached))
            )
        never = [
            s["display_name"]
            for s in state.get("subscriptions", [])
            if s["usage_frequency"] == "never"
        ]
        if never:
            issues.append("You marked these as never used - review them: " + ", ".join(never))
        report_facts = build_report_facts(
            result,
            plans=facts,
            current_items=current_items,
            fixed_items=fixed_items,
            provider_names=PROVIDER_NAMES,
            data_issues=issues,
        )
        obs_ids = [
            by_plan[p].observation_id
            for p in (result.best.plan_ids if result.best else [])
            if p in by_plan
        ]
        if result.status == "optimal" and result.best:
            msg = (
                f"Optimized portfolio: {' + '.join(facts[p].name for p in result.best.plan_ids)}"
                f" at {format_inr(result.best.total_monthly_paise)}/month "
                f"(from {len(cands)} candidate plans, {result.solve_ms} ms)."
            )
        else:
            msg = f"No feasible portfolio: {result.diagnosis.message if result.diagnosis else ''}"
        return {
            "optimization": result.model_dump(mode="json"),
            "facts": report_facts.model_dump(mode="json"),
            "observation_ids": obs_ids,
            "_summary": msg,
        }

    # -------------------------------------------------------------- explain + check_numbers
    def explain(self, state: RunState) -> dict[str, Any]:
        facts = ReportFacts.model_validate(state["facts"])
        public = facts.model_dump(exclude={"allowed_amounts_paise", "allowed_names"})
        try:
            text = self.d.llm.call_text(
                [
                    ChatMessage(role="system", content=EXPLAIN_SYSTEM),
                    ChatMessage(role="user", content=json.dumps(public, ensure_ascii=False)),
                ]
            )
            source = "llm"
        except SubWiseError as exc:
            self.ev(
                state,
                "explain",
                EventType.FALLBACK,
                f"Language model unavailable ({exc.code.value}); using the template summary.",
            )
            text, source = template_summary(facts), "template"
        return {
            "draft_summary": text,
            "draft_source": source,
            "_summary": f"Drafted the explanation ({source}).",
        }

    def check_numbers_node(self, state: RunState) -> dict[str, Any]:
        facts = ReportFacts.model_validate(state["facts"])
        text, source = state["draft_summary"], state["draft_source"]
        violations: list[str] = []
        if source == "llm":
            violations = check_numbers(text, facts)
            allowed = {n.lower() for n in facts.allowed_names}
            for name in known_provider_mentions(text, PROVIDER_NAMES):
                mentioned_ok = any(name.lower() in a for a in allowed) and (
                    name in json.dumps(state["facts"])
                )
                if not mentioned_ok:
                    violations.append(f"mentions {name}, which is not in the facts")
            if violations:
                self.ev(
                    state,
                    "check_numbers",
                    EventType.FALLBACK,
                    "The model's explanation contained figures or names not in the verified "
                    "facts; replaced with the template summary.",
                    {"violations": violations},
                )
                text, source = template_summary(facts), "template"
        markdown = f"## Summary\n\n{text}\n\n{render_template_report(facts)}"
        result = OptimizationResult.model_validate(state["optimization"])
        current_total = sum(
            int(i["monthly_paise"])
            for i in [{"monthly_paise": s["monthly_paise"]} for s in state.get("subscriptions", [])]
        )
        report_id = new_id("rep")
        with session_scope(self.d.session_factory) as s:
            version = 1 + state["revision_count"]
            s.add(
                Report(
                    id=report_id,
                    run_id=state["run_id"],
                    user_id=state["user_id"],
                    version=version,
                    result=state["optimization"],
                    facts=state["facts"],
                    markdown=markdown,
                    generated_by=source,
                    current_monthly_paise=current_total,
                    recommended_monthly_paise=result.best.total_monthly_paise
                    if result.best
                    else None,
                )
            )
            s.flush()
            for oid in state.get("observation_ids", []):
                s.add(ReportEvidence(report_id=report_id, price_observation_id=oid))
        msg = (
            "Verified the report: every amount matches the optimizer output."
            if not violations
            else f"Verification replaced the model text ({len(violations)} issue(s))."
        )
        return {
            "report_id": report_id,
            "_summary": msg,
            "_payload": {"report_id": report_id, "generated_by": source},
        }

    # -------------------------------------------------------------- approval (interrupt)
    def approval(self, state: RunState) -> dict[str, Any]:
        value = interrupt({"kind": "approval", "report_id": state["report_id"]})
        value = value if isinstance(value, dict) else {}
        decision = value.get("decision", "rejected")
        return {
            "decision": decision,
            "decision_reason": value.get("reason") or "",
            "remember": list(value.get("remember") or []),
            "_summary": f"You {decision} the recommendation.",
        }

    # -------------------------------------------------------------- save_and_learn
    def save_and_learn(self, state: RunState) -> dict[str, Any]:
        decision, reason = state["decision"], state.get("decision_reason", "")
        facts = ReportFacts.model_validate(state["facts"])
        with session_scope(self.d.session_factory) as s:
            rep = s.get(Report, state["report_id"])
            if rep is not None:
                rep.status = decision
            s.add(
                ApprovalDecision(
                    id=new_id("dec"),
                    run_id=state["run_id"],
                    report_id=state["report_id"],
                    user_id=state["user_id"],
                    decision=decision,
                    reason=reason or None,
                )
            )
        learned = 0
        uid, rid = state["user_id"], state["run_id"]
        if decision == "approved":
            for code in state.get("remember", []):
                if code in FEATURE_CODES:
                    self.d.memory.remember(
                        uid,
                        MemoryKind.STATED_PRIORITIES,
                        code,
                        {"feature": code, "text": FEATURES_BY_CODE[code].label},
                        rid,
                    )
                    learned += 1
        else:
            for p in facts.recommended:
                if not p.is_current:
                    self.d.memory.remember(
                        uid,
                        MemoryKind.REJECTIONS,
                        p.plan_id,
                        {"plan": p.name, "reason": reason},
                        rid,
                    )
                    learned += 1
        msg = f"Saved your decision ({decision}); {learned} preference(s) remembered."
        return {
            "feedback": reason if decision == "rejected" else "",
            "revision_count": state["revision_count"] + (1 if decision == "rejected" else 0),
            "_summary": msg,
        }

    # -------------------------------------------------------------- routers
    def after_parse(self, state: RunState) -> str:
        if state.get("missing_fields") and (
            state["clarification_count"] < self.d.settings.max_clarifications
        ):
            return "clarify"
        return "plan_research"

    def after_decide(self, state: RunState) -> str:
        return "research" if state["next_action"] == NextAction.RESEARCH_MORE.value else "optimize"

    def after_save(self, state: RunState) -> str:
        if (
            state["decision"] == "rejected"
            and state.get("feedback")
            and state["revision_count"] <= self.d.settings.max_revisions
        ):
            return "load_context"  # reload memory so the rejection is applied
        return END


def build_graph(deps: AgentDeps, checkpointer: Any) -> Any:
    n = Nodes(deps)
    g: Any = StateGraph(RunState)  # node callables are closures; LangGraph overloads are too strict
    g.add_node(
        "load_context",
        n.timed("load_context", n.load_context, "Loading your subscriptions and preferences"),
    )
    g.add_node("parse_intent", n.timed("parse_intent", n.parse_intent, "Understanding the request"))
    g.add_node("clarify", n.timed("clarify", n.clarify, ""))
    g.add_node(
        "plan_research",
        n.timed("plan_research", n.plan_research, "Choosing which providers to research"),
    )
    g.add_node(
        "research",
        n.timed("research", n.research, "Retrieving provider information from official pages"),
    )
    g.add_node("validate", n.timed("validate", n.validate, "Validating prices and evidence"))
    g.add_node("decide", n.timed("decide", n.decide, "Deciding whether the data is sufficient"))
    g.add_node(
        "optimize",
        n.timed(
            "optimize", n.optimize, "Comparing features, detecting overlap, running the optimizer"
        ),
    )
    g.add_node("explain", n.timed("explain", n.explain, "Explaining the recommendation"))
    g.add_node(
        "check_numbers",
        n.timed(
            "check_numbers", n.check_numbers_node, "Verifying the recommendation against the facts"
        ),
    )
    g.add_node("approval", n.timed("approval", n.approval, ""))
    g.add_node("save_and_learn", n.timed("save_and_learn", n.save_and_learn, "Saving the decision"))
    g.add_edge(START, "load_context")
    g.add_edge("load_context", "parse_intent")
    g.add_conditional_edges("parse_intent", n.after_parse, ["clarify", "plan_research"])
    g.add_conditional_edges("clarify", n.after_parse, ["clarify", "plan_research"])
    g.add_edge("plan_research", "research")
    g.add_edge("research", "validate")
    g.add_edge("validate", "decide")
    g.add_conditional_edges("decide", n.after_decide, ["research", "optimize"])
    g.add_edge("optimize", "explain")
    g.add_edge("explain", "check_numbers")
    g.add_edge("check_numbers", "approval")
    g.add_edge("approval", "save_and_learn")
    g.add_conditional_edges("save_and_learn", n.after_save, ["load_context", END])
    return g.compile(checkpointer=checkpointer)
