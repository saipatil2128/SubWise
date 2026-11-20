"""Deterministic cost maths (TA1 equal-cost rule preserved). Pure module; money in paise."""

from __future__ import annotations

from dataclasses import dataclass

from subwise.core.money import format_inr
from subwise.domain.enums import BillingCycle

EQUAL_COST_MESSAGE = "There is no difference between the plans."
"""Exact sentence preserved from TA1's ``compare_plans`` equal-cost test."""


@dataclass(frozen=True, slots=True)
class MonthlyEquivalent:
    paise: int
    remainder_paise: int  # integer-division remainder, recorded instead of rounding silently


@dataclass(frozen=True, slots=True)
class Comparison:
    cheaper: str | None  # "a", "b" or None when equal
    monthly_difference_paise: int
    annual_difference_paise: int
    message: str


def _check(amount: int, name: str = "price") -> None:
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise ValueError(f"{name} must be a non-negative integer number of paise")


def monthly_equivalent(price_paise: int, cycle: BillingCycle | int) -> MonthlyEquivalent:
    """Price per month for a plan billed every ``cycle`` months (rounded half up to the paisa)."""
    _check(price_paise)
    months = int(BillingCycle(cycle))
    whole, rem = divmod(price_paise, months)
    rounded = whole + (1 if rem * 2 >= months and rem else 0)
    return MonthlyEquivalent(paise=rounded, remainder_paise=rem)


def annual_cost(price_paise: int, cycle: BillingCycle | int) -> int:
    """Exact cost over 12 months in paise (12 is divisible by every supported cycle)."""
    _check(price_paise)
    months = int(BillingCycle(cycle))
    return price_paise * (12 // months)


def first_year_cost(intro_monthly_paise: int, intro_months: int, renewal_monthly_paise: int) -> int:
    """intro × n + renewal × (12 − n) for monthly-billed promotions (blueprint H.5)."""
    _check(intro_monthly_paise, "intro")
    _check(renewal_monthly_paise, "renewal")
    if not 0 <= intro_months <= 12:
        raise ValueError("intro_months must be between 0 and 12")
    return intro_monthly_paise * intro_months + renewal_monthly_paise * (12 - intro_months)


def compare_plans(a_monthly_paise: int, b_monthly_paise: int) -> Comparison:
    """Compare two monthly prices. Equal prices return ``EQUAL_COST_MESSAGE`` and zero
    differences; savings are never invented (TA1 requirement)."""
    _check(a_monthly_paise, "a")
    _check(b_monthly_paise, "b")
    if a_monthly_paise == b_monthly_paise:
        return Comparison(None, 0, 0, EQUAL_COST_MESSAGE)
    diff = abs(a_monthly_paise - b_monthly_paise)
    cheaper = "a" if a_monthly_paise < b_monthly_paise else "b"
    label = "Plan A" if cheaper == "a" else "Plan B"
    return Comparison(
        cheaper,
        diff,
        diff * 12,
        f"{label} is cheaper by {format_inr(diff)}/month ({format_inr(diff * 12)}/year).",
    )
