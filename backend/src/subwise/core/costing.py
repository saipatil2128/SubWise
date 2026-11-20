"""Deterministic cost maths (blueprint F, TA1 equal-cost rule). Implementation: M5.

Pure module: no I/O, no LLM. Money in paise only.
"""

from __future__ import annotations

from dataclasses import dataclass

from subwise.domain.enums import BillingCycle
from subwise.errors import NotImplementedYet

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
    message: str  # EQUAL_COST_MESSAGE when equal


def monthly_equivalent(price_paise: int, cycle: BillingCycle) -> MonthlyEquivalent:
    """Price per month for a plan billed every ``cycle`` months (M5)."""
    raise NotImplementedYet("M5", "monthly_equivalent")


def annual_cost(price_paise: int, cycle: BillingCycle) -> int:
    """Cost over 12 months in paise (M5)."""
    raise NotImplementedYet("M5", "annual_cost")


def first_year_cost(intro_paise: int, intro_months: int, renewal_paise: int) -> int:
    """intro × n + renewal × (12 − n), all monthly amounts in paise (blueprint H.5) (M5)."""
    raise NotImplementedYet("M5", "first_year_cost")


def compare_plans(a_monthly_paise: int, b_monthly_paise: int) -> Comparison:
    """Compare two monthly prices. Equal prices MUST return ``EQUAL_COST_MESSAGE`` and zero
    differences; never invent savings (TA1 requirement) (M5)."""
    raise NotImplementedYet("M5", "compare_plans")
