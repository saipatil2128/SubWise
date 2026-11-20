"""Authentication: argon2id password hashes + short-lived JWT in an HttpOnly cookie, plus a
custom-header CSRF check on unsafe methods (blueprint J.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from subwise.config import Settings
from subwise.db.models import User, UserProfile
from subwise.errors import Conflict, Unauthenticated, ValidationFailed
from subwise.ids import new_id

COOKIE_NAME = "subwise_session"
CSRF_HEADER = "X-SubWise-CSRF"
TOKEN_TTL = timedelta(days=7)
_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(password, hashed)
    except Exception:
        return False


def register(s: Session, *, email: str, password: str, display_name: str) -> User:
    email = email.strip().lower()
    if len(password) < 10:
        raise ValidationFailed("Password must be at least 10 characters.")
    if s.scalar(select(User).where(User.email == email)) is not None:
        raise Conflict("An account with this email already exists.")
    user = User(
        id=new_id("usr"),
        email=email,
        password_hash=hash_password(password),
        display_name=display_name.strip(),
    )
    s.add(user)
    s.flush()
    s.add(UserProfile(user_id=user.id, eligibility=[]))
    return user


def authenticate(s: Session, *, email: str, password: str) -> User:
    user = s.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise Unauthenticated("Email or password is incorrect.")
    return user


def issue_token(settings: Settings, user_id: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + TOKEN_TTL},
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def decode_token(settings: Settings, token: str) -> str:
    try:
        data = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise Unauthenticated("Your session has expired. Please sign in again.") from exc
    sub = data.get("sub")
    if not isinstance(sub, str) or not sub.startswith("usr_"):
        raise Unauthenticated("Invalid session.")
    return sub
