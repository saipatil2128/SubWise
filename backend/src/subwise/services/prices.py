"""Price research service: sync the provider registry, fetch official pages, extract, validate,
store evidence, and answer "what can the optimizer use right now?" (blueprint G).

Honesty rules enforced here:
* every observation records its source document, binding and status;
* a failed fetch is recorded as a failed FetchAttempt - it never produces observations;
* a previously verified price is shown as ``cached_verified`` (with its age) once the latest
  fetch fails or it is older than 24 h - never as live.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from subwise.core.costing import monthly_equivalent
from subwise.core.validation import classify, display_label, evidence_text_present, freshness
from subwise.db.models import (
    FetchAttempt,
    Plan,
    PlanFeature,
    PriceObservation,
    Provider,
    ServiceLine,
    SourceDocument,
)
from subwise.db.session import session_scope
from subwise.domain.enums import BindingMethod, ExtractedBy, ObservationStatus, PriceKind
from subwise.errors import FetchFailed, SourceDisallowed
from subwise.ids import new_id
from subwise.research.extract import ExtractedPrice, extract_prices
from subwise.research.fetch import Fetcher
from subwise.research.registry import PROVIDERS, ProviderDef, get_provider
from subwise.research.search import NullSearchProvider, SearchProvider

log = logging.getLogger(__name__)

CYCLE_LABEL = {1: "Monthly", 3: "Quarterly", 6: "6 months", 12: "Annual"}


@dataclass
class RefreshResult:
    provider_id: str
    outcome: str
    prices_found: int = 0
    verified: int = 0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    fetched_at: datetime | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class PlanPrice:
    """One usable price for one plan, with everything the optimizer and UI need."""

    plan_id: str
    provider_id: str
    provider_name: str
    plan_name: str
    service_line_id: str
    exclusion_group: str
    entitled_lines: tuple[str, ...]
    eligibility: tuple[str, ...]
    billing_cycle_months: int
    price_paise: int
    monthly_paise: int
    observation_id: str
    status: str  # verified/partial/unverified/conflict
    label: str  # live_verified/cached_verified/partial/unverified/conflict
    observed_at: datetime
    age_days: int
    source_url: str | None
    evidence_snippet: str
    features: dict[str, str]
    intro: dict[str, Any] | None = None


def plan_id_for(provider_id: str, tier_key: str, cycle: int) -> str:
    return f"{provider_id}:{tier_key}:{cycle}m"


class PriceService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        fetcher: Fetcher,
        search: SearchProvider | None = None,
    ) -> None:
        self._sf = session_factory
        self._fetcher = fetcher
        self._search: SearchProvider = search or NullSearchProvider()

    # ------------------------------------------------------------------ registry
    def sync_registry(self) -> None:
        """Upsert providers and service lines (no prices, no plans)."""
        with session_scope(self._sf) as s:
            for p in PROVIDERS:
                row = s.get(Provider, p.id) or Provider(id=p.id)
                row.name, row.category = p.name, p.category.value
                row.official_domains = list(p.official_domains)
                row.pricing_url, row.needs_js = p.pricing_url, p.needs_js
                row.service_line_id = p.service_line_id
                s.merge(row)
                s.flush()
                for line_id, name in [
                    (p.service_line_id, p.service_line_name),
                    *[(e, e.replace("_", " ").title()) for e in p.entitled_lines],
                ]:
                    line = s.get(ServiceLine, line_id) or ServiceLine(id=line_id)
                    line.provider_id, line.name, line.category = p.id, name, p.category.value
                    s.merge(line)

    # ------------------------------------------------------------------ refresh
    def refresh(
        self, provider_ids: list[str] | None = None, *, run_id: str | None = None
    ) -> list[RefreshResult]:
        ids = provider_ids or [p.id for p in PROVIDERS]
        return [self.refresh_provider(pid, run_id=run_id) for pid in ids]

    def refresh_provider(self, provider_id: str, *, run_id: str | None = None) -> RefreshResult:
        provider = get_provider(provider_id)
        attempt_id = new_id("att")
        started = datetime.now(UTC)
        with session_scope(self._sf) as s:
            s.add(
                FetchAttempt(
                    id=attempt_id,
                    provider_id=provider.id,
                    run_id=run_id,
                    url=provider.pricing_url,
                    started_at=started,
                    outcome="running",
                )
            )
        result = RefreshResult(provider.id, "failed", source_url=provider.pricing_url)
        self._try_url(provider, provider.pricing_url, attempt_id, result)
        if result.outcome not in ("success", "disallowed") and self._search.enabled:
            for url in self._alternative_urls(provider, result):
                alt = RefreshResult(provider.id, "failed", source_url=url)
                self._try_url(provider, url, attempt_id, alt)
                if alt.outcome == "success":
                    alt.warnings.insert(0, f"registry URL failed; used search result {url}")
                    result = alt
                    break
        with session_scope(self._sf) as s:
            att = s.get(FetchAttempt, attempt_id)
            assert att is not None
            att.url = result.source_url or provider.pricing_url
            att.finished_at = datetime.now(UTC)
            att.outcome, att.error = result.outcome, result.error
            att.prices_found, att.verified_found = result.prices_found, result.verified
            att.warnings = result.warnings
        return result

    def _try_url(
        self, provider: ProviderDef, url: str, attempt_id: str, result: RefreshResult
    ) -> None:
        try:
            page = self._fetcher.fetch(url, needs_js=provider.needs_js)
        except SourceDisallowed as exc:
            result.outcome, result.error = "disallowed", exc.message
        except FetchFailed as exc:
            result.outcome, result.error = "failed", exc.message
        except Exception as exc:  # never let one provider break a run
            log.exception("unexpected fetch error for %s", provider.id)
            result.outcome, result.error = "failed", f"{type(exc).__name__}: {exc}"
        else:
            self._ingest(provider, page, attempt_id, result)

    def _alternative_urls(self, provider: ProviderDef, result: RefreshResult) -> list[str]:
        """Optional tier-3 discovery: official-domain pages found by search (max 2)."""
        try:
            hits = self._search.search(
                f"{provider.name} subscription plans price India",
                country="IN",
                max_results=5,
                include_domains=list(provider.official_domains),
            )
        except Exception as exc:
            result.warnings.append(f"search unavailable: {exc}")
            return []
        urls = []
        for h in hits:
            host = (h.url.host or "").lower()
            if any(host == d or host.endswith("." + d) for d in provider.official_domains):
                u = str(h.url)
                if u != provider.pricing_url and u not in urls:
                    urls.append(u)
        return urls[:2]

    def _ingest(
        self, provider: ProviderDef, page: Any, attempt_id: str, result: RefreshResult
    ) -> None:
        extraction = extract_prices(provider, page.html, page.final_url)
        result.warnings = extraction.warnings
        result.fetched_at = page.fetched_at
        doc_id = new_id("doc")
        with session_scope(self._sf) as s:
            s.add(
                SourceDocument(
                    id=doc_id,
                    provider_id=provider.id,
                    requested_url=page.requested_url,
                    final_url=page.final_url,
                    http_status=page.http_status,
                    sha256=page.sha256,
                    fetch_method=page.method,
                    fetched_at=page.fetched_at,
                    path=str(page.path) if page.path else None,
                )
            )
            s.flush()
            att = s.get(FetchAttempt, attempt_id)
            assert att is not None
            att.source_document_id, att.http_status = doc_id, page.http_status
            for ep in extraction.prices:
                if ep.cycle_months is None:
                    continue  # cannot identify the plan variant without a billing period
                self._store(
                    s,
                    provider,
                    ep,
                    extraction.page_text,
                    doc_id,
                    attempt_id,
                    page.fetched_at,
                    result,
                )
        if result.prices_found == 0:
            js_hint = provider.needs_js and not self._fetcher.playwright_available
            result.outcome = "needs_js" if js_hint else "no_prices"
            result.error = (
                "Prices on this page are rendered with JavaScript. To read it, install Playwright "
                '(pip install -e ".[browser]" then python -m playwright install chromium) and '
                "set SUBWISE_PLAYWRIGHT_ENABLED=true."
                if js_hint
                else "The page was fetched but no plan prices could be bound to plans."
            )
        else:
            result.outcome = "success" if result.verified else "no_prices"
            if not result.verified:
                result.error = "Prices were found but none could be fully verified."

    def _store(
        self,
        s: Session,
        provider: ProviderDef,
        ep: ExtractedPrice,
        page_text: str,
        doc_id: str,
        attempt_id: str,
        observed_at: datetime,
        result: RefreshResult,
    ) -> None:
        assert ep.cycle_months is not None
        pid = plan_id_for(provider.id, ep.tier.key, ep.cycle_months)
        plan = s.get(Plan, pid)
        if plan is None:
            plan = Plan(
                id=pid,
                provider_id=provider.id,
                service_line_id=provider.service_line_id,
                tier_key=ep.tier.key,
                first_seen_at=observed_at,
            )
            s.add(plan)
        plan.name = f"{provider.name} {ep.tier.display} ({CYCLE_LABEL[ep.cycle_months]})"
        plan.billing_cycle_months = ep.cycle_months
        plan.exclusion_group = provider.service_line_id
        plan.entitled_lines = [provider.service_line_id, *provider.entitled_lines]
        plan.eligibility = [e.value for e in ep.tier.eligibility]
        plan.last_seen_at, plan.active = observed_at, True
        s.flush()
        for code in provider.defining_features | ep.tier.defining_features:
            s.merge(
                PlanFeature(
                    plan_id=pid,
                    feature_code=code,
                    value="yes",
                    source="defining",
                    evidence=f"{provider.name} service definition",
                    observed_at=observed_at,
                )
            )
        for f in ep.features:
            s.merge(
                PlanFeature(
                    plan_id=pid,
                    feature_code=f.code,
                    value=f.value,
                    source="extracted",
                    evidence=f.evidence,
                    observed_at=observed_at,
                )
            )
        prev = s.scalars(
            select(PriceObservation.price_paise)
            .where(
                PriceObservation.plan_id == pid,
                PriceObservation.price_kind == ep.price_kind.value,
                PriceObservation.status == ObservationStatus.VERIFIED.value,
            )
            .order_by(PriceObservation.observed_at.desc())
            .limit(1)
        ).first()
        dims = {
            "provider": ep.provider_binding,
            "plan": ep.plan_binding,
            "billing_cycle": ep.cycle_binding,
            "currency": ep.currency_binding,
            "region": ep.region_binding,
        }
        unbound = [k for k, b in dims.items() if b.method is BindingMethod.UNBOUND]
        cls = classify(
            price_paise=ep.price_paise,
            cycle_months=ep.cycle_months,
            unbound=unbound,
            evidence_present=evidence_text_present(ep.evidence_snippet, page_text, ep.price_paise),
            extracted_by=ExtractedBy.ADAPTER,
            previous_verified_paise=prev,
        )
        s.add(
            PriceObservation(
                id=new_id("obs"),
                plan_id=pid,
                source_document_id=doc_id,
                fetch_attempt_id=attempt_id,
                price_paise=ep.price_paise,
                billing_cycle_months=ep.cycle_months,
                price_kind=ep.price_kind.value,
                intro_months=ep.intro_months,
                evidence_snippet=ep.evidence_snippet,
                binding={
                    k: {"method": b.method.value, "matched_text": b.matched_text, "note": b.note}
                    for k, b in dims.items()
                },
                extracted_by=ExtractedBy.ADAPTER.value,
                status=cls.status.value,
                reasons=list(cls.reasons),
                observed_at=observed_at,
            )
        )
        result.prices_found += 1
        if cls.status is ObservationStatus.VERIFIED:
            result.verified += 1

    # ------------------------------------------------------------------ queries
    def latest_attempts(self) -> dict[str, FetchAttempt]:
        with session_scope(self._sf) as s:
            rows = s.scalars(
                select(FetchAttempt)
                .where(FetchAttempt.outcome != "running")
                .order_by(FetchAttempt.started_at.desc())
            ).all()
            out: dict[str, FetchAttempt] = {}
            for r in rows:
                out.setdefault(r.provider_id, r)
            return out

    def plan_prices(self, now: datetime | None = None) -> list[PlanPrice]:
        """Latest standard/renewal observation per plan with its display label."""
        now = now or datetime.now(UTC)
        attempts = self.latest_attempts()
        out: list[PlanPrice] = []
        with session_scope(self._sf) as s:
            plans = s.scalars(select(Plan).where(Plan.active.is_(True))).all()
            providers = {p.id: p for p in s.scalars(select(Provider)).all()}
            for plan in plans:
                obs_rows = s.scalars(
                    select(PriceObservation)
                    .where(PriceObservation.plan_id == plan.id)
                    .order_by(PriceObservation.observed_at.desc())
                ).all()
                regular = next(
                    (
                        o
                        for o in obs_rows
                        if o.price_kind in (PriceKind.STANDARD.value, PriceKind.RENEWAL.value)
                    ),
                    None,
                )
                if regular is None:
                    continue
                intro = next(
                    (
                        o
                        for o in obs_rows
                        if o.price_kind == PriceKind.INTRO.value
                        and o.observed_at == regular.observed_at
                    ),
                    None,
                )
                doc = (
                    s.get(SourceDocument, regular.source_document_id)
                    if (regular.source_document_id)
                    else None
                )
                att = attempts.get(plan.provider_id)
                latest_ok = (
                    att is not None
                    and att.outcome == "success"
                    and att.source_document_id == regular.source_document_id
                )
                label = display_label(
                    status=ObservationStatus(regular.status),
                    observed_at=regular.observed_at,
                    now=now,
                    latest_attempt_ok=latest_ok,
                )
                _, age = freshness(regular.observed_at, now)
                feats = {
                    f.feature_code: f.value
                    for f in s.scalars(
                        select(PlanFeature).where(PlanFeature.plan_id == plan.id)
                    ).all()
                }
                prov = providers[plan.provider_id]
                out.append(
                    PlanPrice(
                        plan_id=plan.id,
                        provider_id=plan.provider_id,
                        provider_name=prov.name,
                        plan_name=plan.name,
                        service_line_id=plan.service_line_id,
                        exclusion_group=plan.exclusion_group or plan.service_line_id,
                        entitled_lines=tuple(plan.entitled_lines or [plan.service_line_id]),
                        eligibility=tuple(plan.eligibility or []),
                        billing_cycle_months=regular.billing_cycle_months,
                        price_paise=regular.price_paise,
                        monthly_paise=monthly_equivalent(
                            regular.price_paise, regular.billing_cycle_months
                        ).paise,
                        observation_id=regular.id,
                        status=regular.status,
                        label=label,
                        observed_at=regular.observed_at,
                        age_days=age,
                        source_url=doc.final_url if doc else None,
                        evidence_snippet=regular.evidence_snippet,
                        features=feats,
                        intro=(
                            {
                                "price_paise": intro.price_paise,
                                "months": intro.intro_months,
                                "evidence": intro.evidence_snippet,
                            }
                            if intro
                            else None
                        ),
                    )
                )
        return out

    def history(self, plan_id: str) -> list[PriceObservation]:
        with session_scope(self._sf) as s:
            return list(
                s.scalars(
                    select(PriceObservation)
                    .where(PriceObservation.plan_id == plan_id)
                    .order_by(PriceObservation.observed_at)
                ).all()
            )


def usable_for_optimizer(
    price: PlanPrice, *, allow_cached: bool, allow_partial: bool, allow_unverified: bool
) -> tuple[bool, str]:
    """Decide whether a price may enter the optimizer, and say why not."""
    if price.label == "live_verified":
        return True, "live and verified"
    if price.label == "cached_verified":
        if price.age_days > 30:
            return False, f"cached price is {price.age_days} days old (over 30)"
        if allow_cached:
            return True, f"cached, last verified {price.age_days} day(s) ago"
        return False, "cached price and cached prices are switched off in your settings"
    if price.label == "partial":
        return (
            allow_partial,
            "partially verified"
            if allow_partial
            else "only partially verified (switched off in your settings)",
        )
    if price.label == "unverified":
        return (
            allow_unverified,
            "unverified price"
            if allow_unverified
            else "price could not be verified against the source",
        )
    return False, "conflicting prices from sources"
