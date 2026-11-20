"""Feature vocabulary that OAVOE optimizes over, and the evidence rules that detect
plan-specific features in page text. Pure module."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from subwise.domain.enums import Category


@dataclass(frozen=True, slots=True)
class FeatureDef:
    code: str
    label: str
    category: Category | None  # None = cross-category
    description: str


FEATURES: Final[tuple[FeatureDef, ...]] = (
    FeatureDef("movies", "Movies", Category.VIDEO, "Streams films"),
    FeatureDef("tv_series", "TV series", Category.VIDEO, "Streams series and shows"),
    FeatureDef("live_sports", "Live sports", Category.VIDEO, "Live sport such as cricket"),
    FeatureDef("ad_free_video", "Ad-free video", Category.VIDEO, "Video without advertisements"),
    FeatureDef("full_hd", "Full HD (1080p)", Category.VIDEO, "1080p or better video"),
    FeatureDef("uhd_4k", "4K / Ultra HD", Category.VIDEO, "4K Ultra HD video"),
    FeatureDef("tv_screen", "Watch on TV", Category.VIDEO, "Usable on a TV or computer"),
    FeatureDef("multi_screen", "2+ screens at once", Category.VIDEO, "Two or more streams"),
    FeatureDef("offline_download", "Video downloads", Category.VIDEO, "Download to watch offline"),
    FeatureDef("music_streaming", "Music streaming", Category.MUSIC, "On-demand music"),
    FeatureDef("ad_free_music", "Ad-free music", Category.MUSIC, "Music without advertisements"),
    FeatureDef("offline_music", "Offline music", Category.MUSIC, "Download music offline"),
    FeatureDef("high_quality_audio", "High-quality audio", Category.MUSIC, "~320 kbps or better"),
    FeatureDef("lossless_audio", "Lossless audio", Category.MUSIC, "Lossless / hi-res audio"),
    FeatureDef("multi_account", "Multiple accounts", None, "Family, duo or shared plans"),
)
FEATURE_CODES: Final[frozenset[str]] = frozenset(f.code for f in FEATURES)
FEATURES_BY_CODE: Final[dict[str, FeatureDef]] = {f.code: f for f in FEATURES}

_AD_FREE = re.compile(r"\bad[\s-]?free\b|\bwithout ads\b|\bno ads\b|\bads?-free\b", re.I)
_WITH_ADS = re.compile(r"\bwith ads\b|\bad[\s-]?supported\b|\blimited ads\b", re.I)
_UHD = re.compile(r"\b4K\b|ultra\s?hd|\bUHD\b|2160p", re.I)
_FHD = re.compile(r"1080p|full\s?hd", re.I)
_DOWNLOAD = re.compile(r"\bdownloads?\b|\boffline\b", re.I)
_SCREENS = re.compile(
    r"\b(\d|one|two|three|four|five|six)\s+(?:\w+\s+){0,3}"
    r"(?:screens?|devices?)\b(?:\s+at\s+a\s+time)?",
    re.I,
)
_MOBILE_ONLY = re.compile(r"phone or tablet|mobile[\s-]only|1 mobile device|one phone", re.I)
_TV = re.compile(r"\bTV\b|smart tv|television|computer|laptop|supported devices?", re.I)
_SPORTS = re.compile(r"\blive sports?\b|\bcricket\b|\bIPL\b", re.I)
_HQ_AUDIO = re.compile(r"320\s?kbps|very high audio|high[\s-]quality audio", re.I)
_LOSSLESS = re.compile(r"lossless|hi[\s-]?res|24[\s-]bit", re.I)
_MULTI_ACC = re.compile(r"up to \d+ (?:\w+ )?(?:accounts|members)|family|\bduo\b", re.I)

_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def _screens(text: str) -> int | None:
    best = None
    for m in _SCREENS.finditer(text):
        raw = m.group(1).lower()
        n = int(raw) if raw.isdigit() else _WORDS[raw]
        best = n if best is None else max(best, n)
    return best


@dataclass(frozen=True, slots=True)
class FeatureFinding:
    code: str
    value: str  # "yes" | "no"
    evidence: str


def detect_features(text: str, category: Category, plan_name: str = "") -> list[FeatureFinding]:
    """Detect plan-specific features stated in ``text`` (one plan's block of an official page).

    Only states what the text says: a feature absent from the text is NOT returned (it stays
    'unknown'); 'no' is returned only when the text explicitly limits it (e.g. ads, mobile-only).
    """
    found: dict[str, FeatureFinding] = {}

    def add(code: str, value: str, m: re.Match[str] | None) -> None:
        if m is not None and code not in found:
            found[code] = FeatureFinding(code, value, m.group(0))

    if category is Category.VIDEO:
        add("ad_free_video", "yes", _AD_FREE.search(text))
        if "ad_free_video" not in found:
            add("ad_free_video", "no", _WITH_ADS.search(text))
        add("uhd_4k", "yes", _UHD.search(text))
        m_fhd = _FHD.search(text)
        add("full_hd", "yes", m_fhd or _UHD.search(text))
        add("offline_download", "yes", _DOWNLOAD.search(text))
        add("live_sports", "yes", _SPORTS.search(text))
        mob = _MOBILE_ONLY.search(text)
        if mob:
            add("tv_screen", "no", mob)
        else:
            add("tv_screen", "yes", _TV.search(text))
        n = _screens(text)
        if n is not None:
            m_scr = _SCREENS.search(text)
            add("multi_screen", "yes" if n >= 2 else "no", m_scr)
    else:
        add("ad_free_music", "yes", _AD_FREE.search(text))
        if "ad_free_music" not in found:
            add("ad_free_music", "no", _WITH_ADS.search(text))
        add("offline_music", "yes", _DOWNLOAD.search(text))
        add("lossless_audio", "yes", _LOSSLESS.search(text))
        add("high_quality_audio", "yes", _HQ_AUDIO.search(text) or _LOSSLESS.search(text))
    add("multi_account", "yes", _MULTI_ACC.search(f"{plan_name} {text}"))
    return list(found.values())
