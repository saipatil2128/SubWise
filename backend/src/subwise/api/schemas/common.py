"""Shared API shapes. Money is formatted server-side; the client never does money arithmetic."""

from __future__ import annotations

from pydantic import BaseModel, Field

from subwise.core.money import Paise
from subwise.errors import ErrorEnvelope


class Money(BaseModel):
    paise: Paise
    display: str = Field(examples=["₹499.00"])


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


class Accepted(BaseModel):
    status: str = "accepted"


ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorEnvelope, "description": "Not signed in"},
    404: {"model": ErrorEnvelope, "description": "Not found (also used for other users' data)"},
    422: {"model": ErrorEnvelope, "description": "Validation failed"},
    501: {"model": ErrorEnvelope, "description": "Not implemented yet (Phase 1 stub)"},
}
