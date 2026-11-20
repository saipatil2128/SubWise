"""Auth, profile, requirements and memory schemas (blueprint I.2)."""

from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, BaseModel, EmailStr, Field, SecretStr

from subwise.core.money import Paise
from subwise.domain.enums import FeatureLevel


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
    monthly_budget_paise: Paise | None = None
    country: str = Field(default="IN", min_length=2, max_length=2)
    billing_preference: str = Field(default="any", pattern=r"^(monthly|annual|any)$")
    ads_tolerance: str = Field(default="ok", pattern=r"^(ok|avoid|never)$")
    allow_unverified_prices: bool = False
    eligibility: list[str] = Field(default_factory=list)  # e.g. ["student"]


class ProfileOut(ProfileIn):
    user_id: str


class MeOut(BaseModel):
    user: UserOut
    profile: ProfileOut | None


class FeatureRequirement(BaseModel):
    feature_code: str
    level: FeatureLevel
    weight: float = Field(default=0.5, gt=0, le=1)


class RequirementsIO(BaseModel):
    requirements: list[FeatureRequirement]


class MemoryItemOut(BaseModel):
    kind: str
    key: str
    value: dict[str, Any]
    created_at: AwareDatetime | None = None
