"""Evidence-bound price extraction from an official pricing page (blueprint G.2-G.3, v2).

Pure module (HTML string in, findings out). For every price it binds five dimensions:

* provider - the final URL's domain is one of the provider's official domains;
* plan     - a tier name heads the same DOM block (or table column/row) as the price;
* cycle    - a billing phrase is attached to this amount, or the page states one cycle;
* currency - ₹ / Rs / INR is adjacent to the amount and no foreign currency is on the page;
* region   - the final URL is the India variant of the page AND INR is bound.

Nothing here guesses. A price that cannot be bound on a dimension is returned with that
dimension UNBOUND so validation marks it ``unverified`` (never used by default).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

from subwise.core.features import FeatureFinding, detect_features
from subwise.core.money import FOREIGN_CURRENCY_RE, amount_to_paise
from subwise.domain.enums import BindingMethod, PriceKind
from subwise.research.registry import ProviderDef, TierDef

_WS = re.compile(r"\s+")
_AMT = r"(?:₹|Rs\.?|INR)\s?(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
_PERIOD_WORDS = (
    r"(?P<n>\d+|one|a|an)?\s*(?P<unit>months?|mos?|years?|yrs?|year|annum|quarters?|days?)"
)

# "₹99 for 3 months, then ₹139 per month after"
INTRO_RE = re.compile(
    _AMT + r"\s+for\s+(?P<n>\d+|one|a)\s+(?P<unit>months?|years?)\W{0,3}\s*(?:,|and|\.)?\s*"
    r"then\s+" + _AMT.replace("(\\d", "(?P<r>\\d", 1) + r"\s*(?:/|per|a|every)\s*"
    r"(?P<runit>month|mo|year|yr|quarter)",
    re.I,
)
# "₹139 / month", "₹1,499 per year", "₹599 every 3 months", "₹149/quarter"
PERIODIC_RE = re.compile(
    _AMT + r"\s*(?:/|per|a|every|for)\s*(?:(?P<n>\d+|one|a)\s+)?"
    r"(?P<unit>months?|mo|years?|yr|annum|quarters?|days?)\b",
    re.I,
)
# "₹299 monthly" / "₹1,499 annually"
ADVERB_RE = re.compile(_AMT + r"\s*\(?\s*(?P<adv>monthly|quarterly|annually|yearly)\b", re.I)
BARE_RE = re.compile(_AMT, re.I)
_NUM_WORDS = {"one": 1, "a": 1, "an": 1}
_DAYS_TO_MONTHS = {28: 1, 30: 1, 31: 1, 84: 3, 90: 3, 180: 6, 365: 12}


@dataclass(frozen=True, slots=True)
class Binding:
    method: BindingMethod
    matched_text: str | None = None
    note: str | None = None


@dataclass(slots=True)
class ExtractedPrice:
    tier: TierDef
    price_paise: int
    cycle_months: int | None
    price_kind: PriceKind
    intro_months: int | None
    evidence_snippet: str
    provider_binding: Binding
    plan_binding: Binding
    cycle_binding: Binding
    currency_binding: Binding
    region_binding: Binding
    block_text: str
    features: list[FeatureFinding] = field(default_factory=list)

    @property
    def fully_bound(self) -> bool:
        return all(
            b.method is not BindingMethod.UNBOUND
            for b in (
                self.provider_binding,
                self.plan_binding,
                self.cycle_binding,
                self.currency_binding,
                self.region_binding,
            )
        )


@dataclass(slots=True)
class ExtractionResult:
    page_text: str
    prices: list[ExtractedPrice]
    warnings: list[str]


def normalise(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _months(n_raw: str | None, unit: str) -> int | None:
    unit = unit.lower()
    n = 1
    if n_raw:
        n = int(n_raw) if n_raw.isdigit() else _NUM_WORDS.get(n_raw.lower(), 0)
    if unit.startswith(("month", "mo")):
        months = n
    elif unit.startswith(("year", "yr", "annum")):
        months = 12 * n
    elif unit.startswith("quarter"):
        months = 3 * n
    elif unit.startswith("day"):
        months = _DAYS_TO_MONTHS.get(n, 0)
    else:
        months = 0
    return months if months in (1, 3, 6, 12) else None


def _count_months(n_raw: str | None, unit: str) -> int | None:
    """Length of an introductory period in months (any 1-24, not only billing cycles)."""
    n = 1
    if n_raw:
        n = int(n_raw) if n_raw.isdigit() else _NUM_WORDS.get(n_raw.lower(), 0)
    months = 12 * n if unit.lower().startswith("year") else n
    return months if 1 <= months <= 24 else None


def _sections(soup: BeautifulSoup, provider: ProviderDef) -> dict[str, list[str]]:
    """Text under each tier heading (heading + following siblings until the next tier
    heading). Used for plan FEATURES only, never for prices."""
    out: dict[str, list[str]] = {}
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "dt", "strong"]):
        if not isinstance(el, Tag):
            continue
        tier = _anchor_tier(provider, _own_text(el))
        if tier is None:
            continue
        parts = [_own_text(el)]
        for sib in el.find_next_siblings():
            if not isinstance(sib, Tag):
                continue
            if _anchor_tier(provider, _own_text(sib)) is not None:
                break
            heads = sib.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "dt", "strong"])
            if any(_anchor_tier(provider, _own_text(h)) for h in heads if isinstance(h, Tag)):
                break
            parts.append(_own_text(sib))
            if sum(len(x) for x in parts) > 1500:
                break
        out.setdefault(tier.key, []).append(normalise(" ".join(parts)))
    return out


def _alias_pattern(provider: ProviderDef, alias: str) -> re.Pattern[str]:
    prefixes = "|".join(re.escape(p) for p in provider.plan_prefixes)
    prefix = rf"(?:(?:{prefixes})\s+)?" if prefixes else ""
    return re.compile(rf"^\s*{prefix}{re.escape(alias)}(?:\s+plan)?\b", re.I)


def _anchor_tier(provider: ProviderDef, text: str) -> TierDef | None:
    """Tier whose name starts ``text`` (longest alias wins, so 'Premium 4K' beats 'Premium')."""
    if len(text) > 60:
        return None
    best: tuple[int, TierDef] | None = None
    for tier in provider.tiers:
        for alias in tier.aliases:
            if _alias_pattern(provider, alias).match(text) and (
                best is None or len(alias) > best[0]
            ):
                best = (len(alias), tier)
    return best[1] if best else None


def _mentions_other_tier(provider: ProviderDef, text: str, tier: TierDef) -> bool:
    """True if a *different* tier's name appears as a heading-like phrase in ``text``."""
    own = {a.lower() for a in tier.aliases}
    for other in provider.tiers:
        if other.key == tier.key:
            continue
        for alias in other.aliases:
            if alias.lower() in own or any(alias.lower() in o for o in own):
                continue
            prefixes = "|".join(re.escape(p) for p in provider.plan_prefixes)
            pat = (
                rf"(?:(?:{prefixes})\s+){re.escape(alias)}\b"
                if prefixes
                else rf"\b{re.escape(alias)}\b"
            )
            if re.search(pat, text, re.I if prefixes else 0):
                return True
    return False


