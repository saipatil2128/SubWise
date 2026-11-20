"""Provider registry for the Indian MVP (blueprint G.1, G.5).

This file contains NO prices. It holds only what a person would need to find the official
India pricing page and recognise plan names on it:

* official domains and the India pricing URL to fetch,
* a marker in that URL proving it is the India variant of the page,
* the vocabulary of plan (tier) names used to bind a price to a plan,
* features that define the service itself (a music service streams music); every
  plan-specific feature (ad-free, 4K, screens, downloads ...) is extracted from the page.

Prices, billing cycles and plan-specific features are always read from the live page at run
time and stored with evidence. If a provider changes its page, extraction reports
"no prices found" rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from subwise.domain.enums import Category, Eligibility


@dataclass(frozen=True, slots=True)
class TierDef:
    key: str
    display: str
    aliases: tuple[str, ...]
    eligibility: tuple[Eligibility, ...] = ()
    defining_features: frozenset[str] = frozenset()
    """Features that define this tier's product (not extracted). Keep empty unless certain."""


@dataclass(frozen=True, slots=True)
class ProviderDef:
    id: str
    name: str
    category: Category
    service_line_id: str
    service_line_name: str
    official_domains: tuple[str, ...]
    pricing_url: str
    region_markers: tuple[str, ...]
    """Substrings of the final URL that prove the India page was served (e.g. '/in')."""
    tiers: tuple[TierDef, ...]
    defining_features: frozenset[str]
    """Features every plan of the service has by definition (e.g. a music service streams
    music). Plan-specific features are extracted from the page."""
    entitled_lines: tuple[str, ...] = ()
    """Extra service lines granted by every plan (bundles), e.g. Prime -> Prime Video, Music."""
    needs_js: bool = False
    plan_prefixes: tuple[str, ...] = ()
    """Words that may precede a tier name in headings, e.g. 'Premium' in 'Premium Standard'."""
    page_cycle_phrases: tuple[tuple[str, int], ...] = ()
    """(regex, months): page-level statements that fix the billing cycle for the whole page,
    used only when no cycle phrase sits next to a price (e.g. Netflix: 'billed monthly')."""
    notes: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def _t(key: str, display: str, *aliases: str, **kw: object) -> TierDef:
    return TierDef(key=key, display=display, aliases=(display, *aliases), **kw)  # type: ignore[arg-type]


STUDENT = (Eligibility.STUDENT,)

