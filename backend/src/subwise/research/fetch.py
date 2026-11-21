"""Polite fetcher for official pricing pages (blueprint G.2 step 3, J.3).

Rules: robots.txt honoured; honest User-Agent; 10 s connect / 20 s total timeout; one retry
with backoff on network errors and 5xx; 5 MB cap; only public http(s) hosts (SSRF guard);
no CAPTCHA, login or anti-bot bypass. JavaScript rendering uses Playwright only when the
optional extra is installed and ``SUBWISE_PLAYWRIGHT_ENABLED=true``.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import ipaddress
import logging
import socket
import time
import urllib.robotparser
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

from subwise import __version__
from subwise.errors import FetchFailed, SourceDisallowed

log = logging.getLogger(__name__)

USER_AGENT = (
    f"Mozilla/5.0 (compatible; SubWise/{__version__}; academic price comparison; "
    "+https://github.com/saipatil2128/SubWise)"
)
MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
ROBOTS_TTL_S = 7 * 24 * 3600

Resolver = Callable[[str], list[str]]


def default_resolver(host: str) -> list[str]:
    return list({str(info[4][0]) for info in socket.getaddrinfo(host, None)})


def assert_public_http_url(url: str, resolver: Resolver = default_resolver) -> None:
    """Reject non-http(s) schemes and hosts resolving to private/loopback/link-local IPs."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise SourceDisallowed(f"Only public http(s) URLs may be fetched: {url}")
    try:
        addresses = resolver(parts.hostname)
    except OSError as exc:
        raise FetchFailed(f"Could not resolve {parts.hostname}: {exc}") from exc
    for addr in addresses:
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise SourceDisallowed(f"{parts.hostname} resolves to a non-public address")


@dataclass(frozen=True, slots=True)
class FetchedPage:
    requested_url: str
    final_url: str
    http_status: int
    html: str
    sha256: str
    fetched_at: datetime
    method: str  # "httpx" | "playwright"
    path: Path | None


class _UndecodableBody(Exception):
    """The response body could not be decompressed."""


def _decode_body(raw: bytes, content_encoding: str) -> bytes:
    """Decode a raw HTTP body. Tolerates multi-member gzip and multi-frame zstd."""
    data = raw
    # Encodings are listed in the order they were applied; undo them in reverse.
    for enc in reversed([e.strip().lower() for e in content_encoding.split(",") if e.strip()]):
        try:
            if enc in ("gzip", "x-gzip"):
                data = gzip.decompress(data)
            elif enc == "deflate":
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    data = zlib.decompress(data, -zlib.MAX_WBITS)  # raw deflate
            elif enc == "zstd":
                import zstandard

                reader = zstandard.ZstdDecompressor().stream_reader(
                    io.BytesIO(data), read_across_frames=True
                )
                data = reader.read()
            elif enc in ("identity", ""):
                continue
            else:
                raise _UndecodableBody(f"unsupported content-encoding {enc!r}")
        except _UndecodableBody:
            raise
        except Exception as exc:  # zlib.error, OSError, zstandard.ZstdError, ImportError
            raise _UndecodableBody(f"{enc}: {exc}") from exc
    return data


