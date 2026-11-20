from __future__ import annotations

import pytest

from subwise.core.costing import (
    EQUAL_COST_MESSAGE,
    annual_cost,
    compare_plans,
    first_year_cost,
    monthly_equivalent,
)
from subwise.core.money import format_inr, parse_inr
from subwise.domain.enums import BillingCycle
from subwise.errors import InvalidPrice


@pytest.mark.parametrize(
    ("paise", "text"),
    [
        (0, "₹0.00"),
        (49900, "₹499.00"),
        (149900, "₹1,499.00"),
        (10000000, "₹1,00,000.00"),
        (12345678, "₹1,23,456.78"),
        (-2400, "-₹24.00"),
    ],
)
def test_format_inr_indian_grouping(paise: int, text: str) -> None:
    assert format_inr(paise) == text


@pytest.mark.parametrize(
    ("text", "paise"),
    [
        ("₹1,499", 149900),
        ("Rs. 149", 14900),
        ("Rs 99.50", 9950),
        ("INR 10,000", 1000000),
        ("only ₹139/month", 13900),
    ],
)
def test_parse_inr(text: str, paise: int) -> None:
    assert parse_inr(text) == paise


@pytest.mark.parametrize("bad", ["$9.99", "no price", "₹1 or ₹2", "₹1.999", "₹60,000"])
def test_parse_inr_rejects(bad: str) -> None:
    with pytest.raises(InvalidPrice):
        parse_inr(bad)


def test_ta1_equal_cost_rule_preserved() -> None:
    """Brief case 2 (TA1 original): equal prices report no difference and no savings."""
    c = compare_plans(50000, 50000)
    assert c.message == EQUAL_COST_MESSAGE == "There is no difference between the plans."
    assert c.cheaper is None and c.monthly_difference_paise == 0 and c.annual_difference_paise == 0


def test_different_prices() -> None:
    """Brief case 1."""
    c = compare_plans(90000, 80000)
    assert c.cheaper == "b"
    assert c.monthly_difference_paise == 10000 and c.annual_difference_paise == 120000
    assert "₹100.00/month" in c.message and "₹1,200.00/year" in c.message


@pytest.mark.parametrize(
    ("price", "cycle", "monthly", "annual"),
    [
        (14900, 1, 14900, 178800),
        (59900, 3, 19967, 239600),
        (149900, 12, 12492, 149900),
        (139000, 12, 11583, 139000),
    ],
)
def test_billing_normalisation(price: int, cycle: int, monthly: int, annual: int) -> None:
    assert monthly_equivalent(price, BillingCycle(cycle)).paise == monthly
    assert annual_cost(price, BillingCycle(cycle)) == annual


def test_promo_first_year() -> None:
    """Brief case 10: intro ₹99 for 3 months then ₹139/month."""
    assert first_year_cost(9900, 3, 13900) == 9900 * 3 + 13900 * 9


@pytest.mark.parametrize("bad", [-1, 1.5, True])
def test_costing_rejects_bad_money(bad: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        monthly_equivalent(bad, BillingCycle.MONTHLY)  # type: ignore[arg-type]


def test_unsupported_cycle() -> None:
    with pytest.raises(ValueError):
        monthly_equivalent(100, 2)  # type: ignore[arg-type]
