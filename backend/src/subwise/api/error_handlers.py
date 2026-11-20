"""Render every error as ``ErrorEnvelope`` (blueprint J.1)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from subwise.errors import ErrorBody, ErrorCode, ErrorEnvelope, SubWiseError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def _envelope(status: int, body: ErrorBody) -> JSONResponse:
    return JSONResponse(status_code=status, content=ErrorEnvelope(error=body).model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers so every error response uses ``ErrorEnvelope``."""

    @app.exception_handler(SubWiseError)
    async def _subwise(request: Request, exc: SubWiseError) -> JSONResponse:
        return _envelope(
            exc.http_status,
            ErrorBody(
                code=exc.code.value,
                message=exc.message,
                retryable=exc.retryable,
                details=exc.details,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", ())), "msg": str(e.get("msg", ""))} for e in exc.errors()
        ]
        return _envelope(
            422,
            ErrorBody(
                code=ErrorCode.VALIDATION_FAILED.value,
                message="Request validation failed.",
                details={"errors": errors},
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.INTERNAL_ERROR
        return _envelope(
            exc.status_code,
            ErrorBody(code=code.value, message=str(exc.detail), request_id=_request_id(request)),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return _envelope(
            500,
            ErrorBody(
                code=ErrorCode.INTERNAL_ERROR.value,
                message="An internal error occurred.",
                request_id=_request_id(request),
            ),
        )
