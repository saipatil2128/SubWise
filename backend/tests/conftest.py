"""Shared test fixtures. Everything here is TEST-ONLY: synthetic HTML pages are served through an
httpx MockTransport into an isolated temporary data directory; nothing touches data/."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, TypeVar

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from subwise.config import Settings
from subwise.container import Container, build_container
from subwise.errors import LLMUnavailable
from subwise.llm.gateway import ChatMessage, LLMHealth
from subwise.main import create_app
from subwise.research.fetch import Fetcher

FIXTURES = Path(__file__).parent / "fixtures" / "html"
T = TypeVar("T", bound=BaseModel)

ALLOW_ALL_ROBOTS = "User-agent: *\nAllow: /\n"


def fixture_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class SiteMap:
    """URL -> (status, body). Unknown URLs return 404. Mutable during a test."""

    def __init__(self) -> None:
        self.pages: dict[str, tuple[int, str]] = {}
        self.fail_hosts: set[str] = set()
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.calls.append(url)
        if request.url.host in self.fail_hosts:
            raise httpx.ConnectError("simulated network failure", request=request)
        if url.endswith("/robots.txt"):
            status, body = self.pages.get(url, (200, ALLOW_ALL_ROBOTS))
            return httpx.Response(status, text=body)
        status, body = self.pages.get(url, (404, "not found"))
        return httpx.Response(status, text=body, headers={"content-type": "text/html"})


class FakeLLM:
    """Scriptable LLM. By default it is 'down' (raises LLMUnavailable) so the deterministic
    fallbacks run. Set ``structured[SchemaName]`` / ``text`` to script answers."""

    model_name = "fake-llm"

    def __init__(self) -> None:
        self.down = True
        self.structured: dict[str, dict[str, Any]] = {}
        self.text: str | None = None
        self.calls: list[str] = []

    def call_structured(
        self, schema: type[T], messages: list[ChatMessage], *, timeout_s: float | None = None
    ) -> T:
        self.calls.append(schema.__name__)
        if self.down or schema.__name__ not in self.structured:
            raise LLMUnavailable("fake LLM is down")
        return schema.model_validate(self.structured[schema.__name__])

    def call_text(self, messages: list[ChatMessage], *, timeout_s: float | None = None) -> str:
        self.calls.append("text")
        if self.down or self.text is None:
            raise LLMUnavailable("fake LLM is down")
        return self.text

    def health(self) -> LLMHealth:
        return LLMHealth(
            reachable=not self.down, model=self.model_name, model_present=not self.down
        )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Isolated settings: temp data dir, no search key, never reads the developer's .env."""
    return Settings(
        _env_file=None,
        env="test",
        data_dir=tmp_path / "data",
        tavily_api_key=None,
        jwt_secret="test-secret-" + "x" * 32,
    )  # type: ignore[arg-type]


@pytest.fixture
def sites() -> SiteMap:
    return SiteMap()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


def make_fetcher(settings: Settings, sites: SiteMap) -> Fetcher:
    client = httpx.Client(transport=httpx.MockTransport(sites.handler), follow_redirects=True)
    return Fetcher(
        sources_dir=settings.sources_dir,
        client=client,
        resolver=lambda host: ["93.184.216.34"],
        retries=0,
    )


@pytest.fixture
def container(settings: Settings, sites: SiteMap, fake_llm: FakeLLM) -> Iterator[Container]:
    c = build_container(settings, llm=fake_llm, fetcher=make_fetcher(settings, sites))
    yield c
    c.close()


@pytest.fixture
def client(settings: Settings, container: Container) -> Iterator[TestClient]:
    app = create_app(settings, container=container)
    with TestClient(app, raise_server_exceptions=False, headers={"X-SubWise-CSRF": "1"}) as c:
        yield c


@pytest.fixture
def register(client: TestClient) -> Callable[[str], dict[str, Any]]:
    def _register(email: str = "asha@example.com") -> dict[str, Any]:
        r = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "correct-horse-battery", "display_name": "Asha"},
        )
        assert r.status_code == 201, r.text
        return r.json()  # type: ignore[no-any-return]

    return _register


def serve_standard_sites(sites: SiteMap) -> None:
    """Serve synthetic pages at the registry URLs for netflix, spotify and apple_music."""
    sites.pages["https://help.netflix.com/en/node/24926/in"] = (
        200,
        fixture_html("netflix_in.html"),
    )
    sites.pages["https://www.spotify.com/in-en/premium/"] = (200, fixture_html("spotify_in.html"))
    sites.pages["https://www.apple.com/in/apple-music/"] = (
        200,
        fixture_html("apple_music_in.html"),
    )
