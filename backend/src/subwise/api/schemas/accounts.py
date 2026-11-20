"""Auth, profile, requirements and memory schemas (blueprint I.2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, EmailStr, Field, SecretStr

from subwise.api.schemas.common import Money
from subwise.core.money import Paise
from subwise.domain.enums import Eligibility, FeatureLevel


class RegisterIn(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: SecretStr


class UserOut(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    created_at: AwareDatetime


class ProfileIn(BaseModel):
    country: Literal["IN"] = "IN"
    currency: Literal["INR"] = "INR"
    budget_paise: Paise | None = None
    budget_period: Literal["monthly", "annual"] = "monthly"
    billing_preference: Literal["monthly", "annual", "any"] = "any"
    ads_tolerance: Literal["ok", "avoid", "never"] = "ok"
    allow_cached_prices: bool = True
    allow_partial_prices: bool = False
    allow_unverified_prices: bool = False
    eligibility: list[Eligibility] = Field(default_factory=list)


class ProfileOut(ProfileIn):
    user_id: str
    monthly_budget: Money | None = None


class MeOut(BaseModel):
    user: UserOut
    profile: ProfileOut


class FeatureRequirement(BaseModel):
    feature_code: str
    level: FeatureLevel
    weight: float = Field(default=0.5, gt=0, le=1)


class RequirementsIO(BaseModel):
    requirements: list[FeatureRequirement]


class FeatureDefOut(BaseModel):
    code: str
    label: str
    category: str | None
    description: str


class MemoryItemOut(BaseModel):
    kind: str
    key: str
    value: dict[str, Any]
    created_at: AwareDatetime | None = None
