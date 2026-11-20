"""Live retrieval honesty (brief §1): verified-live, cached, unavailable, disallowed, JS pages.
Pages are synthetic fixtures served by a mock transport."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.conftest import SiteMap, fixture_html, serve_standard_sites

from subwise.container import Container
from subwise.db.models import PriceObservation, SourceDocument
from subwise.db.session import session_scope

API = "/api/v1"


def labels(container: Container, provider: str) -> dict[str, str]:
    return {
        p.plan_name: p.label for p in container.prices.plan_prices() if p.provider_id == provider
    }


def test_live_retrieval_stores_evidence_and_labels_live(
    container: Container, sites: SiteMap
) -> None:
    serve_standard_sites(sites)
    [r] = container.prices.refresh(["netflix"])
    assert r.outcome == "success" and r.verified == 4
    assert set(labels(container, "netflix").values()) == {"live_verified"}
    with session_scope(container.session_factory) as s:
        obs = s.query(PriceObservation).all()
        doc = s.query(SourceDocument).one()
        assert doc.final_url == "https://help.netflix.com/en/node/24926/in"
        assert all(
            o.source_document_id == doc.id and o.binding["region"]["method"] == "url_locale"
            for o in obs
        )
        assert any("₹111/month" in o.evidence_snippet for o in obs)


def test_failed_refresh_turns_previous_prices_into_cached_never_live(
    container: Container, sites: SiteMap
) -> None:
    """Brief case 7 (scraping fails) and the 'never silently reuse old prices' rule."""
    serve_standard_sites(sites)
    container.prices.refresh(["netflix"])
    sites.fail_hosts.add("help.netflix.com")
    [r] = container.prices.refresh(["netflix"])
    assert r.outcome == "failed" and "simulated network failure" in (r.error or "")
    assert set(labels(container, "netflix").values()) == {"cached_verified"}


def test_unavailable_provider_has_no_prices_at_all(container: Container, sites: SiteMap) -> None:
    sites.fail_hosts.add("www.apple.com")
    [r] = container.prices.refresh(["apple_music"])
    assert r.outcome == "failed" and r.prices_found == 0
    assert labels(container, "apple_music") == {}


def test_robots_disallow_is_respected(container: Container, sites: SiteMap) -> None:
    serve_standard_sites(sites)
    sites.pages["https://www.spotify.com/robots.txt"] = (200, "User-agent: *\nDisallow: /")
    [r] = container.prices.refresh(["spotify"])
    assert r.outcome == "disallowed"
    assert "https://www.spotify.com/in-en/premium/" not in sites.calls


def test_js_page_without_browser_is_reported_as_needs_js(
    container: Container, sites: SiteMap
) -> None:
    sites.pages["https://www.jiohotstar.com/subscribe"] = (
        200,
        "<html><body><div id=root></div></body></html>",
    )
    [r] = container.prices.refresh(["jiohotstar"])
    assert r.outcome == "needs_js" and "Playwright" in (r.error or "")


def test_wrong_region_page_yields_only_unverified(container: Container, sites: SiteMap) -> None:
    sites.pages["https://help.netflix.com/en/node/24926/in"] = (
        200,
        fixture_html("foreign_currency.html"),
    )
    [r] = container.prices.refresh(["netflix"])
    assert r.verified == 0 and r.outcome == "no_prices"
    assert set(labels(container, "netflix").values()) <= {"unverified"}


def test_prices_api_exposes_labels_evidence_and_attempts(
    client: TestClient, register, sites: SiteMap
) -> None:  # type: ignore[no-untyped-def]
    register()
    serve_standard_sites(sites)
    sites.fail_hosts.add("www.apple.com")
    res = client.post(f"{API}/prices/refresh", json={"provider_ids": ["netflix", "apple_music"]})
    assert {r["provider_id"]: r["outcome"] for r in res.json()} == {
        "netflix": "success",
        "apple_music": "failed",
    }
    plans = client.get(f"{API}/catalog/plans").json()
    assert plans and all(p["label"] == "live_verified" and p["source_url"] for p in plans)
    hist = client.get(f"{API}/prices/{plans[0]['plan_id']}/history").json()
    assert hist and hist[0]["evidence"]
    provs = {p["id"]: p for p in client.get(f"{API}/catalog/providers").json()}
    assert provs["apple_music"]["latest_attempt"]["outcome"] == "failed"
    assert provs["zee5"]["latest_attempt"] is None
