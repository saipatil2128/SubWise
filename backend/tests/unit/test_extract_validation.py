"""Evidence binding and validation (blueprint G.3, v2). All pages are synthetic test fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tests.conftest import fixture_html

from subwise.core.features import detect_features
from subwise.core.validation import (
    classify,
    detect_conflicts,
    display_label,
    evidence_text_present,
    freshness,
)
from subwise.domain.enums import (
    BindingMethod,
    Category,
    ExtractedBy,
    Freshness,
    ObservationStatus,
    PriceKind,
)
from subwise.research.extract import extract_prices
from subwise.research.registry import get_provider

NETFLIX_URL = "https://help.netflix.com/en/node/24926/in"
SPOTIFY_URL = "https://www.spotify.com/in-en/premium/"


def by_tier(result, tier: str, kind: PriceKind = PriceKind.STANDARD):  # type: ignore[no-untyped-def]
    return [p for p in result.prices if p.tier.key == tier and p.price_kind is kind]


def test_netflix_list_layout_binds_all_five_dimensions() -> None:
    r = extract_prices(get_provider("netflix"), fixture_html("netflix_in.html"), NETFLIX_URL)
    prices = {p.tier.key: p for p in r.prices}
    assert {k: v.price_paise for k, v in prices.items()} == {
        "mobile": 11100,
        "basic": 22200,
        "standard": 33300,
        "premium": 44400,
    }
    assert all(p.fully_bound and p.cycle_months == 1 for p in prices.values())
    prem = {f.code: f.value for f in prices["premium"].features}
    assert prem["uhd_4k"] == "yes" and prem["multi_screen"] == "yes"
    mob = {f.code: f.value for f in prices["mobile"].features}
    assert mob["tv_screen"] == "no"  # "one phone or tablet" stated on the page


def test_spotify_cards_intro_and_renewal_are_separate() -> None:
    r = extract_prices(get_provider("spotify"), fixture_html("spotify_in.html"), SPOTIFY_URL)
    std_renewal = by_tier(r, "standard", PriceKind.RENEWAL)
    std_intro = by_tier(r, "standard", PriceKind.INTRO)
    assert [p.price_paise for p in std_renewal] == [12300]
    assert [(p.price_paise, p.intro_months) for p in std_intro] == [(5500, 3)]
    # The student card mentions "Standard account" - it must not steal the Standard price.
    assert [p.price_paise for p in by_tier(r, "student", PriceKind.RENEWAL)] == [6600]
    assert by_tier(r, "platinum")[0].price_paise == 32100
    assert all(p.fully_bound for p in r.prices)


def test_table_layout_binds_plan_and_cycle_from_headers() -> None:
    r = extract_prices(
        get_provider("apple_music"),
        fixture_html("apple_music_in.html"),
        "https://www.apple.com/in/apple-music/",
    )
    got = {p.tier.key: (p.price_paise, p.cycle_months, p.plan_binding.method) for p in r.prices}
    assert got["individual"] == (13100, 1, BindingMethod.TABLE_CELL)
    assert got["family"][0] == 23200 and got["student"][0] == 7700


def test_region_unbound_when_page_is_not_the_india_variant() -> None:
    r = extract_prices(
        get_provider("netflix"),
        fixture_html("netflix_in.html"),
        "https://help.netflix.com/en/node/24926/us",
    )
    assert r.prices and all(p.region_binding.method is BindingMethod.UNBOUND for p in r.prices)


def test_region_unbound_when_page_shows_another_currency() -> None:
    r = extract_prices(get_provider("netflix"), fixture_html("foreign_currency.html"), NETFLIX_URL)
    assert all(p.region_binding.method is BindingMethod.UNBOUND for p in r.prices)
    assert not any(p.fully_bound for p in r.prices)


def test_provider_unbound_after_redirect_to_unofficial_domain() -> None:
    r = extract_prices(
        get_provider("netflix"),
        fixture_html("netflix_in.html"),
        "https://deals.example-reseller.in/netflix/in",
    )
    assert all(p.provider_binding.method is BindingMethod.UNBOUND for p in r.prices)


def test_price_without_billing_period_is_unbound() -> None:
    html = "<html><body><ul><li>Basic: ₹222</li><li>Premium: ₹444</li></ul></body></html>"
    r = extract_prices(get_provider("spotify"), html, SPOTIFY_URL)  # spotify has no page phrase
    r2 = extract_prices(get_provider("netflix"), html, NETFLIX_URL)  # no "billed monthly" on page
    for res in (r, r2):
        assert all(not p.fully_bound for p in res.prices)


def test_price_next_to_another_plan_name_is_not_stolen() -> None:
    html = (
        "<html><body><p>Plans are billed monthly.</p><div><h3>Standard</h3>"
        "<p>Compare with Premium: ₹444/month</p></div></body></html>"
    )
    r = extract_prices(get_provider("netflix"), html, NETFLIX_URL)
    assert not [p for p in r.prices if p.tier.key == "standard" and p.fully_bound]


def test_two_different_prices_for_same_plan_and_period_are_ambiguous() -> None:
    html = (
        "<html><body><p>billed monthly</p><ul><li>Basic: ₹222/month</li></ul>"
        "<ul><li>Basic: ₹999/month</li></ul></body></html>"
    )
    r = extract_prices(get_provider("netflix"), html, NETFLIX_URL)
    assert r.prices and all(p.plan_binding.method is BindingMethod.UNBOUND for p in r.prices)


def test_no_prices_reports_warning() -> None:
    r = extract_prices(get_provider("netflix"), "<html><body>Sign in</body></html>", NETFLIX_URL)
    assert r.prices == [] and "no plan prices found on the page" in r.warnings


# ----------------------------------------------------------------------------- validation
def test_evidence_must_be_verbatim_and_match_amount() -> None:
    page = "Plans Basic: ₹222/month Premium: ₹444/month"
    assert evidence_text_present("Basic: ₹222/month", page, 22200)
    assert not evidence_text_present("Basic: ₹222/month", page, 33300)
    assert not evidence_text_present("Basic: ₹223/month", page, 22300)


def test_classify_statuses() -> None:
    base = {
        "price_paise": 22200,
        "cycle_months": 1,
        "unbound": [],
        "evidence_present": True,
        "extracted_by": ExtractedBy.ADAPTER,
        "previous_verified_paise": None,
    }
    assert classify(**base).status is ObservationStatus.VERIFIED  # type: ignore[arg-type]
    assert classify(**{**base, "unbound": ["region"]}).status is ObservationStatus.UNVERIFIED  # type: ignore[arg-type]
    assert classify(**{**base, "evidence_present": False}).status is ObservationStatus.UNVERIFIED  # type: ignore[arg-type]
    assert classify(**{**base, "extracted_by": ExtractedBy.LLM}).status is ObservationStatus.PARTIAL  # type: ignore[arg-type]
    assert (
        classify(**{**base, "previous_verified_paise": 2000}).status is ObservationStatus.CONFLICT
    )  # type: ignore[arg-type]
    assert classify(**{**base, "cycle_months": None}).status is ObservationStatus.UNVERIFIED  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (0, Freshness.FRESH),
        (30, Freshness.FRESH),
        (31, Freshness.STALE),
        (90, Freshness.STALE),
        (91, Freshness.EXPIRED),
    ],
)
def test_freshness_boundaries(days: int, expected: Freshness) -> None:
    """Brief case 8 (stale source)."""
    now = datetime(2026, 11, 21, tzinfo=UTC)
    assert freshness(now - timedelta(days=days), now) == (expected, days)


def test_conflicting_prices_detected() -> None:
    """Brief case 9."""
    t = datetime(2026, 11, 1, tzinfo=UTC)
    obs = [
        ("p", "standard", 22200, t),
        ("p", "standard", 22200, t + timedelta(days=2)),
        ("p", "standard", 29900, t + timedelta(days=3)),
        ("q", "standard", 1, t),
    ]
    assert detect_conflicts(obs) == {0, 1, 2}


def test_display_label_never_calls_old_or_failed_data_live() -> None:
    now = datetime(2026, 11, 21, 12, tzinfo=UTC)
    v = ObservationStatus.VERIFIED
    assert (
        display_label(
            status=v, observed_at=now - timedelta(hours=1), now=now, latest_attempt_ok=True
        )
        == "live_verified"
    )
    assert (
        display_label(
            status=v, observed_at=now - timedelta(hours=1), now=now, latest_attempt_ok=False
        )
        == "cached_verified"
    )
    assert (
        display_label(
            status=v, observed_at=now - timedelta(days=2), now=now, latest_attempt_ok=True
        )
        == "cached_verified"
    )


def test_feature_detection_only_states_what_text_says() -> None:
    found = {
        f.code: f.value
        for f in detect_features(
            "Ad-free. 4K Ultra HD. Watch on 4 supported devices at a time.", Category.VIDEO
        )
    }
    assert found["ad_free_video"] == "yes" and found["uhd_4k"] == "yes"
    assert found["multi_screen"] == "yes"
    assert "live_sports" not in found  # not stated -> stays unknown
    with_ads = {f.code: f.value for f in detect_features("Mobile plan with ads", Category.VIDEO)}
    assert with_ads["ad_free_video"] == "no"