def _own_text(el: Tag) -> str:
    return normalise(el.get_text(" ", strip=True))


def _blocks(soup: BeautifulSoup, provider: ProviderDef) -> list[tuple[TierDef, str, Binding]]:
    """Find (tier, block_text, plan_binding) for every element headed by a tier name."""
    out: list[tuple[TierDef, str, Binding]] = []
    seen: set[tuple[str, str]] = set()
    for el in soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "li",
            "span",
            "div",
            "strong",
            "b",
            "th",
            "td",
            "dt",
            "label",
            "button",
        ]
    ):
        if not isinstance(el, Tag):
            continue
        text = _own_text(el)
        tier = _anchor_tier(provider, text)
        if tier is None:
            continue
        node: Tag | None = el
        for _ in range(7):
            if node is None:
                break
            block = _own_text(node)
            if BARE_RE.search(block):
                if _mentions_other_tier(provider, block, tier):
                    # Shared container: keep only the window that starts at this tier's name.
                    start = block.find(text[:40])
                    window = block[start:] if start >= 0 else block
                    nxt = _next_other_tier_pos(provider, window, tier)
                    window = window[:nxt] if nxt else window
                    if BARE_RE.search(window):
                        key = (tier.key, window)
                        if key not in seen:
                            seen.add(key)
                            out.append(
                                (tier, window, Binding(BindingMethod.SAME_TEXT_WINDOW, text[:60]))
                            )
                else:
                    key = (tier.key, block)
                    if key not in seen:
                        seen.add(key)
                        out.append((tier, block, Binding(BindingMethod.SAME_DOM_BLOCK, text[:60])))
                break
            parent = node.parent
            node = parent if isinstance(parent, Tag) else None
    return out


