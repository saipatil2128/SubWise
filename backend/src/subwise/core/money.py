"""Money primitives. All money in SubWise is an integer number of paise (₹1 = 100 paise).

Floats are never used for money (TA2 used ``float``; see docs/ta2-migration.md).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import Field

from subwise.errors import InvalidPrice

MAX_PRICE_PAISE = 5_000_000
Paise = Annotated[int, Field(ge=0, le=MAX_PRICE_PAISE, description="Amount in paise (₹1 = 100).")]
"""Non-negative amount in paise, capped at ₹50,000 (blueprint G.3 format rule)."""

# ₹ 1,499 | Rs. 149 | Rs 1499.00 | INR 99.50 | ₹1,00,000
INR_AMOUNT_RE = re.compile(
    r"(?P<cur>₹|Rs\.?|INR)\s?(?P<num>\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?!\d)(?![.,]\d)",
    re.IGNORECASE,
)
FOREIGN_CURRENCY_RE = re.compile(r"(?:US\$|\$|€|£|USD|EUR|GBP|PKR|AED)\s?\d", re.IGNORECASE)


def _group_indian(rupees: int) -> str:
    s = str(rupees)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join([*groups, tail])


def format_inr(amount: int) -> str:
    """Format paise with Indian digit grouping, e.g. ``49900 -> "₹499.00"``,
    ``10000000 -> "₹1,00,000.00"``. Negative amounts (differences) get a leading minus."""
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise TypeError("format_inr expects integer paise")
    sign = "-" if amount < 0 else ""
    rupees, paise = divmod(abs(amount), 100)
    return f"{sign}₹{_group_indian(rupees)}.{paise:02d}"


def amount_to_paise(number_text: str) -> int:
    """Convert the numeric part of a rupee amount ("1,499" or "99.50") to paise."""
    try:
        value = Decimal(number_text.replace(",", ""))
    except InvalidOperation as exc:
        raise InvalidPrice(f"Not a number: {number_text!r}") from exc
    paise = value * 100
    if paise != paise.to_integral_value():
        raise InvalidPrice(f"More than two decimal places: {number_text!r}")
    result = int(paise)
    if not 0 <= result <= MAX_PRICE_PAISE:
        raise InvalidPrice(f"Amount out of range: {number_text!r}")
    return result


def parse_inr(text: str) -> int:
    """Parse exactly one INR amount such as ``"₹1,499"``, ``"Rs. 149"`` or ``"INR 99.50"``.

    Raises ``InvalidPrice`` if the text holds no INR amount, several, or a foreign currency.
    """
    if FOREIGN_CURRENCY_RE.search(text):
        raise InvalidPrice(f"Foreign currency in {text!r}")
    matches = INR_AMOUNT_RE.findall(text)
    if len(matches) != 1:
        raise InvalidPrice(f"Expected exactly one INR amount in {text!r}, found {len(matches)}")
    return amount_to_paise(matches[0][1])
