"""Auth, /me, profile, requirements, feature vocabulary and learned memory."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from subwise.api.deps import ContainerDep, CurrentUser, DbDep, require_csrf
from subwise.api.schemas.accounts import (
    FeatureDefOut,
    LoginIn,
    MemoryItemOut,
    MeOut,
    ProfileIn,
    ProfileOut,
    RegisterIn,
    RequirementsIO,
    UserOut,
)
from subwise.api.schemas.common import ERROR_RESPONSES, Money
from subwise.core.features import FEATURE_CODES, FEATURES
from subwise.core.money import format_inr
from subwise.db import repositories as repo
from subwise.db.models import User, UserProfile
from subwise.errors import NotFound, ValidationFailed
from subwise.memory.learned import MemoryKind
from subwise.services import auth

auth_router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)
me_router = APIRouter(prefix="/me", tags=["me"], responses=ERROR_RESPONSES)
features_router = APIRouter(prefix="/features", tags=["catalog"], responses=ERROR_RESPONSES)


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, display_name=u.display_name, created_at=u.created_at)


def _profile_out(p: UserProfile) -> ProfileOut:
    monthly = None
    if p.budget_paise is not None:
        mb = p.budget_paise if p.budget_period == "monthly" else p.budget_paise // 12
        monthly = Money(paise=mb, display=format_inr(mb))
    return ProfileOut(
        user_id=p.user_id,
        country="IN",
        currency="INR",
        budget_paise=p.budget_paise,
        budget_period=p.budget_period,
        billing_preference=p.billing_preference,
        ads_tolerance=p.ads_tolerance,
        allow_cached_prices=p.allow_cached_prices,
        allow_partial_prices=p.allow_partial_prices,
        allow_unverified_prices=p.allow_unverified_prices,
        eligibility=list(p.eligibility or []),
        monthly_budget=monthly,
    )


def _set_cookie(response: Response, c: ContainerDep, user_id: str) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.issue_token(c.settings, user_id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=int(auth.TOKEN_TTL.total_seconds()),
        path="/",
    )


@auth_router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def register(body: RegisterIn, response: Response, db: DbDep, c: ContainerDep) -> UserOut:
    user = auth.register(
        db,
        email=body.email,
        password=body.password.get_secret_value(),
        display_name=body.display_name,
    )
    _set_cookie(response, c, user.id)
    return _user_out(user)


@auth_router.post("/login", response_model=UserOut, dependencies=[Depends(require_csrf)])
def login(body: LoginIn, response: Response, db: DbDep, c: ContainerDep) -> UserOut:
    user = auth.authenticate(db, email=body.email, password=body.password.get_secret_value())
    _set_cookie(response, c, user.id)
    return _user_out(user)


@auth_router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
def logout(response: Response) -> Response:
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@me_router.get("", response_model=MeOut)
def get_me(user: CurrentUser, db: DbDep) -> MeOut:
    u = repo.get_user(db, user.user_id)
    return MeOut(user=_user_out(u), profile=_profile_out(repo.get_or_create_profile(db, u.id)))


@me_router.get("/profile", response_model=ProfileOut)
def get_profile(user: CurrentUser, db: DbDep) -> ProfileOut:
    return _profile_out(repo.get_or_create_profile(db, user.user_id))


@me_router.put("/profile", response_model=ProfileOut)
def put_profile(body: ProfileIn, user: CurrentUser, db: DbDep) -> ProfileOut:
    prof = repo.get_or_create_profile(db, user.user_id)
    for field, value in body.model_dump().items():
        setattr(
            prof,
            field,
            [e.value if hasattr(e, "value") else e for e in value]
            if field == "eligibility"
            else value,
        )
    db.flush()
    return _profile_out(prof)


@me_router.get("/requirements", response_model=RequirementsIO)
def get_requirements(user: CurrentUser, db: DbDep) -> RequirementsIO:
    return RequirementsIO.model_validate(
        {
            "requirements": [
                {"feature_code": r.feature_code, "level": r.level, "weight": r.weight}
                for r in repo.list_requirements(db, user.user_id)
            ]
        }
    )


@me_router.put("/requirements", response_model=RequirementsIO)
def put_requirements(body: RequirementsIO, user: CurrentUser, db: DbDep) -> RequirementsIO:
    unknown = [r.feature_code for r in body.requirements if r.feature_code not in FEATURE_CODES]
    if unknown:
        raise ValidationFailed("Unknown feature codes.", details={"unknown": unknown})
    repo.replace_requirements(
        db,
        user.user_id,
        [r.model_dump(mode="json") for r in body.requirements if r.level != "none"],
    )
    return get_requirements(user, db)


@me_router.get("/memory", response_model=list[MemoryItemOut])
def list_memory(user: CurrentUser, c: ContainerDep) -> list[MemoryItemOut]:
    return [
        MemoryItemOut(kind=i.kind.value, key=i.key, value=i.value, created_at=i.created_at)
        for i in c.memory.list_for_user(user.user_id)
    ]


@me_router.delete("/memory/{kind}/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(kind: str, key: str, user: CurrentUser, c: ContainerDep) -> Response:
    if kind not in MemoryKind.__members__.values():
        raise NotFound("Unknown memory kind.")
    if not c.memory.forget(user.user_id, MemoryKind(kind), key):
        raise NotFound("Memory item not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@features_router.get("", response_model=list[FeatureDefOut])
def list_features() -> list[FeatureDefOut]:
    return [
        FeatureDefOut(
            code=f.code,
            label=f.label,
            description=f.description,
            category=f.category.value if f.category else None,
        )
        for f in FEATURES
    ]
