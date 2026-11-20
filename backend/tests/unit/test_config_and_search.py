"""Tavily is optional: no key or no package => NullSearchProvider, app still healthy."""

from __future__ import annotations

from pathlib import Path

import pytest

from subwise.config import DEFAULT_DATA_DIR, Settings
from subwise.research import search as search_mod
from subwise.research.search import NullSearchProvider, get_search_provider


def test_empty_values_fall_back_to_defaults() -> None:
    s = Settings(_env_file=None, data_dir="", tavily_api_key="")
    assert s.data_dir == DEFAULT_DATA_DIR
    assert s.tavily_api_key is None and not s.search_enabled
    assert s.ollama_model == "qwen2.5:3b"


def test_all_paths_derive_from_data_dir(tmp_path: Path) -> None:
    s = Settings(_env_file=None, data_dir=tmp_path)
    for p in (s.app_db_path, s.checkpoints_db_path, s.memory_db_path, s.sources_dir, s.logs_dir):
        assert p.is_relative_to(tmp_path)
    assert s.database_url.startswith("sqlite:///")


def test_no_key_means_null_provider() -> None:
    provider = get_search_provider(Settings(_env_file=None, tavily_api_key=None))
    assert isinstance(provider, NullSearchProvider)
    assert provider.search("netflix plans", country="IN") == []


def test_key_without_package_still_null(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search_mod, "tavily_installed", lambda: False)
    provider = get_search_provider(Settings(_env_file=None, tavily_api_key="tvly-x"))
    assert isinstance(provider, NullSearchProvider)


def test_key_and_package_selects_tavily(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search_mod, "tavily_installed", lambda: True)
    provider = get_search_provider(Settings(_env_file=None, tavily_api_key="tvly-x"))
    assert provider.name == "tavily" and provider.enabled