PROVIDERS: tuple[ProviderDef, ...] = (
    ProviderDef(
        id="netflix",
        name="Netflix",
        category=Category.VIDEO,
        service_line_id="netflix_streaming",
        service_line_name="Netflix streaming",
        official_domains=("netflix.com",),
        pricing_url="https://help.netflix.com/en/node/24926/in",
        region_markers=("/in",),
        tiers=(
            _t("mobile", "Mobile"),
            _t("basic", "Basic"),
            _t("standard", "Standard"),
            _t("premium", "Premium"),
        ),
        defining_features=frozenset({"movies", "tv_series"}),
        page_cycle_phrases=((r"billed monthly", 1), (r"/\s?month", 1)),
        notes="Help-centre page per country; static HTML.",
    ),
    ProviderDef(
        id="amazon_prime",
        name="Amazon Prime",
        category=Category.VIDEO,
        service_line_id="prime_membership",
        service_line_name="Amazon Prime membership",
        official_domains=("amazon.in",),
        pricing_url="https://www.amazon.in/amazonprime",
        region_markers=("amazon.in",),
        tiers=(
            _t("prime", "Prime", "Monthly Prime", "Quarterly Prime", "Annual Prime"),
            _t("prime_lite", "Prime Lite", "Annual Prime Lite"),
        ),
        defining_features=frozenset({"movies", "tv_series"}),
        entitled_lines=("prime_video",),
        notes="Bundle: membership includes Prime Video. Music/delivery extracted when stated.",
    ),
    ProviderDef(
        id="jiohotstar",
        name="JioHotstar",
        category=Category.VIDEO,
        service_line_id="jiohotstar_streaming",
        service_line_name="JioHotstar streaming",
        official_domains=("jiohotstar.com", "hotstar.com"),
        pricing_url="https://www.jiohotstar.com/subscribe",
        region_markers=("jiohotstar.com",),
        tiers=(_t("mobile", "Mobile"), _t("super", "Super"), _t("premium", "Premium")),
        defining_features=frozenset({"movies", "tv_series"}),
        needs_js=True,
        notes="India-only service; pricing rendered with JavaScript.",
    ),
    ProviderDef(
        id="sonyliv",
        name="Sony LIV",
        category=Category.VIDEO,
        service_line_id="sonyliv_streaming",
        service_line_name="Sony LIV streaming",
        official_domains=("sonyliv.com",),
        pricing_url="https://www.sonyliv.com/subscription",
        region_markers=("sonyliv.com",),
        tiers=(
            _t("mobile", "Mobile", "LIV Mobile", "Mobile Only"),
            _t("premium", "Premium", "LIV Premium"),
        ),
        defining_features=frozenset({"movies", "tv_series"}),
        needs_js=True,
    ),
    ProviderDef(
        id="zee5",
        name="ZEE5",
        category=Category.VIDEO,
        service_line_id="zee5_streaming",
        service_line_name="ZEE5 streaming",
        official_domains=("zee5.com",),
        pricing_url="https://www.zee5.com/myaccount/subscription",
        region_markers=("zee5.com",),
        tiers=(
            _t("premium_hd", "Premium HD"),
            _t("premium_4k", "Premium 4K"),
            _t("premium", "Premium"),
        ),
        defining_features=frozenset({"movies", "tv_series"}),
        needs_js=True,
    ),
    ProviderDef(
        id="spotify",
        name="Spotify",
        category=Category.MUSIC,
        service_line_id="spotify_premium",
        service_line_name="Spotify Premium",
        official_domains=("spotify.com",),
        pricing_url="https://www.spotify.com/in-en/premium/",
        region_markers=("/in-en/", "/in/"),
        tiers=(
            _t("standard", "Standard"),
            _t("platinum", "Platinum"),
            _t("student", "Student", eligibility=STUDENT),
            _t("individual", "Individual"),
            _t("duo", "Duo"),
            _t("family", "Family"),
            _t("lite", "Lite"),
        ),
        plan_prefixes=("Premium", "Spotify Premium"),
        defining_features=frozenset({"music_streaming"}),
    ),
    ProviderDef(
        id="youtube_premium",
        name="YouTube Premium",
        category=Category.MUSIC,
        service_line_id="youtube_premium",
        service_line_name="YouTube Premium",
        official_domains=("youtube.com",),
        pricing_url="https://www.youtube.com/premium?gl=IN&hl=en-IN",
        region_markers=("gl=IN",),
        tiers=(
            _t("individual", "Individual"),
            _t("family", "Family"),
            _t("student", "Student", eligibility=STUDENT),
        ),
        defining_features=frozenset({"music_streaming", "ad_free_video"}),
        entitled_lines=("youtube_music_premium",),
        needs_js=True,
        notes="YouTube Premium includes YouTube Music Premium and ad-free YouTube by definition.",
    ),
    ProviderDef(
        id="apple_music",
        name="Apple Music",
        category=Category.MUSIC,
        service_line_id="apple_music",
        service_line_name="Apple Music",
        official_domains=("apple.com",),
        pricing_url="https://www.apple.com/in/apple-music/",
        region_markers=("/in/",),
        tiers=(
            _t("individual", "Individual"),
            _t("family", "Family"),
            _t("student", "Student", eligibility=STUDENT),
        ),
        defining_features=frozenset({"music_streaming"}),
    ),
)

PROVIDERS_BY_ID: dict[str, ProviderDef] = {p.id: p for p in PROVIDERS}


def get_provider(provider_id: str) -> ProviderDef:
    try:
        return PROVIDERS_BY_ID[provider_id]
    except KeyError as exc:
        raise KeyError(f"Unknown provider {provider_id!r}") from exc
