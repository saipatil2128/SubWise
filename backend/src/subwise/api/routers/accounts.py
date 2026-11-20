"""Auth, /me, profile, requirements and learned memory. Implementation: M3 (memory: M9)."""

from __future__ import annotations

from fastapi import APIRouter, status

from subwise.api.deps import CurrentUser
from subwise.api.schemas.accounts import (
    LoginIn,
    MemoryItemOut,
    MeOut,
    ProfileIn,
    ProfileOut,
    RegisterIn,
    RequirementsIO,
    UserOut,
)
from subwise.api.schemas.common import ERROR_RESPONSES
from subwise.errors import NotImplementedYet

auth_router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)
me_router = APIRouter(prefix="/me", tags=["me"], responses=ERROR_RESPONSES)


@auth_router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn) -> UserOut:
    raise NotImplementedYet("M3", "Registration")


@auth_router.post("/login", response_model=UserOut)
def login(body: LoginIn) -> UserOut:
    raise NotImplementedYet("M3", "Login")


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    raise NotImplementedYet("M3", "Logout")


@me_router.get("", response_model=MeOut)
def get_me(user: CurrentUser) -> MeOut:
    raise NotImplementedYet("M3")


@me_router.get("/profile", response_model=ProfileOut)
def get_profile(user: CurrentUser) -> ProfileOut:
    raise NotImplementedYet("M3")


@me_router.put("/profile", response_model=ProfileOut)
def put_profile(body: ProfileIn, user: CurrentUser) -> ProfileOut:
    raise NotImplementedYet("M3")


@me_router.get("/requirements", response_model=RequirementsIO)
def get_requirements(user: CurrentUser) -> RequirementsIO:
    raise NotImplementedYet("M3")


@me_router.put("/requirements", response_model=RequirementsIO)
def put_requirements(body: RequirementsIO, user: CurrentUser) -> RequirementsIO:
    raise NotImplementedYet("M3")


@me_router.get("/memory", response_model=list[MemoryItemOut])
def list_memory(user: CurrentUser) -> list[MemoryItemOut]:
    raise NotImplementedYet("M9")


@me_router.delete("/memory/{kind}/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(kind: str, key: str, user: CurrentUser) -> None:
    raise NotImplementedYet("M9")
