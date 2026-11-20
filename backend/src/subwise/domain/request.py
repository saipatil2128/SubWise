"""RequestSpec: the typed form of a natural-language optimization request (blueprint D.1)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from subwise.core.money import Paise
from subwise.domain.enums import Category, OptimizeMode


class RequestSpec(BaseModel):
    """Produced by `parse_intent` (LLM with JSON-schema output, or the rule-based fallback).

    The LLM never fills money it was not given: ``budget_paise`` is either parsed from an
    explicit ₹ amount in the user's text or copied from the profile.
    """

    model_config = ConfigDict(extra="forbid")

    categories: list[Category] = Field(min_length=1)
    budget_paise: Paise | None = None
    must_have_features: list[str] = Field(default_factory=list)
    nice_to_have: dict[str, float] = Field(default_factory=dict)
    keep_service_lines: list[str] = Field(default_factory=list)
    drop_providers: list[str] = Field(default_factory=list)
    billing_preference: str = Field(default="any", pattern=r"^(monthly|annual|any)$")
    mode: OptimizeMode = OptimizeMode.BEST
    missing_fields: list[str] = Field(default_factory=list)
    source: str = Field(default="llm", pattern=r"^(llm|rules|profile)$")