def _next_other_tier_pos(provider: ProviderDef, window: str, tier: TierDef) -> int | None:
    positions = []
    for other in provider.tiers:
        if other.key == tier.key:
            continue
        for alias in other.aliases:
            if any(alias.lower() in a.lower() for a in tier.aliases):
                continue
            prefixes = "|".join(re.escape(p) for p in provider.plan_prefixes)
            pat = (
                rf"(?:(?:{prefixes})\s+){re.escape(alias)}\b"
                if prefixes
                else rf"\b{re.escape(alias)}\b"
            )
            m = re.search(pat, window[1:], re.I if prefixes else 0)
            if m:
                positions.append(m.start() + 1)
    return min(positions) if positions else None


def _snippet(text: str, start: int, end: int, pad: int = 70) -> str:
    return text[max(0, start - pad) : min(len(text), end + pad)].strip()


def _parse_block(
    provider: ProviderDef,
    tier: TierDef,
    block: str,
    plan_binding: Binding,
    page_cycle: Binding | None,
    provider_b: Binding,
    region_ok: Binding,
) -> list[ExtractedPrice]:
    results: list[ExtractedPrice] = []
    consumed: list[tuple[int, int]] = []
    features = detect_features(block, provider.category, tier.display)

    def taken(span: tuple[int, int]) -> bool:
        return any(s < span[1] and span[0] < e for s, e in consumed)

    def emit(
        paise: int,
        cycle: int | None,
        kind: PriceKind,
        intro: int | None,
        span: tuple[int, int],
        cyc_b: Binding,
    ) -> None:
        snippet = _snippet(block, *span)
        cur_text = block[span[0] : span[0] + 4]
        results.append(
            ExtractedPrice(
                tier=tier,
                price_paise=paise,
                cycle_months=cycle,
                price_kind=kind,
                intro_months=intro,
                evidence_snippet=snippet,
                provider_binding=provider_b,
                plan_binding=plan_binding,
                cycle_binding=cyc_b,
                currency_binding=Binding(BindingMethod.ADJACENT_TOKEN, cur_text.strip()),
                region_binding=region_ok,
                block_text=block[:600],
                features=features,
            )
        )
        consumed.append(span)

    for m in INTRO_RE.finditer(block):
        intro_months = _count_months(m.group("n"), m.group("unit"))
        renewal_cycle = _months(None, m.group("runit"))
        if intro_months is None or renewal_cycle is None:
            continue
        span = (m.start(), m.end())
        cyc = Binding(BindingMethod.SAME_TEXT_WINDOW, m.group(0)[:80])
        emit(amount_to_paise(m.group("r")), renewal_cycle, PriceKind.RENEWAL, None, span, cyc)
        emit(amount_to_paise(m.group(1)), renewal_cycle, PriceKind.INTRO, intro_months, span, cyc)
    for m in PERIODIC_RE.finditer(block):
        span = (m.start(), m.end())
        if taken(span):
            continue
        cycle = _months(m.group("n"), m.group("unit"))
        if cycle is None:
            continue
        emit(
            amount_to_paise(m.group(1)),
            cycle,
            PriceKind.STANDARD,
            None,
            span,
            Binding(BindingMethod.SAME_TEXT_WINDOW, m.group(0)[:80]),
        )
    for m in ADVERB_RE.finditer(block):
        span = (m.start(), m.end())
        if taken(span):
            continue
        adv = m.group("adv").lower()
        cycle = {"monthly": 1, "quarterly": 3, "annually": 12, "yearly": 12}[adv]
        emit(
            amount_to_paise(m.group(1)),
            cycle,
            PriceKind.STANDARD,
            None,
            span,
            Binding(BindingMethod.SAME_TEXT_WINDOW, m.group(0)[:80]),
        )
    for m in BARE_RE.finditer(block):
        span = (m.start(), m.end())
        if taken(span):
            continue
        if page_cycle is not None:
            emit(
                amount_to_paise(m.group(1)),
                int(page_cycle.note or 0) or None,
                PriceKind.STANDARD,
                None,
                span,
                page_cycle,
            )
        else:
            emit(
                amount_to_paise(m.group(1)),
                None,
                PriceKind.STANDARD,
                None,
                span,
                Binding(BindingMethod.UNBOUND, None, "no billing period next to this price"),
            )
    return results


