"""Regression: real sites send gzip/deflate/brotli. The fetcher must decode exactly once."""

from __future__ import annotations

import gzip
import zlib

import httpx
import pytest

from subwise.research.fetch import Fetcher

PAGE = "<html><body><h2>Premium</h2><p>₹649/month</p></body></html>"


def _resolver(host: str) -> list[str]:
    return ["93.184.216.34"]  # public address; no DNS in tests


@pytest.mark.parametrize(
    ("encoding", "encode"),
    [
        ("gzip", gzip.compress),
        ("deflate", zlib.compress),
    ],
)
def test_compressed_pages_and_robots_are_decoded_once(encoding: str, encode) -> None:  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        body = "User-agent: *\nAllow: /\n" if request.url.path == "/robots.txt" else PAGE
        return httpx.Response(
            200,
            headers={"Content-Encoding": encoding, "Content-Type": "text/html; charset=utf-8"},
            content=encode(body.encode("utf-8")),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    fetcher = Fetcher(sources_dir=None, client=client, resolver=_resolver, retries=0)
    page = fetcher.fetch("https://www.example.com/premium")
    assert page.html == PAGE
    assert page.final_url == "https://www.example.com/premium"


def test_final_url_after_redirect_is_kept() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/old":
            return httpx.Response(301, headers={"Location": "https://www.example.com/in/new"})
        return httpx.Response(
            200, headers={"Content-Encoding": "gzip"}, content=gzip.compress(PAGE.encode())
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    fetcher = Fetcher(sources_dir=None, client=client, resolver=_resolver, retries=0)
    page = fetcher.fetch("https://www.example.com/old")
    assert page.final_url == "https://www.example.com/in/new"
    assert "₹649" in page.html


def test_only_gzip_and_deflate_are_requested() -> None:
    # httpx would add zstd when `zstandard` is installed; multi-frame zstd breaks its decoder.
    fetcher = Fetcher(sources_dir=None, resolver=_resolver, retries=0)
    assert fetcher._client.headers["accept-encoding"] == "gzip, deflate"
    fetcher.close()


def test_zstd_frame_ending_on_a_chunk_boundary_is_decoded() -> None:
    """help.netflix.com: httpx's streaming zstd decoder fails with 'cannot use a decompressobj
    multiple times' when a frame ends exactly at a chunk boundary. The fetcher decodes itself."""
    zstandard = pytest.importorskip("zstandard")
    c = zstandard.ZstdCompressor()
    frames = [c.compress(b"User-agent: *\nAllow: /\n")]
    page_frames = [c.compress(PAGE[:20].encode()), c.compress(PAGE[20:].encode())]

    class Chunks(httpx.SyncByteStream):
        def __init__(self, parts: list[bytes]) -> None:
            self.parts = parts

        def __iter__(self):  # type: ignore[no-untyped-def]
            yield from self.parts

    def handler(request: httpx.Request) -> httpx.Response:
        parts = frames if request.url.path == "/robots.txt" else page_frames
        return httpx.Response(200, headers={"Content-Encoding": "zstd"}, stream=Chunks(parts))

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    fetcher = Fetcher(sources_dir=None, client=client, resolver=_resolver, retries=0)
    assert fetcher.fetch("https://help.example.com/node/1").html == PAGE


def test_undecodable_body_is_refetched_uncompressed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("accept-encoding") == "identity":
            text = "User-agent: *\nAllow: /\n" if request.url.path == "/robots.txt" else PAGE
            return httpx.Response(200, text=text)
        return httpx.Response(
            200, headers={"Content-Encoding": "gzip"}, stream=httpx.ByteStream(b"not gzip at all")
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    fetcher = Fetcher(sources_dir=None, client=client, resolver=_resolver, retries=0)
    assert fetcher.fetch("https://www.example.com/premium").html == PAGE