class Fetcher:
    def __init__(
        self,
        *,
        sources_dir: Path | None,
        client: httpx.Client | None = None,
        resolver: Resolver = default_resolver,
        playwright_enabled: bool = False,
        retries: int = 1,
    ) -> None:
        self._sources_dir = sources_dir
        self._client = client or httpx.Client(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
                # Only encodings httpx decodes reliably. httpx also advertises zstd when the
                # `zstandard` package is installed (it is, via langsmith); multi-frame zstd
                # responses (e.g. help.netflix.com) then fail with "cannot use a decompressobj
                # multiple times".
                "Accept-Encoding": "gzip, deflate",
            },
        )
        self._resolver = resolver
        self._playwright_enabled = playwright_enabled
        self._retries = retries
        self._robots: dict[str, tuple[float, urllib.robotparser.RobotFileParser | None]] = {}

    @property
    def playwright_available(self) -> bool:
        return self._playwright_enabled and importlib.util.find_spec("playwright") is not None

    # ------------------------------------------------------------------ robots
    def robots_allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        base = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
        cached = self._robots.get(base)
        if cached is None or time.time() - cached[0] > ROBOTS_TTL_S:
            parser: urllib.robotparser.RobotFileParser | None = urllib.robotparser.RobotFileParser()
            try:
                resp = self._get(base + "/robots.txt")
                if resp.status_code >= 500:
                    raise FetchFailed(f"robots.txt returned {resp.status_code}")
                if resp.status_code >= 400:
                    parser = None  # no robots.txt => allowed (RFC 9309)
                else:
                    assert parser is not None
                    parser.parse(resp.text.splitlines())
            except httpx.HTTPError as exc:
                raise FetchFailed(f"Could not read robots.txt for {base}: {exc}") from exc
            cached = (time.time(), parser)
            self._robots[base] = cached
        parser = cached[1]
        return True if parser is None else parser.can_fetch(USER_AGENT, url)

    # ------------------------------------------------------------------ fetching
    def _get(self, url: str) -> httpx.Response:
        try:
            return self._get_once(url, accept_encoding=None)
        except _UndecodableBody:
            # Some servers send encodings or framings that fail to decode. Ask for the page
            # uncompressed instead of failing the provider.
            return self._get_once(url, accept_encoding="identity")

    def _get_once(self, url: str, *, accept_encoding: str | None) -> httpx.Response:
        assert_public_http_url(url, self._resolver)
        headers = {"Accept-Encoding": accept_encoding} if accept_encoding else None
        last: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                with self._client.stream("GET", url, headers=headers) as resp:
                    try:
                        chunks: list[bytes] = []
                        size = 0
                        for chunk in resp.iter_raw():
                            size += len(chunk)
                            if size > MAX_BYTES:
                                raise FetchFailed(f"{url} is larger than {MAX_BYTES} bytes")
                            chunks.append(chunk)
                        body = _decode_body(
                            b"".join(chunks), resp.headers.get("content-encoding", "")
                        )
                    except httpx.StreamConsumed:
                        # In-memory responses (e.g. from a transport that built the response
                        # from bytes) were already read and decoded by httpx.
                        body = resp.content
                    if len(body) > MAX_BYTES:
                        raise FetchFailed(f"{url} is larger than {MAX_BYTES} bytes when decoded")
                    # The body is decoded now; drop the encoding headers so the rebuilt
                    # response is not decoded a second time.
                    out_headers = [
                        (k, v)
                        for k, v in resp.headers.multi_items()
                        if k.lower()
                        not in ("content-encoding", "content-length", "transfer-encoding")
                    ]
                    out = httpx.Response(
                        resp.status_code, headers=out_headers, content=body, request=resp.request
                    )
                    if resp.history:
                        out.history = list(resp.history)
                    if resp.status_code >= 500 and attempt < self._retries:
                        last = FetchFailed(f"HTTP {resp.status_code}")
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    return out
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = exc
                if attempt < self._retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
            except httpx.DecodingError as exc:
                raise _UndecodableBody(str(exc)) from exc
        raise FetchFailed(f"Network error fetching {url}: {last}")

    def fetch(self, url: str, *, needs_js: bool = False) -> FetchedPage:
        if not self.robots_allowed(url):
            raise SourceDisallowed(f"robots.txt disallows automated access to {url}")
        if needs_js and self.playwright_available:
            return self._fetch_playwright(url)
        resp = self._get(url)
        if resp.status_code >= 400:
            raise FetchFailed(
                f"{url} returned HTTP {resp.status_code}", details={"http_status": resp.status_code}
            )
        final_url = str(resp.url) if resp.url else url
        assert_public_http_url(final_url, self._resolver)
        return self._store(url, final_url, resp.status_code, resp.text, "httpx")

    def _fetch_playwright(self, url: str) -> FetchedPage:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    page = browser.new_page(user_agent=USER_AGENT, locale="en-IN")
                    resp = page.goto(url, wait_until="networkidle", timeout=30_000)
                    status = resp.status if resp else 0
                    html = page.content()
                    final_url = page.url
                finally:
                    browser.close()
        except PlaywrightError as exc:
            raise FetchFailed(f"Browser rendering failed for {url}: {exc}") from exc
        if status >= 400:
            raise FetchFailed(f"{url} returned HTTP {status}", details={"http_status": status})
        assert_public_http_url(final_url, self._resolver)
        return self._store(url, final_url, status, html, "playwright")

    def _store(self, url: str, final_url: str, status: int, html: str, method: str) -> FetchedPage:
        sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
        path = None
        if self._sources_dir is not None:
            self._sources_dir.mkdir(parents=True, exist_ok=True)
            path = self._sources_dir / f"{sha}.html"
            if not path.exists():
                path.write_text(html, encoding="utf-8")
        return FetchedPage(url, final_url, status, html, sha, datetime.now(UTC), method, path)

    def close(self) -> None:
        self._client.close()
