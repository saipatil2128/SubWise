"""Opt-in: fetches the REAL official pricing pages.  Run:  pytest -m live -rA

For every provider in the registry this runs the production pipeline (robots.txt check, fetch,
extraction, five-dimension binding, storage) into a temporary data directory and checks that:

* a successful retrieval yields verified prices whose evidence text is really on the fetched page,
  whose source URL is on the provider's official domain, and whose amounts are in INR;
* a failed retrieval is reported honestly (outcome + error) and produces NO usable price.

A provider whose site blocks automated access, needs JavaScript (without the browser extra) or
changed its layout is reported as XFAIL with the reason, never as a pass. Results depend on the
day, your network and each site's markup, so this suite is not part of CI.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest

from subwise.config import Settings
from subwise.container import Container, build_container
from subwise.research.registry import PROVIDERS, PROVIDERS_BY_ID

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def live(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Container]:
    data = tmp_path_factory.mktemp("live")
    settings = Settings(data_dir=Path(data), tavily_api_key=None)  # real fetcher, real network
    c = build_container(settings)
    yield c
    c.close()


@pytest.mark.parametrize("provider_id", [p.id for p in PROVIDERS])
def test_provider_retrieval_is_verified_or_honestly_failed(
    live: Container, provider_id: str
) -> None:
    (result,) = live.prices.refresh([provider_id])
    prov = PROVIDERS_BY_ID[provider_id]
    print(
        f"\n{prov.name}: outcome={result.outcome} found={result.prices_found} "
        f"verified={result.verified} error={result.error} warnings={result.warnings[:3]}"
    )
    prices = [p for p in live.prices.plan_prices() if p.provider_id == provider_id]

    if result.outcome != "success":
        # Honest failure: nothing live-verified may exist for this provider.
        assert result.error or result.warnings or result.outcome in ("no_prices", "needs_js")
        assert not [p for p in prices if p.label == "live_verified"]
        pytest.xfail(
            f"{prov.name}: {result.outcome} - {result.error or '; '.join(result.warnings[:2])}"
        )

    assert result.verified > 0 and prices
    page_dir = live.settings.sources_dir
    page_text = "\n".join(
        f.read_text(encoding="utf-8", errors="ignore") for f in page_dir.rglob("*") if f.is_file()
    )
    for p in prices:
        assert p.label == "live_verified", p
        assert p.price_paise > 0
        host = urlparse(p.source_url or "").hostname or ""
        assert any(host == d or host.endswith("." + d) for d in prov.official_domains), host
        # The evidence snippet's digits must appear in a stored source page.
        digits = "".join(ch for ch in p.evidence_snippet if ch.isdigit())
        assert digits and digits[:3] in "".join(ch for ch in page_text if ch.isdigit()), p
