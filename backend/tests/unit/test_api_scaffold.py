"""Phase 1 contract: the API surface exists, health works, every other endpoint is an honest
501 stub in the standard error envelope (never a fake 200)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from subwise.main import API_PREFIX, create_app

EXPECTED_OPERATIONS = {
    ("post", "/auth/register"), ("post", "/auth/login"), ("post", "/auth/logout"),
    ("get", "/me"), ("get", "/me/profile"), ("put", "/me/profile"),
    ("get", "/me/requirements"), ("put", "/me/requirements"),
    ("get", "/me/memory"), ("delete", "/me/memory/{kind}/{key}"),
    ("get", "/subscriptions"), ("post", "/subscriptions"),
    ("patch", "/subscriptions/{subscription_id}"), ("delete", "/subscriptions/{subscription_id}"),
    ("get", "/catalog/providers"), ("get", "/catalog/plans"),
    ("post", "/threads"), ("get", "/threads/{thread_id}/messages"),
    ("post", "/runs"), ("get", "/runs"), ("get", "/runs/{run_id}"),
    ("get", "/runs/{run_id}/events"), ("post", "/runs/{run_id}/clarification"),
    ("post", "/runs/{run_id}/approval"), ("post", "/runs/{run_id}/cancel"),
    ("get", "/reports/{report_id}"),
    ("get", "/prices"), ("get", "/prices/{plan_id}/history"), ("post", "/prices/refresh"),
    ("get", "/dashboard"), ("get", "/health"),
}  # fmt: skip

# Minimal valid bodies so requests reach the stub instead of failing validation.
BODIES: dict[tuple[str, str], dict[str, Any]] = {
    ("post", "/auth/register"): {
        "email": "a@example.com", "password": "0123456789", "display_name": "A",
    },
    ("post", "/auth/login"): {"email": "a@example.com", "password": "0123456789"},
    ("put", "/me/profile"): {},
    ("put", "/me/requirements"): {"requirements": []},
    ("post", "/subscriptions"): {"custom_name": "X", "price_paise": 100, "billing_cycle": 1},
    ("patch", "/subscriptions/{subscription_id}"): {},
    ("post", "/threads"): {},
    ("post", "/runs"): {"thread_id": "thr_1", "message": "help"},
    ("post", "/runs/{run_id}/clarification"): {"answers": {"budget": "1000"}},
    ("post", "/runs/{run_id}/approval"): {"report_id": "rep_1", "decision": "approved"},
    ("post", "/prices/refresh"): {},
}  # fmt: skip


def _operations() -> set[tuple[str, str]]:
    paths = create_app().openapi()["paths"]
    ops = set()
    for path, item in paths.items():
        for method in item:
            ops.add((method, path.removeprefix(API_PREFIX)))
    return ops


def test_openapi_exposes_exactly_the_blueprint_surface() -> None:
    assert _operations() == EXPECTED_OPERATIONS


def test_health_ok_with_search_disabled_by_default(client: TestClient) -> None:
    resp = client.get(f"{API_PREFIX}/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["search"] == "disabled"


@pytest.mark.parametrize(("method", "path"), sorted(EXPECTED_OPERATIONS - {("get", "/health")}))
def test_every_stub_returns_501_envelope(client: TestClient, method: str, path: str) -> None:
    url = API_PREFIX + path.format(
        kind="rejections", key="k", subscription_id="sub_1", thread_id="thr_1",
        run_id="run_1", report_id="rep_1", plan_id="plan_1",
    )  # fmt: skip
    resp = client.request(method.upper(), url, json=BODIES.get((method, path)))
    assert resp.status_code == 501, resp.text
    error = resp.json()["error"]
    assert error["code"] == "NOT_IMPLEMENTED"
    assert error["details"]["module"].startswith("M")
