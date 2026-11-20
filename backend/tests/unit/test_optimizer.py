"""OAVOE (blueprint H, v2). Plans here are abstract test inputs, not catalog data."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from subwise.core.optimizer import solve
from subwise.core.optimizer.bruteforce import solve_bruteforce
from subwise.domain.enums import OptimizeMode
from subwise.domain.optimization import CandidatePlan, OptimizerInput


def plan(
    pid: str,
    paise: int,
    feats: set[str],
    group: str | None = None,
    lines: set[str] | None = None,
    current: bool = False,
    prereq: tuple[frozenset[str], ...] = (),
) -> CandidatePlan:
    return CandidatePlan(
        plan_id=pid,
        name=pid,
        monthly_paise=paise,
        exclusion_group=group or pid,
        service_lines=frozenset(lines or {group or pid}),
        features=frozenset(feats),
        is_current=current,
        prerequisites_any_of=prereq,
    )


def test_cheaper_plan_lacking_must_have_is_rejected() -> None:
    """Brief case 3."""
    r = solve(
        OptimizerInput(
            candidates=[
                plan("cheap", 10000, {"movies"}),
                plan("full", 30000, {"movies", "live_sports"}),
            ],
            must_have=frozenset({"movies", "live_sports"}),
            budget_paise=50000,
        )
    )
    assert r.best and r.best.plan_ids == ["full"]
    assert {x.plan_id: x.reason_code for x in r.rejected}["cheap"] == "no_new_value"


def test_overlapping_features_counted_once() -> None:
    """Brief case 4: three plans all give movies; only one is kept unless others add value."""
    r = solve(
        OptimizerInput(
            candidates=[
                plan("a", 20000, {"movies"}),
                plan("b", 25000, {"movies"}),
                plan("c", 30000, {"movies", "music_streaming"}),
            ],
            must_have=frozenset({"movies"}),
            weights={"music_streaming": 0.5},
        )
    )
    assert r.best and r.best.plan_ids == ["c"]


def test_budget_too_low_reports_exact_shortfall() -> None:
    """Brief case 5."""
    r = solve(
        OptimizerInput(
            candidates=[plan("v", 30000, {"movies"}), plan("m", 15000, {"music_streaming"})],
            must_have=frozenset({"movies", "music_streaming"}),
            budget_paise=40000,
        )
    )
    assert r.status == "infeasible" and r.best is None
    assert r.diagnosis and r.diagnosis.min_cost_for_must_haves_paise == 45000
    assert r.diagnosis.shortfall_paise == 5000
    assert r.diagnosis.max_must_haves_within_budget == 1


def test_no_plan_has_feature() -> None:
    """Brief case 6."""
    r = solve(
        OptimizerInput(
            candidates=[plan("v", 30000, {"movies"})], must_have=frozenset({"live_sports"})
        )
    )
    assert r.status == "infeasible" and r.diagnosis
    assert r.diagnosis.uncoverable_features == ["live_sports"]


def test_no_candidates() -> None:
    r = solve(OptimizerInput(candidates=[], must_have=frozenset({"movies"})))
    assert r.status == "no_candidates" and r.best is None


def test_tiers_of_one_service_are_mutually_exclusive() -> None:
    r = solve(
        OptimizerInput(
            candidates=[
                plan("nf_basic", 20000, {"movies"}, group="netflix"),
                plan("nf_prem", 60000, {"movies", "uhd_4k"}, group="netflix"),
            ],
            weights={"uhd_4k": 1.0},
        )
    )
    assert r.best and r.best.plan_ids == ["nf_prem"]
    assert {x.plan_id: x.reason_code for x in r.rejected}["nf_basic"] == "same_service_line"


def test_same_provider_different_service_lines_can_be_combined() -> None:
    """v2 revision 2: Prime (bundle) + Amazon Music Unlimited are both Amazon, both allowed."""
    r = solve(
        OptimizerInput(
            candidates=[
                plan(
                    "prime",
                    12500,
                    {"movies", "music_streaming"},
                    group="prime_membership",
                    lines={"prime_membership", "prime_video"},
                ),
                plan(
                    "amu",
                    9900,
                    {"music_streaming", "ad_free_music"},
                    group="amazon_music_unlimited",
                ),
            ],
            must_have=frozenset({"movies", "ad_free_music"}),
        )
    )
    assert r.best and r.best.plan_ids == ["amu", "prime"]


def test_bundle_beats_two_singles_and_counts_retention_through_bundle() -> None:
    r = solve(
        OptimizerInput(
            candidates=[
                plan(
                    "bundle",
                    15000,
                    {"movies", "music_streaming"},
                    group="b",
                    lines={"b", "video_x"},
                ),
                plan("video_x", 12000, {"movies"}, group="video_x", current=True),
                plan("music", 9000, {"music_streaming"}),
            ],
            must_have=frozenset({"movies", "music_streaming"}),
            current_line_usage={"video_x": 1.0},
            mode=OptimizeMode.SAVINGS,
        )
    )
    assert r.best and r.best.plan_ids == ["bundle"]


def test_addon_requires_its_base_plan() -> None:
    base = plan("base", 10000, {"movies"})
    addon = plan("addon", 5000, {"ad_free_video"}, prereq=(frozenset({"base"}),))
    r = solve(OptimizerInput(candidates=[base, addon], weights={"ad_free_video": 1.0}))
    assert r.best and r.best.plan_ids == ["addon", "base"]
    r2 = solve(
        OptimizerInput(
            candidates=[base, addon],
            weights={"ad_free_video": 1.0},
            excluded_plan_ids={"base": "dropped"},
        )
    )
    assert r2.best and r2.best.plan_ids == []


def test_mandatory_and_excluded_plans() -> None:
    r = solve(
        OptimizerInput(
            candidates=[plan("keep", 30000, {"movies"}), plan("x", 1000, {"movies"})],
            must_have=frozenset({"movies"}),
            mandatory_plan_ids=frozenset({"keep"}),
            excluded_plan_ids={"x": "you dropped it"},
        )
    )
    assert r.best and r.best.plan_ids == ["keep"]
    assert {x.plan_id: x.reason for x in r.rejected}["x"] == "you dropped it"


def test_modes_trade_coverage_for_cost() -> None:
    cands = [
        plan("hd", 20000, {"movies"}, group="s"),
        plan("uhd", 60000, {"movies", "uhd_4k"}, group="s"),
    ]
    base = {"candidates": cands, "must_have": frozenset({"movies"}), "weights": {"uhd_4k": 0.3}}
    best = solve(OptimizerInput(**base, mode=OptimizeMode.BEST))  # type: ignore[arg-type]
    save = solve(OptimizerInput(**base, mode=OptimizeMode.SAVINGS))  # type: ignore[arg-type]
    assert best.best and best.best.plan_ids == ["uhd"]
    assert save.best and save.best.plan_ids == ["hd"]


def test_equal_cost_portfolios_have_no_invented_saving() -> None:
    """Brief case 2 at portfolio level: switching to an equal-cost plan saves nothing."""
    r = solve(
        OptimizerInput(
            candidates=[
                plan("cur", 50000, {"movies"}, current=True),
                plan("alt", 50000, {"movies"}),
            ],
            must_have=frozenset({"movies"}),
        )
    )
    assert r.best and r.current
    assert r.best.total_monthly_paise == r.current.total_monthly_paise == 50000
    assert r.best.plan_ids == ["cur"]  # tie goes to what the user already has


def test_fixed_costs_count_against_budget() -> None:
    r = solve(
        OptimizerInput(
            candidates=[plan("v", 30000, {"movies"})],
            must_have=frozenset({"movies"}),
            budget_paise=40000,
            fixed_monthly_paise=15000,
        )
    )
    assert r.status == "infeasible"


FEATS = ["movies", "music_streaming", "uhd_4k", "ad_free_music", "live_sports"]


@st.composite
def problems(draw: st.DrawFn) -> OptimizerInput:
    n = draw(st.integers(min_value=1, max_value=9))
    groups = draw(
        st.lists(st.sampled_from(["g1", "g2", "g3", "g4", "g5", "g6"]), min_size=n, max_size=n)
    )
    cands = []
    for i in range(n):
        feats = set(draw(st.lists(st.sampled_from(FEATS), max_size=3)))
        cands.append(
            plan(
                f"p{i}",
                draw(st.integers(1000, 60000)),
                feats,
                group=groups[i],
                current=draw(st.booleans()),
            )
        )
    must = frozenset(draw(st.lists(st.sampled_from(FEATS[:2]), max_size=2)))
    weights = {
        f: draw(st.sampled_from([0.3, 0.6, 1.0]))
        for f in draw(st.lists(st.sampled_from(FEATS[2:]), max_size=2))
    }
    budget = draw(st.one_of(st.none(), st.integers(10000, 150000)))
    usage = {
        f"g{i}": draw(st.sampled_from([0.0, 0.6, 1.0]))
        for i in draw(st.lists(st.integers(1, 6), max_size=2))
    }
    return OptimizerInput(
        candidates=cands,
        must_have=must,
        weights=weights,
        budget_paise=budget,
        current_line_usage=usage,
        alternatives=0,
    )


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(problems())
def test_ilp_matches_bruteforce(p: OptimizerInput) -> None:
    expected = solve_bruteforce(p)
    got = solve(p)
    if expected is None:
        assert got.status == "infeasible"
        return
    assert got.status == "optimal" and got.best is not None
    assert abs(got.best.score - expected[0]) < 1e-6
    assert got.best.monthly_paise == expected[1]
