"""Money primitives. All money in SubWise is an integer number of paise (₹1 = 100 paise).

Floats are never used for money (TA2 used ``float``; see docs/ta2-migration.md).
Implementation: roadmap module M5.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from subwise.errors import NotImplementedYet

Paise = Annotated[int, Field(ge=0, le=5_000_000, description="Amount in paise (₹1 = 100).")]
"""Non-negative amount in paise, capped at ₹50,000 (blueprint G.3 format rule)."""

MAX_PRICE_PAISE = 5_000_000


def format_inr(amount: int) -> str:
    """Format paise as an Indian-rupee display string, e.g. ``49900 -> "₹499.00"``.

    Must use Indian digit grouping (``₹1,00,000.00``). Implemented in M5.
    """
    raise NotImplementedYet("M5", "format_inr")


def parse_inr(text: str) -> int:
    """Parse a rupee amount such as ``"₹1,499"``, ``"Rs. 149"`` or ``"INR 99.50"`` into paise.

    Raises ``InvalidPrice`` for anything that is not a single unambiguous INR amount.
    Implemented in M5.
    """
    raise NotImplementedYet("M5", "parse_inr")
