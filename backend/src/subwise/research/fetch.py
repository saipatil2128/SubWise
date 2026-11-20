"""Polite fetcher (blueprint G.2 step 3). Implementation: M8.

Rules: httpx, 10 s connect / 20 s total, one retry with backoff, honest User-Agent, max 4
concurrent and 1 per domain, 5 MB cap, robots.txt honoured, SSRF guard, never bypass CAPTCHAs.
"""

from __future__ import annotations

from dataclasses import dataclass

from subwise import __version__
from subwise.domain.evidence import SourceDocument
from subwise.errors import NotImplementedYet

USER_AGENT = f"SubWise/{__version__} (academic project; +https://github.com/saipatil2128/SubWise)"
MAX_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class FetchResult:
    document: SourceDocument
    text: str
    html: str


class Fetcher:
    def fetch(self, url: str, *, provider_id: str) -> FetchResult:
        """Fetch, normalise to text, store under data/sources/<sha>.txt (M8)."""
        raise NotImplementedYet("M8", "Fetcher.fetch")


def robots_allowed(url: str, user_agent: str = USER_AGENT) -> bool:
    """Check robots.txt with urllib.robotparser; cached per domain for 7 days (M8)."""
    raise NotImplementedYet("M8", "robots_allowed")


def assert_public_http_url(url: str) -> None:
    """Reject non-http(s) schemes and private/loopback/link-local IPs (SSRF guard) (M8)."""
    raise NotImplementedYet("M8", "assert_public_http_url")
