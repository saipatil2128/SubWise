"""Auth, profile, requirements, subscriptions CRUD and per-user isolation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

API = "/api/v1"


def test_register_login_logout_and_me(
    client: TestClient, register: Callable[[str], dict[str, Any]]
) -> None:
    user = register("asha@example.com")
    assert user["id"].startswith("usr_")
    me = client.get(f"{API}/me").json()
    assert me["user"]["email"] == "asha@example.com"
    assert me["profile"]["currency"] == "INR" and me["profile"]["country"] == "IN"
    assert client.post(f"{API}/auth/logout").status_code == 204
    assert client.get(f"{API}/me").status_code == 401
    r = client.post(
        f"{API}/auth/login", json={"email": "asha@example.com", "password": "correct-horse-battery"}
    )
    assert r.status_code == 200
    bad = client.post(f"{API}/auth/login", json={"email": "asha@example.com", "password": "x" * 12})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "UNAUTHENTICATED"


def test_duplicate_email_and_weak_password(
    client: TestClient, register: Callable[[str], dict[str, Any]]
) -> None:
    register("a@example.com")
    r = client.post(
        f"{API}/auth/register",
        json={"email": "a@example.com", "password": "0123456789", "display_name": "A"},
    )
    assert r.status_code == 409
    r = client.post(
        f"{API}/auth/register",
        json={"email": "b@example.com", "password": "short", "display_name": "B"},
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_FAILED"


def test_csrf_header_required_for_unsafe_methods(
    client: TestClient, register: Callable[[str], dict[str, Any]]
) -> None:
    register()
    r = client.put(f"{API}/me/profile", json={}, headers={"X-SubWise-CSRF": ""})
    assert r.status_code == 403


def test_profile_budget_and_requirements(
    client: TestClient, register: Callable[[str], dict[str, Any]]
) -> None:
    register()
    r = client.put(
        f"{API}/me/profile",
        json={
            "budget_paise": 1200000,
            "budget_period": "annual",
            "ads_tolerance": "avoid",
            "eligibility": ["student"],
        },
    )
    assert r.status_code == 200
    assert r.json()["monthly_budget"]["display"] == "₹1,000.00"
    r = client.put(
        f"{API}/me/requirements",
        json={
            "requirements": [
                {"feature_code": "movies", "level": "must", "weight": 1},
                {"feature_code": "uhd_4k", "level": "nice", "weight": 0.4},
            ]
        },
    )
    assert r.status_code == 200 and len(r.json()["requirements"]) == 2
    bad = client.put(
        f"{API}/me/requirements",
        json={"requirements": [{"feature_code": "teleportation", "level": "must", "weight": 1}]},
    )
    assert bad.status_code == 422
    feats = client.get(f"{API}/features").json()
    assert {"movies", "music_streaming", "uhd_4k"} <= {f["code"] for f in feats}


def test_subscription_crud(client: TestClient, register: Callable[[str], dict[str, Any]]) -> None:
    register()
    r = client.post(
        f"{API}/subscriptions",
        json={
            "provider_id": "netflix",
            "price_paise": 49900,
            "billing_cycle": 1,
            "usage_frequency": "daily",
            "renewal_date": "2026-12-01",
        },
    )
    assert r.status_code == 201, r.text
    sub = r.json()
    assert sub["display_name"] == "Netflix" and sub["monthly_equivalent"]["display"] == "₹499.00"
    assert sub["annual_cost"]["display"] == "₹5,988.00"
    r = client.post(
        f"{API}/subscriptions",
        json={"custom_name": "Local cable", "price_paise": 59900, "billing_cycle": 3},
    )
    assert r.json()["monthly_equivalent"]["display"] == "₹199.67"
    upd = client.patch(f"{API}/subscriptions/{sub['id']}", json={"usage_frequency": "never"})
    assert upd.json()["usage_frequency"] == "never"
    assert len(client.get(f"{API}/subscriptions").json()) == 2
    assert client.delete(f"{API}/subscriptions/{sub['id']}").status_code == 204
    assert len(client.get(f"{API}/subscriptions").json()) == 1
    bad = client.post(
        f"{API}/subscriptions", json={"provider_id": "nope", "price_paise": 1, "billing_cycle": 1}
    )
    assert bad.status_code == 422
    both = client.post(
        f"{API}/subscriptions",
        json={"provider_id": "netflix", "custom_name": "x", "price_paise": 1, "billing_cycle": 1},
    )
    assert both.status_code == 422


def test_users_cannot_see_or_change_each_others_data(
    client: TestClient, register: Callable[[str], dict[str, Any]]
) -> None:
    register("one@example.com")
    sub = client.post(
        f"{API}/subscriptions", json={"custom_name": "Mine", "price_paise": 100, "billing_cycle": 1}
    ).json()
    client.post(f"{API}/auth/logout")
    register("two@example.com")
    assert client.get(f"{API}/subscriptions").json() == []
    assert (
        client.patch(f"{API}/subscriptions/{sub['id']}", json={"price_paise": 1}).status_code == 404
    )
    assert client.delete(f"{API}/subscriptions/{sub['id']}").status_code == 404
    assert client.get(f"{API}/runs/run_does_not_exist").status_code == 404
    assert client.get(f"{API}/reports/rep_x").status_code == 404


def test_health_reports_components(client: TestClient) -> None:
    body = client.get(f"{API}/health").json()
    assert body["database"] == "ok"
    assert body["search"] == "disabled" and body["playwright"] == "disabled"
    assert body["llm"]["reachable"] is False and body["status"] == "degraded"


def test_unknown_api_route_is_json_404(client: TestClient) -> None:
    r = client.get(f"{API}/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    assert r.headers["X-Request-ID"]
