"""Application settings.

All file-system paths are derived here from ``data_dir`` so no module ever writes to a path
relative to the current working directory (a TA2 bug, see docs/ta2-migration.md).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables prefixed ``SUBWISE_``
    and from ``<repo>/.env``."""

    model_config = SettingsConfigDict(
        env_prefix="SUBWISE_",
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["development", "test", "demo"] = "development"
    jwt_secret: SecretStr = SecretStr("change-me-to-a-long-random-string")
    data_dir: Path = DEFAULT_DATA_DIR
    country: str = Field(default="IN", min_length=2, max_length=2)

    # Local LLM
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    llm_timeout_s: float = Field(default=60.0, gt=0)

    # Optional discovery. Empty/None => NullSearchProvider (discovery off).
    tavily_api_key: SecretStr | None = None
    playwright_enabled: bool = False

    # Agent bounds (blueprint section D)
    max_clarifications: int = 2
    max_research_rounds: int = 2
    max_revisions: int = 2
    recursion_limit: int = 40
    run_timeout_s: float = 600.0

    @field_validator("data_dir", mode="before")
    @classmethod
    def _empty_data_dir_means_default(cls, value: object) -> object:
        return DEFAULT_DATA_DIR if value in (None, "") else value

    @field_validator("tavily_api_key", mode="before")
    @classmethod
    def _empty_key_means_none(cls, value: object) -> object:
        return None if value in (None, "") else value

    # Derived paths -------------------------------------------------------------------
    @property
    def app_db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def checkpoints_db_path(self) -> Path:
        return self.data_dir / "checkpoints.db"

    @property
    def memory_db_path(self) -> Path:
        return self.data_dir / "memory.db"

    @property
    def sources_dir(self) -> Path:
        return self.data_dir / "sources"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.app_db_path.as_posix()}"

    @property
    def search_enabled(self) -> bool:
        return self.tavily_api_key is not None


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings. Tests construct ``Settings(...)`` directly instead."""
    return Settings()
