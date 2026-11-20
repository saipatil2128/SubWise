"""Liveness endpoint. Phase 1 reports configuration only; live Ollama/DB probes arrive in
M1/M2/M7."""

from __future__ import annotations

from fastapi import APIRouter

from subwise import __version__
from subwise.api.deps import SettingsDep
from subwise.api.schemas.runs import HealthOut
from subwise.research.search import get_search_provider

health_router = APIRouter(tags=["health"])


@health_router.get("/health", response_model=HealthOut)
def health(settings: SettingsDep) -> HealthOut:
    search = get_search_provider(settings)
    return HealthOut(
        status="ok",
        version=__version__,
        environment=settings.env,
        llm="not_checked",
        search="enabled" if search.enabled else "disabled",
        database="not_checked",
    )
