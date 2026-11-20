from __future__ import annotations

from subwise.core.optimizer import solve
from subwise.core.report_facts import (
    PlanFact,
    build_report_facts,
    check_numbers,
    render_template_report,
    template_summary,
)
from subwise.domain.enums import NextAction
from subwise.domain.optimization import CandidatePlan, OptimizerInput
from subwise.llm.fallbacks import amount_stated, decide_rules, parse_intent_rules


def _facts():  # type: ignore[no-untyped-def]
    cands = [
        CandidatePlan(
            plan_id="cur",
            name="Old Plan",
            monthly_paise=50000,
            exclusion_group="a",
            service_lines=frozenset({"a"}),
            features=frozenset({"movies"}),
            is_current=True,
        ),
        CandidatePlan(
            plan_id="new",
            name="New Plan",
            monthly_paise=20000,
            exclusion_group="b",
            service_lines=frozenset({"b"}),
            features=frozenset({"movies"}),
        ),
    ]
    res = solve(
        OptimizerInput(
            candidates=cands, must_have=frozenset({"movies"}), budget_paise=60000, mode="savings"
        )
    )  # type: ignore[arg-type]
    plans = {
        "cur": PlanFact(
            plan_id="cur",
            name="Old Plan",
            provider_name="X",
            monthly_display="₹500.00",
            price_display="₹500.00",
            billing_cycle_months=1,
            label="user_entered",
            is_current=True,
        ),
        "new": PlanFact(
            plan_id="new",
            name="New Plan",
            provider_name="Y",
            monthly_display="₹200.00",
            price_display="₹200.00",
            billing_cycle_months=1,
            label="live_verified",
            source_url="https://example.invalid/in",
        ),
    }
    return build_report_facts(
        res,
        plans=plans,
        current_items=[
            {"name": "Old Plan", "monthly_paise": 50000, "usage": "weekly", "plan_id": "cur"}
        ],
        fixed_items=[],
        provider_names=["Netflix", "Spotify"],
        data_issues=["X failed"],
    )


def test_facts_compute_savings_and_changes() -> None:
    f = _facts()
    assert f.recommended_total_display == "₹200.00"
    assert f.monthly_saving_display == "₹300.00" and f.annual_saving_display == "₹3,600.00"
    assert f.add == ["New Plan"] and f.drop == ["Old Plan"] and f.within_budget is True


def test_template_mentions_every_key_fact() -> None:
    f = _facts()
    md = render_template_report(f)
    for text in (
        "₹200.00",
        "₹300.00",
        "₹3,600.00",
        "within budget",
        "New Plan",
        "X failed",
        "live, verified",
    ):
        assert text in md
    assert "saving ₹300.00" in template_summary(f)


def test_check_numbers_passes_faithful_text_and_catches_invented_numbers() -> None:
    f = _facts()
    assert check_numbers("You would pay ₹200.00 a month and save ₹300.00.", f) == []
    assert check_numbers("You would save ₹350.00 a month.", f)
    assert check_numbers("It costs 199 per month.", f)


def test_rule_parser_extracts_needs_budget_and_mode() -> None:
    out = parse_intent_rules(
        "I mainly watch movies and cricket, and listen to music. "
        "My budget is ₹1,000. Help me reduce costs. Keep Spotify."
    )
    assert {"movies", "live_sports", "music_streaming"} <= set(out["must_have"])  # type: ignore[arg-type]
    assert out["budget_rupees"] == 1000 and out["mode"] == "savings"
    assert out["keep_providers"] == ["spotify"]
    assert set(out["categories"]) == {"video", "music"}  # type: ignore[arg-type]


def test_budget_guard_rejects_numbers_the_user_never_typed() -> None:
    assert amount_stated("my budget is ₹1,000 a month", 1000)
    assert not amount_stated("my budget is ₹1,000 a month", 1200)


def test_decide_rule_table() -> None:
    assert (
        decide_rules(all_must_haves_usable=True, failed_providers=0, research_round=1, max_rounds=2)
        is NextAction.PROCEED
    )
    assert (
        decide_rules(
            all_must_haves_usable=False, failed_providers=2, research_round=1, max_rounds=2
        )
        is NextAction.RESEARCH_MORE
    )
    assert (
        decide_rules(
            all_must_haves_usable=False, failed_providers=2, research_round=2, max_rounds=2
        )
        is NextAction.PROCEED_WITH_GAPS
    )
