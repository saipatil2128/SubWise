"""Price-observation validation rules (blueprint G.3, v2). Pure module.

Status meanings:
  verified   - all five dimensions bound, evidence text present in the stored page,
               extracted deterministically by the provider adapter, format + plausibility OK
  partial    - bound and evidenced, but extracted by the LLM (tier 3)
  unverified - any dimension unbound or evidence missing; kept for audit, not used by default
  conflict   - disagrees with a recent verified price for the same plan (both kept, neither used)

Display labels (what the user sees) add *when* and *whether the last fetch worked*:
  live_verified, cached_verified, partial, unverified, conflict, unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from subwise.core.money import INR_AMOUNT_RE, MAX_PRICE_PAISE, amount_to_paise
from subwise.domain.enums import ExtractedBy, Freshness, ObservationStatus
from subwise.errors import InvalidPrice

FRESH_MAX_DAYS = 30
STALE_MAX_DAYS = 90
PLAUSIBLE_LOW, PLAUSIBLE_HIGH = 1 / 3, 3.0
CONFLICT_WINDOW_DAYS = 7
CONFLICT_TOLERANCE_PAISE = 100
LIVE_WINDOW_HOURS = 24
VALID_CYCLES = (1, 3, 6, 12)


def _norm(text: str) -> str:
    return " ".join(text.split())


def freshness(observed_at: datetime, now: datetime) -> tuple[Freshness, int]:
    """(freshness, age_days): <=30 fresh, 31-90 stale, >90 expired."""
    age = max(0, (now - observed_at).days)
    if age <= FRESH_MAX_DAYS:
        return Freshness.FRESH, age
    if age <= STALE_MAX_DAYS:
        return Freshness.STALE, age
    return Freshness.EXPIRED, age


def evidence_text_present(snippet: str, page_text: str, price_paise: int) -> bool:
    """True if ``snippet`` occurs verbatim (whitespace-normalised) in ``page_text`` and an
    INR amount inside it equals ``price_paise``."""
    if not snippet or _norm(snippet) not in _norm(page_text):
        return False
    for m in INR_AMOUNT_RE.finditer(snippet):
        try:
            if amount_to_paise(m.group("num")) == price_paise:
                return True
        except InvalidPrice:
            continue
    return False


@dataclass(frozen=True, slots=True)
class Classification:
    status: ObservationStatus
    reasons: tuple[str, ...]


def classify(
    *,
    price_paise: int,
    cycle_months: int | None,
    unbound: list[str],
    evidence_present: bool,
    extracted_by: ExtractedBy,
    previous_verified_paise: int | None,
) -> Classification:
    reasons: list[str] = []
    if not 0 < price_paise <= MAX_PRICE_PAISE:
        return Classification(ObservationStatus.UNVERIFIED, ("price outside ₹0.01-₹50,000",))
    if cycle_months not in VALID_CYCLES:
        reasons.append("billing period not bound to this price")
    reasons.extend(f"{dim} not bound" for dim in unbound)
    if not evidence_present:
        reasons.append("evidence text not found in the stored page")
    if reasons:
        return Classification(ObservationStatus.UNVERIFIED, tuple(dict.fromkeys(reasons)))
    if previous_verified_paise:
        ratio = price_paise / previous_verified_paise
        if not PLAUSIBLE_LOW <= ratio <= PLAUSIBLE_HIGH:
            return Classification(
                ObservationStatus.CONFLICT,
                (f"implausible change from previous verified price ({ratio:.2f}x)",),
            )
    if extracted_by is ExtractedBy.ADAPTER:
        return Classification(ObservationStatus.VERIFIED, ())
    return Classification(ObservationStatus.PARTIAL, ("extracted by the language model",))


def detect_conflicts(
    observations: list[tuple[str, str, int, datetime]],
) -> set[int]:
    """Indexes of observations (plan_id, kind, paise, observed_at) that conflict: same plan and
    kind within 7 days differing by more than ₹1."""
    bad: set[int] = set()
    for i, (plan_a, kind_a, paise_a, at_a) in enumerate(observations):
        for j in range(i + 1, len(observations)):
            plan_b, kind_b, paise_b, at_b = observations[j]
            if (plan_a, kind_a) != (plan_b, kind_b):
                continue
            if abs((at_a - at_b).days) > CONFLICT_WINDOW_DAYS:
                continue
            if abs(paise_a - paise_b) > CONFLICT_TOLERANCE_PAISE:
                bad.update({i, j})
    return bad


def display_label(
    *,
    status: ObservationStatus,
    observed_at: datetime,
    now: datetime,
    latest_attempt_ok: bool,
) -> str:
    """User-facing label. A previously verified price is 'live_verified' only if the most recent
    fetch of that provider succeeded and the observation is less than 24 hours old."""
    if status is ObservationStatus.VERIFIED:
        hours = (now - observed_at).total_seconds() / 3600
        if latest_attempt_ok and hours <= LIVE_WINDOW_HOURS:
            return "live_verified"
        return "cached_verified"
    return status.value
