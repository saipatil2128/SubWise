"""FastAPI application factory. Run with:  uvicorn subwise.main:app --reload"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from subwise import __version__
from subwise.api.error_handlers import register_exception_handlers
from subwise.api.routers.accounts import auth_router, me_router
from subwise.api.routers.health import health_router
from subwise.api.routers.runs import (
    dashboard_router,
    prices_router,
    reports_router,
    runs_router,
    threads_router,
)
from subwise.api.routers.subscriptions import catalog_router, subscriptions_router
from subwise.config import Settings, get_settings
from subwise.worker.runner import ThreadRunExecutor

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        executor = ThreadRunExecutor()
        app.state.executor = executor
        # M11: sweep_orphaned_runs() goes here.
        yield
        executor.shutdown()

    app = FastAPI(
        title="SubWise API",
        version=__version__,
        description="Overlap-aware subscription portfolio optimizer. Phase 1: stubs return 501.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    register_exception_handlers(app)
    for router in (
        health_router,
        auth_router,
        me_router,
        subscriptions_router,
        catalog_router,
        threads_router,
        runs_router,
        reports_router,
        prices_router,
        dashboard_router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
