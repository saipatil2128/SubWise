"""FastAPI application factory.

Run (from ``backend``):
    uvicorn subwise.main:create_app --factory --reload --host 127.0.0.1 --port 8000
Importing this module has no side effects; ``create_app`` builds the app and the lifespan builds
the container (DB migrations, worker thread, connections).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from subwise import __version__
from subwise.api.error_handlers import register_exception_handlers
from subwise.api.routers.accounts import auth_router, features_router, me_router
from subwise.api.routers.health import health_router
from subwise.api.routers.runs import dashboard_router, reports_router, runs_router, threads_router
from subwise.api.routers.subscriptions import catalog_router, prices_router, subscriptions_router
from subwise.config import Settings, get_settings
from subwise.container import Container, build_container
from subwise.ids import new_id
from subwise.logging_config import configure_logging, request_id_var

API_PREFIX = "/api/v1"
FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.logs_dir)
        owned = container is None
        app.state.container = container or build_container(settings)
        try:
            yield
        finally:
            if owned:
                app.state.container.close()

    app = FastAPI(
        title="SubWise API",
        version=__version__,
        description="Overlap-aware subscription portfolio optimizer with evidence-backed prices.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    register_exception_handlers(app)

    @app.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("X-Request-ID") or new_id("evt")
        request.state.request_id = rid
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    for router in (
        health_router,
        auth_router,
        me_router,
        features_router,
        subscriptions_router,
        catalog_router,
        prices_router,
        threads_router,
        runs_router,
        reports_router,
        dashboard_router,
    ):
        app.include_router(router, prefix=API_PREFIX)

    if FRONTEND_DIST.is_dir():  # single-process mode after `npm run build`
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise StarletteHTTPException(status_code=404, detail="Not Found")
            target = FRONTEND_DIST / path
            if path and target.is_file():
                return FileResponse(target)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app
