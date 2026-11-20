"""Health: database, Ollama (server + model), optional search and browser rendering."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

from subwise import __version__
from subwise.api.deps import ContainerDep
from subwise.api.schemas.runs import HealthOut
from subwise.research.search import get_search_provider

health_router = APIRouter(tags=["health"])


@health_router.get("/health", response_model=HealthOut)
async def health(c: ContainerDep) -> HealthOut:
    try:
        with c.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db = "ok"
    except Exception as exc:  # pragma: no cover - reported, not raised
        db = f"error: {exc}"
    llm = await run_in_threadpool(c.llm.health)
    search = get_search_provider(c.settings)
    degraded = db != "ok" or not (llm.reachable and llm.model_present)
    return HealthOut(
        status="degraded" if degraded else "ok",
        version=__version__,
        environment=c.settings.env,
        database=db,
        llm=llm.model_dump(),
        search="enabled" if search.enabled else "disabled",
        playwright="enabled" if c.fetcher.playwright_available else "disabled",
    )
