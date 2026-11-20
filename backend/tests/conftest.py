from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from subwise.config import Settings
from subwise.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Isolated settings: temp data dir, no search key, never reads the developer's .env."""
    return Settings(_env_file=None, env="test", data_dir=tmp_path / "data", tavily_api_key=None)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings), raise_server_exceptions=False) as c:
        yield c
