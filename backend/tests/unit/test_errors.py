from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from subwise.api.error_handlers import register_exception_handlers
from subwise.errors import (
    ErrorCode,
    LLMTimeout,
    NotFound,
    RunInProgress,
    SubWiseError,
)


def _app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    @app.get("/missing")
    def missing() -> None:
        raise NotFound("No such run.", details={"run_id": "run_1"})

    @app.get("/typed/{n}")
    def typed(n: int) -> int:
        return n

    return app


def test_hierarchy_codes_and_statuses() -> None:
    assert issubclass(LLMTimeout, SubWiseError)
    assert LLMTimeout.code is ErrorCode.LLM_TIMEOUT and LLMTimeout.retryable
    assert RunInProgress.http_status == 409
    err = NotFound("No such run.", details={"run_id": "run_1"})
    assert err.http_status == 404 and err.details == {"run_id": "run_1"}


def test_subwise_error_rendered_as_envelope() -> None:
    resp = TestClient(_app()).get("/missing")
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "No such run.",
            "retryable": False,
            "details": {"run_id": "run_1"},
            "request_id": None,
        }
    }


def test_validation_error_uses_same_envelope() -> None:
    resp = TestClient(_app()).get("/typed/not-a-number")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"
    assert resp.json()["error"]["details"]["errors"]


def test_unknown_route_and_unhandled_exception_hide_internals() -> None:
    client = TestClient(_app(), raise_server_exceptions=False)
    assert client.get("/nope").json()["error"]["code"] == "NOT_FOUND"
    resp = client.get("/boom")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret internals" not in resp.text
