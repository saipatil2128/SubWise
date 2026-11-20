"""Price-observation validation rules (blueprint G.3, v2). Implementation: M5.

Pure module. Decides an observation's ``ObservationStatus`` and ``Freshness`` from data only.
"""

from __future__ import annotations

from datetime import datetime

from subwise.domain.catalog import Plan, Provider
from subwise.domain.enums import Freshness, ObservationStatus
from subwise.domain.evidence import PlanObservation, SourceDocument, ValidatedPlan
from subwise.errors import NotImplementedYet

FRESH_MAX_DAYS = 30
STALE_MAX_DAYS = 90
PLAUSIBLE_RATIO = (1 / 3, 3.0)
CONFLICT_WINDOW_DAYS = 7
CONFLICT_TOLERANCE_PAISE = 100


def freshness(observed_at: datetime, now: datetime) -> tuple[Freshness, int]:
    """Return (freshness, age_days): <=30 fresh, 31-90 stale, >90 expired (M5)."""
    raise NotImplementedYet("M5", "freshness")


def evidence_text_present(snippet: str, page_text: str, price_paise: int) -> bool:
    """True if ``snippet`` occurs verbatim (whitespace-normalised) in ``page_text`` and the
    INR amount inside it parses to ``price_paise`` (M5)."""
    raise NotImplementedYet("M5", "evidence_text_present")


def validate_observation(
    obs: PlanObservation,
    *,
    plan: Plan,
    provider: Provider,
    document: SourceDocument | None,
    page_text: str | None,
    previous_verified_paise: int | None,
    now: datetime,
) -> ValidatedPlan:
    """Apply binding + format + plausibility + freshness rules (M5).

    verified  = all five bindings + evidence present + extracted_by adapter + checks pass
    partial   = all five bindings + evidence present, but LLM-extracted or features incomplete
    unverified = anything else that parsed
    """
    raise NotImplementedYet("M5", "validate_observation")


def detect_conflicts(observations: list[PlanObservation]) -> list[tuple[int, int]]:
    """Index pairs of observations for the same plan/kind within 7 days differing by > ₹1 (M5)."""
    raise NotImplementedYet("M5", "detect_conflicts")


def overall_status(validated: ValidatedPlan) -> ObservationStatus:
    """Convenience accessor kept for the optimizer's candidate filter (M5)."""
    raise NotImplementedYet("M5", "overall_status")
