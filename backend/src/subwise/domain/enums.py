"""Closed vocabularies shared by API, agent, core and database layers."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class Category(StrEnum):
    VIDEO = "video"
    MUSIC = "music"


class BillingCycle(IntEnum):
    """Billing cycle length in months."""

    MONTHLY = 1
    QUARTERLY = 3
    HALF_YEARLY = 6
    ANNUAL = 12


class UsageFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    OCCASIONALLY = "occasionally"
    NEVER = "never"
    UNKNOWN = "unknown"


USAGE_VALUE: dict[UsageFrequency, float] = {
    UsageFrequency.DAILY: 1.0,
    UsageFrequency.WEEKLY: 0.6,
    UsageFrequency.OCCASIONALLY: 0.2,
    UsageFrequency.NEVER: 0.0,
    UsageFrequency.UNKNOWN: 0.5,
}
"""u(s) in blueprint H.2."""


class FeatureLevel(StrEnum):
    MUST = "must"
    NICE = "nice"
    NONE = "none"


class FeatureValue(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"  # never treated as yes


class Eligibility(StrEnum):
    STUDENT = "student"
    NEW_CUSTOMER = "new_customer"
    TELECOM_CUSTOMER = "telecom_customer"


class ObservationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    CONFLICT = "conflict"


class Freshness(StrEnum):
    FRESH = "fresh"  # <= 30 days
    STALE = "stale"  # 31-90 days
    EXPIRED = "expired"  # > 90 days


class PriceKind(StrEnum):
    STANDARD = "standard"
    INTRO = "intro"
    RENEWAL = "renewal"


class TaxIncluded(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class ExtractedBy(StrEnum):
    ADAPTER = "adapter"
    LLM = "llm"
    MANUAL = "manual"


class FetchMethod(StrEnum):
    HTTPX = "httpx"
    PLAYWRIGHT = "playwright"
    MANUAL = "manual"


class BindingMethod(StrEnum):
    """How one evidence dimension was bound (blueprint G.3)."""

    DOMAIN_MAP = "domain_map"
    SAME_DOM_BLOCK = "same_dom_block"
    SAME_TEXT_WINDOW = "same_text_window"
    ADJACENT_TOKEN = "adjacent_token"
    URL_LOCALE = "url_locale"
    MANUAL = "manual"
    UNBOUND = "unbound"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_CLARIFICATION = "waiting_clarification"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventType(StrEnum):
    NODE_START = "node_start"
    NODE_END = "node_end"
    TOOL_CALL = "tool_call"
    TOOL_ERROR = "tool_error"
    DECISION = "decision"
    FALLBACK = "fallback"
    INTERRUPT = "interrupt"


class Decision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class NextAction(StrEnum):
    RESEARCH_MORE = "research_more"
    PROCEED = "proceed"
    PROCEED_WITH_GAPS = "proceed_with_gaps"
    ASK_USER = "ask_user"


class DecidedBy(StrEnum):
    LLM = "llm"
    RULE = "rule"


class OptimizeMode(StrEnum):
    BEST = "best"
    BALANCED = "balanced"
    SAVINGS = "savings"


class ReportSource(StrEnum):
    LLM = "llm"
    TEMPLATE = "template"
