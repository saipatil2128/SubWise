"""Browser end-to-end test: the BUILT frontend (frontend/dist) served by the real FastAPI app over
real HTTP, driven by a real Chromium through Playwright. Provider pages are the synthetic test
fixtures served through the test-only mock transport and the LLM is the scripted fake (down), so
this exercises the full UI -> API -> worker -> LangGraph -> SSE path deterministically.

Run:  pytest -m e2e   (needs: npm run build; pip install playwright; python -m playwright install chromium)
Set SUBWISE_E2E_CHROME to a Chrome/Chromium executable to use one that is already installed.
"""

from __future__ import annotations

import os
import re
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn

from subwise.config import Settings
from subwise.container import build_container
from subwise.main import FRONTEND_DIST, create_app
from tests.conftest import FakeLLM, SiteMap, make_fetcher, serve_standard_sites

pytestmark = pytest.mark.e2e

playwright_sync = pytest.importorskip("playwright.sync_api", reason="pip install playwright")
if not (FRONTEND_DIST / "index.html").exists():
    pytest.skip("frontend/dist missing: run `npm run build` in frontend/", allow_module_level=True)

expect = playwright_sync.expect


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def server(tmp_path: Path) -> Iterator[str]:
    settings = Settings(
        _env_file=None,
        env="test",
        data_dir=tmp_path / "data",
        tavily_api_key=None,
        jwt_secret="e2e-secret-" + "x" * 32,
    )  # type: ignore[arg-type]
    sites = SiteMap()
    serve_standard_sites(sites)
    container = build_container(settings, llm=FakeLLM(), fetcher=make_fetcher(settings, sites))
    app = create_app(settings, container=container)
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    assert srv.started, "uvicorn did not start"
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    thread.join(timeout=10)
    container.close()


@pytest.fixture
def page(server: str) -> Iterator[playwright_sync.Page]:
    with playwright_sync.sync_playwright() as p:
        exe = os.environ.get("SUBWISE_E2E_CHROME")
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        ctx = browser.new_context(base_url=server, viewport={"width": 1366, "height": 900})
        pg = ctx.new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.set_default_timeout(20_000)
        yield pg
        browser.close()
        assert not errors, f"JavaScript errors in the page: {errors}"


def _shot(page: playwright_sync.Page, name: str) -> None:
    """Save a full-page screenshot when SUBWISE_E2E_SCREENSHOTS names a folder."""
    folder = os.environ.get("SUBWISE_E2E_SCREENSHOTS")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(folder) / f"{name}.png"), full_page=True)


def test_full_user_journey_in_browser(page: playwright_sync.Page) -> None:
    # Landing -> register
    page.goto("/")
    expect(page.get_by_role("heading", level=1)).to_contain_text("Stop paying twice")
    _shot(page, "01-landing")
    page.get_by_role("link", name="Create account").first.click()
    page.get_by_label("Name").fill("Asha")
    page.get_by_label("Email").fill("asha@example.com")
    page.get_by_label("Password", exact=True).fill("correct-horse-battery")
    page.get_by_label("Confirm password").fill("correct-horse-battery")
    page.get_by_role("button", name="Create account").click()
    expect(page).to_have_url(re.compile(r"/app/subscriptions$"))

    # Fetch prices (three synthetic provider pages succeed, the other three fail honestly)
    page.get_by_role("link", name="Plans & prices").click()
    page.get_by_role("button", name="Refresh all prices").click()
    expect(page.get_by_text(re.compile(r"Refreshed 6 providers: 3 succeeded"))).to_be_visible(
        timeout=60_000
    )
    expect(page.get_by_text("Live · verified").first).to_be_visible()
    expect(page.get_by_text("failed").first).to_be_visible()
    _shot(page, "02-plans")

    # Evidence modal for a plan
    page.get_by_role("button", name="Evidence & history").first.click()
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_text("Evidence", exact=True)).to_be_visible()
    dialog.get_by_role("button", name="Close").click()

    # Add three subscriptions with the user's own prices
    page.get_by_role("link", name="Subscriptions").click()
    for provider, price, usage in (
        ("Netflix", "333", "daily"),
        ("Spotify", "123", "weekly"),
        ("Apple Music", "131", "never"),
    ):
        page.get_by_role(
            "button", name=re.compile("^Add (your first )?subscription$")
        ).first.click()
        d = page.get_by_role("dialog")
        d.get_by_label("Service").select_option(label=provider)
        d.get_by_label("Plan name").fill("My plan")
        d.get_by_label("Price you pay (₹)").fill(price)
        d.get_by_label("How often you use it").select_option(usage)
        d.get_by_role("button", name="Add subscription").click()
        expect(page.get_by_role("dialog")).to_have_count(0)
    expect(page.get_by_role("row")).to_have_count(4)  # header + 3
    _shot(page, "05-subscriptions")

    # Budget preference
    page.get_by_role("link", name="Preferences").click()
    page.get_by_label("Budget (₹)").fill("500")
    page.get_by_role("button", name="Save preferences").click()
    expect(page.get_by_text("Saved").first).to_be_visible()

    # Dashboard shows real spend
    page.get_by_role("link", name="Dashboard").click()
    expect(page.get_by_text("₹587.00").first).to_be_visible()
    page.wait_for_timeout(600)
    _shot(page, "03-dashboard")

    # Optimize with live timeline, then approve
    page.get_by_role("link", name="Optimizer").click()
    page.get_by_label("What would you like?").fill(
        "I watch movies and listen to music. Reduce my spending."
    )
    page.get_by_role("button", name="Start optimization").click()
    expect(page).to_have_url(re.compile(r"/app/runs/run_"))
    expect(page.get_by_text("Your decision")).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Fetching prices from providers").first).to_be_visible()
    expect(page.get_by_text("Optimizing (OAVOE)").first).to_be_visible()
    expect(page.get_by_text("Data limitations", exact=True)).to_be_visible()
    expect(page.get_by_text("Recommended plans")).to_be_visible()
    verified_row = page.get_by_role("row").filter(has_text="Live · verified").first
    verified_row.get_by_role("button", name="Show").click()
    expect(page.get_by_text("Text on the page:").first).to_be_visible()
    _shot(page, "04-run-approval")
    page.get_by_role("button", name="Approve").click()
    expect(page.get_by_text("You approved this recommendation.")).to_be_visible(timeout=30_000)

    # History lists the run with its report
    page.get_by_role("link", name="History").click()
    expect(page.get_by_text("completed").first).to_be_visible()
    page.get_by_role("link", name="Report").first.click()
    expect(page.get_by_role("heading", name="Recommendation report")).to_be_visible()

    # Sign out returns to the login page; the app is protected again
    page.get_by_role("button", name="Sign out").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    page.goto("/app")
    expect(page).to_have_url(re.compile(r"/login$"))
