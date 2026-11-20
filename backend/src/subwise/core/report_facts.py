"""Explainable, verifiable report facts (blueprint H.6) + deterministic template + the
``check_numbers`` guard that every LLM-written explanation must pass. Pure module."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from subwise.core.features import FEATURES_BY_CODE
from subwise.core.money import INR_AMOUNT_RE, amount_to_paise, format_inr
from subwise.domain.optimization import OptimizationResult
from subwise.errors import InvalidPrice

LABEL_TEXT = {
    "live_verified": "live, verified",
    "cached_verified": "cached (previously verified)",
    "partial": "partially verified",
    "unverified": "unverified",
    "conflict": "conflicting sources",
    "user_entered": "price you entered",
}


class PlanFact(BaseModel):
    plan_id: str
    name: str
    provider_name: str
    monthly_display: str
    price_display: str
    billing_cycle_months: int
    label: str
    observed_at: str | None = None
    source_url: str | None = None
    evidence: str | None = None
    is_current: bool = False


class ReportFacts(BaseModel):
    status: str
    budget_display: str | None
    within_budget: bool | None
    current_total_display: str
    current_items: list[dict[str, str]]
    recommended: list[PlanFact] = Field(default_factory=list)
    fixed_items: list[dict[str, str]] = Field(default_factory=list)
    recommended_total_display: str | None = None
    monthly_saving_paise: int | None = None
    monthly_saving_display: str | None = None
    annual_saving_display: str | None = None
    keep: list[str] = Field(default_factory=list)
    add: list[str] = Field(default_factory=list)
    drop: list[str] = Field(default_factory=list)
    features_covered: list[str] = Field(default_factory=list)
    features_lost: list[str] = Field(default_factory=list)
    missing_must_have: list[str] = Field(default_factory=list)
    missing_nice_to_have: list[str] = Field(default_factory=list)
    current_overlaps: dict[str, list[str]] = Field(default_factory=dict)
    rejected: list[dict[str, str]] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    data_issues: list[str] = Field(default_factory=list)
    diagnosis: str | None = None
    diagnosis_amounts: dict[str, str] = Field(default_factory=dict)
    allowed_amounts_paise: list[int] = Field(default_factory=list)
    allowed_names: list[str] = Field(default_factory=list)


def _feat(code: str) -> str:
    f = FEATURES_BY_CODE.get(code)
    return f.label if f else code


def build_report_facts(
    result: OptimizationResult,
    *,
    plans: dict[str, PlanFact],
    current_items: list[dict[str, Any]],
    fixed_items: list[dict[str, Any]],
    provider_names: list[str],
    data_issues: list[str],
) -> ReportFacts:
    """``current_items``: [{name, monthly_paise, usage, plan_id|None}] - what the user pays now.
    ``plans``: facts for every candidate plan id referenced by the result."""
    amounts: set[int] = set()

    def money(paise: int) -> str:
        amounts.add(abs(paise))
        return format_inr(paise)

    current_total = sum(int(i["monthly_paise"]) for i in current_items)
    facts = ReportFacts(
        status=result.status,
        budget_display=money(result.budget_paise) if result.budget_paise is not None else None,
        within_budget=None,
        current_total_display=money(current_total),
        current_items=[
            {
                "name": str(i["name"]),
                "monthly_display": money(int(i["monthly_paise"])),
                "usage": str(i.get("usage", "unknown")),
            }
            for i in current_items
        ],
        fixed_items=[
            {"name": str(i["name"]), "monthly_display": money(int(i["monthly_paise"]))}
            for i in fixed_items
        ],
        current_overlaps={
            _feat(f): [plans[p].name if p in plans else p for p in ids]
            for f, ids in result.current_overlaps.items()
        },
        data_issues=data_issues,
    )
    if result.best is not None:
        best = result.best
        rec = [plans[p] for p in best.plan_ids]
        for p in rec:
            amounts.add(amount_to_paise(p.monthly_display.lstrip("₹").replace(",", "")))
            amounts.add(amount_to_paise(p.price_display.lstrip("₹").replace(",", "")))
        facts.recommended = rec
        facts.recommended_total_display = money(best.total_monthly_paise)
        saving = current_total - best.total_monthly_paise
        facts.monthly_saving_paise = saving
        facts.monthly_saving_display = money(saving)
        facts.annual_saving_display = money(saving * 12)
        facts.within_budget = best.within_budget
        current_plan_ids = {str(i["plan_id"]) for i in current_items if i.get("plan_id")}
        facts.keep = [plans[p].name for p in best.plan_ids if p in current_plan_ids]
        facts.add = [plans[p].name for p in best.plan_ids if p not in current_plan_ids]
        facts.drop = [
            str(i["name"])
            for i in current_items
            if i.get("plan_id") and i["plan_id"] not in best.plan_ids
        ]
        facts.features_covered = [_feat(f) for f in best.covered_features]
        facts.features_lost = [_feat(f) for f in best.lost_features]
        facts.missing_must_have = [_feat(f) for f in best.missing_must_have]
        facts.missing_nice_to_have = [_feat(f) for f in best.missing_nice_to_have]
        facts.alternatives = [
            {
                "plans": [plans[p].name for p in a.plan_ids],
                "total_display": money(a.total_monthly_paise),
                "missing_nice_to_have": [_feat(f) for f in a.missing_nice_to_have],
            }
            for a in result.alternatives
        ]
    facts.rejected = [
        {"name": plans[r.plan_id].name if r.plan_id in plans else r.plan_id, "reason": r.reason}
        for r in result.rejected
    ]
    if result.diagnosis is not None:
        d = result.diagnosis
        facts.diagnosis = d.message
        if d.min_cost_for_must_haves_paise is not None:
            facts.diagnosis_amounts["minimum_needed"] = money(d.min_cost_for_must_haves_paise)
        if d.shortfall_paise is not None:
            facts.diagnosis_amounts["shortfall"] = money(d.shortfall_paise)
        if d.uncoverable_features:
            facts.diagnosis_amounts["uncoverable"] = ", ".join(
                _feat(f) for f in d.uncoverable_features
            )
    facts.allowed_amounts_paise = sorted(amounts)
    names = {p.name for p in plans.values()} | {str(i["name"]) for i in current_items}
    facts.allowed_names = sorted(names | set(provider_names))
    return facts


def render_template_report(facts: ReportFacts) -> str:
    """Deterministic report used as the body of every report and as the full fallback."""
    lines: list[str] = []
    if facts.status != "optimal":
        lines.append("## No recommendation")
        lines.append(facts.diagnosis or "No feasible combination of plans was found.")
        for k, v in facts.diagnosis_amounts.items():
            lines.append(f"- {k.replace('_', ' ').capitalize()}: {v}")
        lines.append(f"\nYou currently pay {facts.current_total_display} per month.")
    else:
        lines.append("## Recommendation")
        saving = facts.monthly_saving_paise or 0
        if saving > 0:
            change = (
                f"saves {facts.monthly_saving_display} per month "
                f"({facts.annual_saving_display} per year)"
            )
        elif saving == 0:
            change = "costs the same as today. There is no difference between the plans."
        else:
            change = (
                f"costs {(facts.monthly_saving_display or '').lstrip('-')} more per month than "
                "today, because it covers features you asked for"
            )
        lines.append(
            f"The recommended portfolio costs {facts.recommended_total_display} per "
            f"month and {change}."
        )
        if facts.budget_display:
            lines.append(
                f"Budget: {facts.budget_display} per month - "
                f"{'within budget' if facts.within_budget else 'over budget'}."
            )
        lines.append("\n| Plan | Price | Per month | Price status | Source |")
        lines.append("| --- | --- | --- | --- | --- |")
        for p in facts.recommended:
            src = f"[official page]({p.source_url})" if p.source_url else "your entered price"
            when = f" ({p.observed_at[:10]})" if p.observed_at else ""
            lines.append(
                f"| {p.name}{' (current)' if p.is_current else ''} | {p.price_display} "
                f"every {p.billing_cycle_months} mo | {p.monthly_display} | "
                f"{LABEL_TEXT.get(p.label, p.label)}{when} | {src} |"
            )
        for f in facts.fixed_items:
            lines.append(
                f"| {f['name']} (kept, not in catalog) | - | {f['monthly_display']} | "
                "price you entered | - |"
            )
        if facts.keep:
            lines.append(f"\n**Keep:** {', '.join(facts.keep)}")
        if facts.add:
            lines.append(f"**Switch to / add:** {', '.join(facts.add)}")
        if facts.drop:
            lines.append(f"**Cancel or replace:** {', '.join(facts.drop)}")
        lines.append(f"\n**Features covered:** {', '.join(facts.features_covered) or 'none'}")
        if facts.features_lost:
            lines.append(f"**Features you would lose:** {', '.join(facts.features_lost)}")
        if facts.missing_nice_to_have:
            lines.append(f"**Nice-to-haves not covered:** {', '.join(facts.missing_nice_to_have)}")
    if facts.current_overlaps:
        lines.append("\n## Overlap in what you pay for today")
        for feat, names in facts.current_overlaps.items():
            lines.append(f"- {feat}: {', '.join(names)}")
    if facts.rejected:
        lines.append("\n## Plans not chosen")
        for r in facts.rejected[:12]:
            lines.append(f"- {r['name']}: {r['reason']}")
    if facts.alternatives:
        lines.append("\n## Alternatives")
        for a in facts.alternatives:
            miss = (
                f" (missing: {', '.join(a['missing_nice_to_have'])})"
                if (a["missing_nice_to_have"])
                else ""
            )
            lines.append(f"- {' + '.join(a['plans'])}: {a['total_display']} per month{miss}")
    if facts.data_issues:
        lines.append("\n## Data limitations")
        for issue in facts.data_issues:
            lines.append(f"- {issue}")
    return "\n".join(lines)


def template_summary(facts: ReportFacts) -> str:
    if facts.status != "optimal":
        return facts.diagnosis or "No feasible recommendation could be made."
    saving = facts.monthly_saving_paise or 0
    head = (
        f"Switching to {' + '.join(p.name for p in facts.recommended)} brings your monthly "
        f"spend to {facts.recommended_total_display}"
    )
    if saving > 0:
        return f"{head}, saving {facts.monthly_saving_display} per month."
    if saving == 0:
        return f"{head}. There is no difference between the plans in cost."
    return f"{head}, which is {(facts.monthly_saving_display or '').lstrip('-')} more than today."


def check_numbers(text: str, facts: ReportFacts) -> list[str]:
    """Every ₹ amount in ``text`` must be one of the facts' amounts; no unknown provider names.
    Returns violations (empty list = pass)."""
    allowed = set(facts.allowed_amounts_paise)
    violations: list[str] = []
    for m in INR_AMOUNT_RE.finditer(text):
        try:
            paise = amount_to_paise(m.group("num"))
        except InvalidPrice:
            violations.append(f"unparseable amount {m.group(0)!r}")
            continue
        if paise not in allowed:
            violations.append(f"amount {m.group(0)} is not in the verified facts")
    # bare numbers that look like prices ("costs 499 per month")
    for m in re.finditer(
        r"\b(\d{2,6})(?:\.\d{2})?\s*(?:rupees|/month|per month|a month)", text, re.I
    ):
        paise = int(m.group(1)) * 100
        if paise not in allowed:
            violations.append(f"number {m.group(0)!r} is not in the verified facts")
    return violations


def known_provider_mentions(text: str, provider_names: list[str]) -> list[str]:
    return [n for n in provider_names if re.search(rf"\b{re.escape(n)}\b", text, re.I)]
