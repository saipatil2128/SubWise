"""Opt-in: hits real provider pricing pages.  Run:  pytest -m live   (adapters arrive in M8)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


@pytest.mark.skip(reason="Provider adapters are implemented in roadmap module M8.")
def test_each_registry_adapter_extracts_bound_prices() -> None:
    raise AssertionError("unreachable")
