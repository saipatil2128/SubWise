"""Prefixed ULID identifiers. The prefix makes identity mix-ups visible (blueprint F.1)."""

from __future__ import annotations

from typing import Literal

from ulid import ULID

IdPrefix = Literal["usr", "thr", "run", "rep", "sub", "obs", "doc", "evt", "dec"]


def new_id(prefix: IdPrefix) -> str:
    """e.g. ``new_id("run") -> "run_01JD3Z..."``"""
    return f"{prefix}_{ULID()}"