def _table_prices(
    soup: BeautifulSoup, provider: ProviderDef, provider_b: Binding, region_ok: Binding
) -> list[ExtractedPrice]:
    """Tables with tier names in one header and billing periods in the other."""
    out: list[ExtractedPrice] = []
    for table in soup.find_all("table"):
        if not isinstance(table, Tag):
            continue
        rows = [r for r in table.find_all("tr") if isinstance(r, Tag)]
        if len(rows) < 2:
            continue
        header = [_own_text(c) for c in rows[0].find_all(["th", "td"]) if isinstance(c, Tag)]
        for row in rows[1:]:
            cells = [c for c in row.find_all(["th", "td"]) if isinstance(c, Tag)]
            if not cells:
                continue
            row_head = _own_text(cells[0])
            for idx, cell in enumerate(cells[1:], start=1):
                text = _own_text(cell)
                m = BARE_RE.search(text)
                if not m or idx >= len(header):
                    continue
                col_head = header[idx]
                tier = _anchor_tier(provider, col_head) or _anchor_tier(provider, row_head)
                period_src = row_head if _anchor_tier(provider, col_head) else col_head
                pm = re.search(
                    r"(monthly|quarterly|annual|yearly|\d+\s*months?|1\s*year)", period_src, re.I
                )
                if tier is None:
                    continue
                cycle = None
                cyc_b = Binding(BindingMethod.UNBOUND, None, "no period header for this cell")
                if pm:
                    word = pm.group(1).lower()
                    cycle = {"monthly": 1, "quarterly": 3, "annual": 12, "yearly": 12}.get(word)
                    if cycle is None:
                        nm = re.match(r"(\d+)\s*(months?|year)", word)
                        if nm:
                            cycle = _months(nm.group(1), nm.group(2))
                    if cycle:
                        cyc_b = Binding(BindingMethod.TABLE_CELL, f"{row_head} / {col_head}")
                snippet = normalise(f"{row_head} {col_head} {text}")
                out.append(
                    ExtractedPrice(
                        tier=tier,
                        price_paise=amount_to_paise(m.group(1)),
                        cycle_months=cycle,
                        price_kind=PriceKind.STANDARD,
                        intro_months=None,
                        evidence_snippet=text,
                        provider_binding=provider_b,
                        plan_binding=Binding(BindingMethod.TABLE_CELL, col_head or row_head),
                        cycle_binding=cyc_b,
                        currency_binding=Binding(BindingMethod.ADJACENT_TOKEN, text[:4]),
                        region_binding=region_ok,
                        block_text=snippet,
                        features=detect_features(snippet, provider.category, tier.display),
                    )
                )
    return out


