"""Typed error hierarchy and the JSON error envelope model (blueprint section J.1).

Pure module (no web framework imports) so ``core/`` may raise these errors. HTTP rendering
lives in ``subwise.api.error_handlers``.

Every error that reaches the HTTP layer is rendered as::

    {"error": {"code": "...", "message": "...", "retryable": false,
               "details": {}, "request_id": "..."}}
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    CONFLICT = "CONFLICT"
    RUN_IN_PROGRESS = "RUN_IN_PROGRESS"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_INVALID_OUTPUT = "LLM_INVALID_OUTPUT"
    LLM_NUMBER_MISMATCH = "LLM_NUMBER_MISMATCH"
    SEARCH_UNAVAILABLE = "SEARCH_UNAVAILABLE"
    FETCH_FAILED = "FETCH_FAILED"
    SOURCE_DISALLOWED = "SOURCE_DISALLOWED"
    INVALID_PRICE = "INVALID_PRICE"
    DATA_QUALITY = "DATA_QUALITY"
    OPTIMIZER_INFEASIBLE = "OPTIMIZER_INFEASIBLE"
    OPTIMIZER_ERROR = "OPTIMIZER_ERROR"
    PERSISTENCE_ERROR = "PERSISTENCE_ERROR"
    DB_UNAVAILABLE = "DB_UNAVAILABLE"
    RUN_TIMEOUT = "RUN_TIMEOUT"
    WORKER_LOST = "WORKER_LOST"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class SubWiseError(Exception):
    """Base class. Subclasses fix ``code``, ``http_status`` and ``retryable``."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    http_status: int = 500
    retryable: bool = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class ValidationFailed(SubWiseError):
    code, http_status = ErrorCode.VALIDATION_FAILED, 422


class NotFound(SubWiseError):
    code, http_status = ErrorCode.NOT_FOUND, 404


class Forbidden(SubWiseError):
    code, http_status = ErrorCode.FORBIDDEN, 403


class Unauthenticated(SubWiseError):
    code, http_status = ErrorCode.UNAUTHENTICATED, 401


class Conflict(SubWiseError):
    code, http_status = ErrorCode.CONFLICT, 409


class RunInProgress(Conflict):
    code = ErrorCode.RUN_IN_PROGRESS


class ExternalServiceError(SubWiseError):
    code, http_status, retryable = ErrorCode.INTERNAL_ERROR, 502, True


class LLMUnavailable(ExternalServiceError):
    code, http_status = ErrorCode.LLM_UNAVAILABLE, 503


class LLMTimeout(ExternalServiceError):
    code, http_status = ErrorCode.LLM_TIMEOUT, 504


class LLMInvalidOutput(ExternalServiceError):
    code, retryable = ErrorCode.LLM_INVALID_OUTPUT, False


class SearchUnavailable(ExternalServiceError):
    code, http_status = ErrorCode.SEARCH_UNAVAILABLE, 503


class FetchFailed(ExternalServiceError):
    code = ErrorCode.FETCH_FAILED


class SourceDisallowed(ExternalServiceError):
    code, retryable = ErrorCode.SOURCE_DISALLOWED, False


class InvalidPrice(SubWiseError):
    code, http_status = ErrorCode.INVALID_PRICE, 422


class DataQualityError(SubWiseError):
    code, http_status = ErrorCode.DATA_QUALITY, 422


class OptimizerInfeasible(SubWiseError):
    code, http_status = ErrorCode.OPTIMIZER_INFEASIBLE, 422


class PersistenceError(SubWiseError):
    code, http_status, retryable = ErrorCode.PERSISTENCE_ERROR, 503, True


# ----------------------------------------------------------------------------- envelope
class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
