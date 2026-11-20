"""LangGraph workflow end to end through the API (brief cases 11-15, blueprint D).
Sources are synthetic fixtures; the LLM is a scripted fake (down unless scripted)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from tests.conftest import FakeLLM, SiteMap, make_fetcher, serve_standard_sites

from subwise.config import Settings
from subwise.container import Container, build_container
from subwise.main import create_app

API = "/api/v1"


def setup_user(
    client: TestClient, register: Callable[[str], dict[str, Any]], budget: int | None = 50000
) -> None:
    register("ravi@example.com")
    if budget is not None:
        client.put(f"{API}/me/profile", json={"budget_paise": budget})
    for body in (
        {
            "provider_id": "netflix",
            "price_paise": 33300,
            "billing_cycle": 1,
            "usage_frequency": "daily",
        },
        {
            "provider_id": "spotify",
            "price_paise": 12300,
            "billing_cycle": 1,
            "usage_frequency": "weekly",
        },
        {
            "provider_id": "apple_music",
            "price_paise": 13100,
            "billing_cycle": 1,
            "usage_frequency": "never",
        },
    ):
        assert client.post(f"{API}/subscriptions", json=body).status_code == 201


def start(
    client: TestClient, container: Container, message: str, mode: str = "auto"
) -> dict[str, Any]:
    r = client.post(f"{API}/runs", json={"message": message, "mode": mode})
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    container.worker.wait(run_id, timeout=60)
    return client.get(f"{API}/runs/{run_id}").json()  # type: ignore[no-any-return]


def finish(client: TestClient, container: Container, run_id: str) -> dict[str, Any]:
    container.worker.wait(run_id, timeout=60)
    return client.get(f"{API}/runs/{run_id}").json()  # type: ignore[no-any-return]


def test_full_journey_with_overlap_savings_evidence_and_approval(
    client: TestClient,
    container: Container,
    sites: SiteMap,
    register: Callable[[str], dict[str, Any]],
) -> None:
    """Brief case 15 + §8 scenario: subscriptions, budget, usage -> research -> validate ->
    optimize -> explain -> approve -> saved report, with honest failures for other providers."""
    serve_standard_sites(sites)
    setup_user(client, register)
    run = start(client, container, "I watch movies and listen to music. Reduce my spending.")
    assert run["status"] == "waiting_approval", run
    events = client.get(f"{API}/runs/{run['run_id']}/events/list").json()
    msgs = " | ".join(e["message"] for e in events)
    assert "Netflix: 4 verified price(s) from the live page" in msgs
    assert "Amazon Prime: live retrieval failed" in msgs  # honest failure, nothing invented
    assert "Detected overlap in current subscriptions" in msgs  # Spotify + Apple Music
    report = client.get(f"{API}/reports/{run['latest_report_id']}").json()
    facts = report["facts"]
    assert facts["status"] == "optimal" and facts["within_budget"] is True
    assert report["current_monthly"]["display"] == "₹587.00"
    rec = report["recommended_monthly"]["paise"]
    assert rec < 58700 and facts["monthly_saving_paise"] == 58700 - rec
    assert any("Apple Music" in d for d in facts["drop"])  # never-used duplicate music service
    assert report["evidence"] and all(e["source_url"] for e in report["evidence"])
    assert "Data limitations" in report["markdown"] and report["generated_by"] == "template"
    ok = client.post(
        f"{API}/runs/{run['run_id']}/approval",
        json={"report_id": report["id"], "decision": "approved", "remember": ["movies"]},
    )
    assert ok.status_code == 202
    done = finish(client, container, run["run_id"])
    assert done["status"] == "completed" and done["latest_report_status"] == "approved"
    memory = client.get(f"{API}/me/memory").json()
    assert [m["key"] for m in memory] == ["movies"]
    dash = client.get(f"{API}/dashboard").json()
    assert dash["latest_report"]["status"] == "approved" and dash["active_subscriptions"] == 3


def test_clarification_when_budget_missing(
    client: TestClient,
    container: Container,
    sites: SiteMap,
    register: Callable[[str], dict[str, Any]],
) -> None:
    serve_standard_sites(sites)
    setup_user(client, register, budget=None)
    run = start(client, container, "Help me with my music and movies subscriptions.")
    assert run["status"] == "waiting_clarification"
    assert run["pending_interrupt"]["questions"][0]["field"] == "budget"
    r = client.post(
        f"{API}/runs/{run['run_id']}/clarification", json={"answers": {"budget": "400"}}
    )
    assert r.status_code == 202
    done = finish(client, container, run["run_id"])
    assert done["status"] == "waiting_approval"
    report = client.get(f"{API}/reports/{done['latest_report_id']}").json()
    assert report["facts"]["budget_display"] == "₹400.00"


def test_rejection_is_remembered_and_triggers_a_revision(
    client: TestClient,
    container: Container,
    sites: SiteMap,
    register: Callable[[str], dict[str, Any]],
) -> None:
    """Brief case 13."""
    serve_standard_sites(sites)
    setup_user(client, register)
    run = start(client, container, "Cut my costs, I watch movies and listen to music.")
    first = client.get(f"{API}/reports/{run['latest_report_id']}").json()
    added = [p["plan_id"] for p in first["facts"]["recommended"] if not p["is_current"]]
    client.post(
        f"{API}/runs/{run['run_id']}/approval",
        json={"report_id": first["id"], "decision": "rejected", "reason": "I must keep Spotify"},
    )
    again = finish(client, container, run["run_id"])
    assert again["status"] == "waiting_approval" and again["latest_report_id"] != first["id"]
    second = client.get(f"{API}/reports/{again['latest_report_id']}").json()
    assert second["version"] == 2
    assert not ({p["plan_id"] for p in second["facts"]["recommended"]} & set(added))
    assert any(p["name"].startswith("Spotify") for p in second["facts"]["recommended"])
    stale = client.post(
        f"{API}/runs/{run['run_id']}/approval",
        json={"report_id": first["id"], "decision": "approved"},
    )
    assert stale.status_code == 409
    kinds = {m["kind"] for m in client.get(f"{API}/me/memory").json()}
    assert "rejections" in kinds


def test_infeasible_budget_is_reported_not_manufactured(
    client: TestClient,
    container: Container,
    sites: SiteMap,
    register: Callable[[str], dict[str, Any]],
) -> None:
    serve_standard_sites(sites)
    register("tight@example.com")
    client.put(
        f"{API}/me/requirements",
        json={
            "requirements": [
                {"feature_code": "uhd_4k", "level": "must", "weight": 1},
                {"feature_code": "lossless_audio", "level": "must", "weight": 1},
            ]
        },
    )
    run = start(client, container, "Movies and music please, my budget is ₹100.")
    report = client.get(f"{API}/reports/{run['latest_report_id']}").json()
    assert report["facts"]["status"] == "infeasible" and report["recommended_monthly"] is None
    assert report["facts"]["diagnosis_amounts"]["shortfall"].startswith("₹")
    assert "No recommendation" in report["markdown"]


def test_llm_path_with_number_check_guard(
    client: TestClient,
    container: Container,
    sites: SiteMap,
    fake_llm: FakeLLM,
    register: Callable[[str], dict[str, Any]],
) -> None:
    """LLM parses intent and decides; its explanation invents a figure -> template replaces it."""
    serve_standard_sites(sites)
    setup_user(client, register)
    fake_llm.down = False
    fake_llm.structured["IntentLLM"] = {
        "categories": ["video", "music"],
        "budget_rupees": 9999,
        "must_have": ["movies", "music_streaming"],
        "mode": "savings",
    }
    fake_llm.structured["DecideLLM"] = {"action": "proceed_with_gaps", "reason": "enough data"}
    fake_llm.text = "Great news: you will save ₹12,345.00 every month!"
    run = start(client, container, "Movies and music, reduce my bill.")
    report = client.get(f"{API}/reports/{run['latest_report_id']}").json()
    assert report["generated_by"] == "template" and "12,345" not in report["markdown"]
    assert report["facts"]["budget_display"] == "₹500.00"  # 9999 was never typed: ignored
    events = client.get(f"{API}/runs/{run['run_id']}/events/list").json()
    assert any(e["payload"].get("decided_by") == "llm" for e in events if e["node"] == "decide")
    assert any("not in the verified facts" in str(e["payload"]) for e in events)


def test_paused_run_survives_restart_and_completes(
    settings: Settings, sites: SiteMap, fake_llm: FakeLLM
) -> None:
    """Brief case 12: checkpoint + resume across a backend restart (new container, same data)."""
    serve_standard_sites(sites)
    c1 = build_container(settings, llm=fake_llm, fetcher=make_fetcher(settings, sites))
    with TestClient(create_app(settings, container=c1), headers={"X-SubWise-CSRF": "1"}) as cl:
        cl.post(
            f"{API}/auth/register",
            json={"email": "r@example.com", "password": "0123456789ab", "display_name": "R"},
        )
        cl.put(f"{API}/me/profile", json={"budget_paise": 50000})
        run_id = cl.post(f"{API}/runs", json={"message": "movies and music"}).json()["run_id"]
        c1.worker.wait(run_id, timeout=60)
        run = cl.get(f"{API}/runs/{run_id}").json()
        assert run["status"] == "waiting_approval"
        cookies = dict(cl.cookies)
    c1.close()
    c2 = build_container(settings, llm=fake_llm, fetcher=make_fetcher(settings, sites))
    with TestClient(
        create_app(settings, container=c2), headers={"X-SubWise-CSRF": "1"}, cookies=cookies
    ) as cl:
        assert cl.get(f"{API}/runs/{run_id}").json()["status"] == "waiting_approval"
        r = cl.post(
            f"{API}/runs/{run_id}/approval",
            json={"report_id": run["latest_report_id"], "decision": "approved"},
        )
        assert r.status_code == 202
        c2.worker.wait(run_id, timeout=60)
        assert cl.get(f"{API}/runs/{run_id}").json()["status"] == "completed"
        assert len(cl.get(f"{API}/runs").json()) == 1
    c2.close()


def test_one_active_run_per_user_and_sse_stream(
    client: TestClient,
    container: Container,
    sites: SiteMap,
    register: Callable[[str], dict[str, Any]],
) -> None:
    serve_standard_sites(sites)
    setup_user(client, register)
    run = start(client, container, "movies and music")
    with client.stream("GET", f"{API}/runs/{run['run_id']}/events") as resp:
        body = "".join(resp.iter_text())
    assert "event: run_event" in body and "event: run_status" in body
    assert '"status": "waiting_approval"' in body
    msgs = client.get(f"{API}/threads/{run['thread_id']}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