def bind_provider(provider: ProviderDef, final_url: str) -> Binding:
    host = (urlsplit(final_url).hostname or "").lower()
    for domain in provider.official_domains:
        if host == domain or host.endswith("." + domain):
            return Binding(BindingMethod.DOMAIN_MAP, host)
    return Binding(BindingMethod.UNBOUND, host, "final URL is not an official domain")


def bind_region(provider: ProviderDef, final_url: str, page_text: str) -> Binding:
    marker = next((m for m in provider.region_markers if m.lower() in final_url.lower()), None)
    if marker is None:
        return Binding(BindingMethod.UNBOUND, final_url, "URL is not the India page")
    foreign = FOREIGN_CURRENCY_RE.search(page_text)
    if foreign:
        return Binding(BindingMethod.UNBOUND, foreign.group(0), "page shows another currency")
    if not BARE_RE.search(page_text):
        return Binding(BindingMethod.UNBOUND, None, "no INR amount on page")
    return Binding(BindingMethod.URL_LOCALE, marker)


def extract_prices(provider: ProviderDef, html: str, final_url: str) -> ExtractionResult:
    soup = BeautifulSoup(html, "lxml")
    for junk in soup(["script", "style", "noscript", "svg", "template"]):
        junk.decompose()
    page_text = normalise(soup.get_text(" ", strip=True))
    warnings: list[str] = []
    provider_b = bind_provider(provider, final_url)
    region_b = bind_region(provider, final_url, page_text)
    if region_b.method is BindingMethod.UNBOUND:
        warnings.append(f"region not bound: {region_b.note}")

    page_cycle = None
    for pattern, months in provider.page_cycle_phrases:
        m = re.search(pattern, page_text, re.I)
        if m:
            page_cycle = Binding(BindingMethod.PAGE_STATEMENT, m.group(0), str(months))
            break

    prices: list[ExtractedPrice] = []
    for tier, block, plan_b in _blocks(soup, provider):
        prices.extend(_parse_block(provider, tier, block, plan_b, page_cycle, provider_b, region_b))
    prices.extend(_table_prices(soup, provider, provider_b, region_b))

    # Merge features stated in each tier's own section (headings followed by bullet lists).
    for tier_key, texts in _sections(soup, provider).items():
        for p in prices:
            if p.tier.key != tier_key:
                continue
            have = {f.code for f in p.features}
            for text in texts:
                for f in detect_features(text, provider.category, p.tier.display):
                    if f.code not in have:
                        p.features.append(f)
                        have.add(f.code)

    # De-duplicate: same tier + cycle + kind + amount found via nested blocks.
    unique: dict[tuple[str, int | None, str, int, int | None], ExtractedPrice] = {}
    for p in prices:
        key = (p.tier.key, p.cycle_months, p.price_kind.value, p.price_paise, p.intro_months)
        if key not in unique or len(p.block_text) < len(unique[key].block_text):
            unique[key] = p
    deduped = list(unique.values())

    # Two different amounts for the same tier/cycle/kind = ambiguous: unbind the plan.
    groups: dict[tuple[str, int | None, str], list[ExtractedPrice]] = {}
    for p in deduped:
        groups.setdefault((p.tier.key, p.cycle_months, p.price_kind.value), []).append(p)
    for (tier_key, cycle, _kind), items in groups.items():
        if len({i.price_paise for i in items}) > 1:
            warnings.append(f"ambiguous prices for {tier_key} cycle={cycle}")
            for i in items:
                i.plan_binding = Binding(
                    BindingMethod.UNBOUND, None, "several different prices for this plan and period"
                )
    if not deduped:
        warnings.append("no plan prices found on the page")
    return ExtractionResult(page_text=page_text, prices=deduped, warnings=warnings)
