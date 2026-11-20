"""Provider adapters: deterministic extractors for registry providers (tier 1). M8.

An adapter MUST bind every observation on all five dimensions (provider, plan, billing cycle,
currency, region) using the same DOM block, or mark the dimension UNBOUND. It must never
return a price it did not find inside that block.
"""

from __future__ import annotations

from typing import Protocol

from subwise.domain.catalog import Plan, Provider
from subwise.domain.evidence import PlanObservation
from subwise.research.fetch import FetchResult


class ProviderAdapter(Protocol):
    key: str
    pricing_url: str  # the India-region official pricing URL

    def extract(
        self, fetched: FetchResult, *, provider: Provider, plans: list[Plan]
    ) -> list[PlanObservation]: ...


ADAPTERS: dict[str, ProviderAdapter] = {}
"""Registry filled in M8, keyed by ``Provider.adapter_key``."""
